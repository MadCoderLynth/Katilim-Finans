"""KAFİF bildirim kimliklerinin toplanması — Faz 1.2.

Bu adım **form indirmez**, yalnız kimlik listesi çıkarır. Sebep: kaç form
indireceğimizi bilmeden 1.4'ün bütçesi konuşulamaz.

Rota ve kaynak (2.0'da ölçüldü, yeniden keşfedilmiyor):

    /tr/bildirim-sorgu-sonuc?member={mkkMemberOid}&disclosureClass=DG

Veri **DOM'dan değil, gömülü RSC yükünden** okunur: `disclosureBasic` nesnesi
`disclosureIndex`, `publishDate`, `disclosureClass`, `year`, `period`, `donem`,
`title` alanlarını yapılandırılmış veriyor. Checkbox `id` niteliğini kazımak
(1.0'ın yolu) **yedek katman** olarak duruyor — birincil değil, yalnız RSC
ayıklaması boş dönerse "sayfa gerçekten boş mu" sorusunu ayırt etmeye yarıyor.

**Sayfalama döngüsü yok.** 2.0 ölçtü: sunucu bulduğu kaydın tamamını tek
sayfada basıyor (92 = 92) ve `page`/`offset`/`size` yok sayılıyor.

**İki eksen (1.1'in bulgusu).** Sorgu ekseni uuid (746 tüzel kişi), panel
ekseni ticker (795 pay kodu). Çoklu kodlu şirketler (ALBRK/ALK) bir kez
sorgulanır, sonuç kodlara sonradan dağıtılır — aksi halde 45 gereksiz istek
ve aynı bildirimin iki kaydı olurdu.

Değiştirilemez kural 7 bu modülün omurgası: **"0 kayıt" ile "sayfayı
okuyamadım" ayrı durumlardır.** `ayikla`, beklediği çıpaların hiçbirini
bulamazsa `SayfaOkunamadi` fırlatır; sessizce boş liste dönmez.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from bs4 import BeautifulSoup

from . import rsc
from .metin import normalize

SORGU_KALIBI = (
    "https://kap.org.tr/tr/bildirim-sorgu-sonuc?member={uuid}&disclosureClass=DG"
)
SORGU_KALIBI_FILTRESIZ = "https://kap.org.tr/tr/bildirim-sorgu-sonuc?member={uuid}"

# Konu metni sabit; içerik imzası olarak kullanılıyor (kural 4). KAP'ın
# yazımında sondaki boşluk var ("...Bilgi Formu "), normalize onu da yutar.
KAFIF_KONUSU = "Katılım Finansı İlkeleri Bilgi Formu"

GECMIS_CSV = Path("veri/evren/bildirim_gecmisi.csv")
DURUM_CSV = Path("veri/evren/sorgu_durumu.csv")


class SayfaOkunamadi(RuntimeError):
    """Beklenen çıpaların hiçbiri yok. Bu 'sonuç yok' DEĞİLDİR (kural 7)."""


# --- Ayıklama --------------------------------------------------------------


def rsc_ayiklama(html: str) -> rsc.Ayiklama:
    """RSC yükündeki `disclosureBasic` nesneleri + bozuk sayacı.

    Çözme işi `katilim.rsc`'de: yük bir JS dize literalidir ve naif kaçış
    çözme, özetinde tırnak geçen bildirimleri sessizce düşürüyordu.
    """
    return rsc.deger_nesneleri(html, "disclosureBasic")


def rsc_kayitlari(html: str) -> list[dict]:
    return rsc_ayiklama(html).kayitlar


def checkbox_idleri(html: str) -> list[str]:
    """YEDEK katman: satırdaki checkbox `id`'leri (1.0'ın yolu).

    RSC yükü kaybolursa bu kalır. Birincil kaynak değil; burada asıl işi
    "sayfa gerçekten boş mu yoksa ayrıştırma mı çöktü" ayrımında yapıyor.
    """
    corba = BeautifulSoup(html, "html.parser")
    return [
        i["id"]
        for i in corba.find_all("input", {"name": "notification-checkbox"})
        if i.get("id")
    ]


def sunucu_kayit_sayisi(html: str) -> int | None:
    """Sunucunun kendi saydığı toplam: "92 bildirim bulundu."."""
    m = re.search(r"(\d+)\s*bildirim bulundu", html)
    return int(m.group(1)) if m else None


def bos_sonuc_mu(html: str) -> bool:
    """Boş sonuç metni TABLONUN İÇİNDE mi?

    Aynı metin i18n sözlüğünde de geçiyor, yani gövdede aramak DOLU sayfayı
    boş gösterir. 1.0'daki iki ölçüm hatasının biri tam olarak buydu.
    """
    corba = BeautifulSoup(html, "html.parser")
    tablo = corba.find("table")
    return bool(
        tablo and re.search(r"Bildirim bulunamadı|Sonuç Bulunamadı", tablo.get_text())
    )


def kafif_mi(baslik: str | None) -> bool:
    """Konu metni içerik imzasıyla tanınır (kural 4), konumla değil.

    `normalize` iki tarafa da uygulanıyor: Türkçe harf tuzağı (noktasız 'ı'),
    büyük/küçük harf ve fazla boşluk farkları böyle eleniyor.
    """
    return normalize(KAFIF_KONUSU) in normalize(baslik or "")


def _ts(metin: str | None) -> datetime | None:
    try:
        return datetime.strptime(metin or "", "%d.%m.%Y %H:%M:%S")
    except ValueError:
        return None


@dataclass
class Bildirim:
    """Tek bir KAP bildiriminin kimlik satırı (Spec §1.2'nin alt kümesi)."""

    bildirim_id: int
    konu: str
    gonderim_ts: datetime | None
    yil: int | None = None
    periyot: str | None = None
    sinif: str | None = None          # disclosureClass
    stock_code: str | None = None
    duzeltme_izi: bool | None = None  # RSC 'isChanged'; doğrulanmadı (bkz. 2.3)

    @property
    def kafif_mi(self) -> bool:
        return kafif_mi(self.konu)


@dataclass
class SorguSonucu:
    """Bir sorgu sayfasının ayrıştırılmış hâli.

    `sinif` üç durumun ikisini taşır: DOLU / BOS. Üçüncü durum (sayfa
    okunamadı) burada temsil edilmez — çünkü o bir değer değil, bir
    istisnadır (`SayfaOkunamadi`).
    """

    sinif: str
    bildirimler: list[Bildirim] = field(default_factory=list)
    sunucu_sayisi: int | None = None
    checkbox_sayisi: int = 0
    bozuk_kayit: int = 0

    @property
    def kafifler(self) -> list[Bildirim]:
        return [b for b in self.bildirimler if b.kafif_mi]

    @property
    def eksik_ayiklama(self) -> bool:
        """Sunucu N dedi ama N kayıt çıkaramadıysak: sessiz kayıp uyarısı.

        Bu kontrol boşuna değil: 1.2'nin ilk koşusunda RSC kaçış hatasını
        (DITAS 26 -> 24) tam olarak bu yakaladı.
        """
        return self.bozuk_kayit > 0 or (
            self.sunucu_sayisi is not None
            and self.sunucu_sayisi != len(self.bildirimler)
        )


def ayikla(html: str) -> SorguSonucu:
    """Sorgu sonucu gövdesi -> `SorguSonucu`. Kural 7'yi kodda uygular.

    Üç durum:
      (a) tablo dolu                      -> sinif='DOLU'
      (b) sunucunun bastığı "bulunamadı"  -> sinif='BOS'
      (c) beklenen çıpaların hiçbiri yok  -> SayfaOkunamadi FIRLATIR
    """
    ayiklama = rsc_ayiklama(html)
    kayitlar = ayiklama.kayitlar
    kutular = checkbox_idleri(html)
    sunucu = sunucu_kayit_sayisi(html)
    bos = bos_sonuc_mu(html)

    if not kayitlar and not kutular and sunucu is None and not bos:
        raise SayfaOkunamadi(
            "Ne RSC kaydı, ne checkbox satırı, ne sunucu sayısı, ne boş-sonuç "
            "metni bulundu — sayfa okunamadı. Bu 'bildirim yok' anlamına GELMEZ."
        )

    bildirimler = [
        Bildirim(
            bildirim_id=int(k["disclosureIndex"]),
            konu=(k.get("title") or "").strip(),
            gonderim_ts=_ts(k.get("publishDate")),
            yil=k.get("year"),
            # 'donem' formun kendi etiketi ('6 Aylık' / 'Yıllık'); '-' ise
            # dönem bilgisi yok demektir ve None kalır. Sayısal 'period'
            # alanından etiket TÜRETİLMİYOR: eşleme doğrulanmadı.
            periyot=(k.get("donem") if k.get("donem") not in (None, "", "-") else None),
            sinif=k.get("disclosureClass"),
            stock_code=k.get("stockCode"),
            duzeltme_izi=k.get("isChanged"),
        )
        for k in kayitlar
        if k.get("disclosureIndex") is not None
    ]

    sinif = "BOS" if (sunucu == 0 or (bos and not bildirimler)) else "DOLU"
    return SorguSonucu(
        sinif=sinif,
        bildirimler=bildirimler,
        sunucu_sayisi=sunucu,
        checkbox_sayisi=len(kutular),
        bozuk_kayit=ayiklama.bozuk,
    )


# --- Toplama ---------------------------------------------------------------

# Şirket başına sorgu sonucu. Durum bir YORUM değil, gözlemin sınıfı:
# neden KAFİF bulunamadığı aşağı akışta (1.4, 4.0) ayrı ayrı ele alınacak.
DURUM_KAFIF_VAR = "KAFIF_VAR"
DURUM_KAFIF_YOK = "KAFIF_YOK"          # sayfa dolu ama KAFİF satırı yok
DURUM_BOS_SONUC = "BOS_SONUC"          # sunucu "bildirim bulunamadı" dedi
DURUM_OKUNAMADI = "SAYFA_OKUNAMADI"    # kural 7 — hata, boş değil
DURUM_CEKIM_HATASI = "CEKIM_HATASI"
DURUM_MUAF = "MUAF_SORGULANMADI"


@dataclass
class SirketDurumu:
    uuid: str
    tickerlar: list[str]
    unvan: str
    durum: str
    kafif_sayisi: int = 0
    toplam_bildirim: int = 0
    sorgu_tarihi: str = ""
    not_: str = ""


@dataclass
class Toplama:
    satirlar: list[dict] = field(default_factory=list)      # ticker x bildirim
    durumlar: list[SirketDurumu] = field(default_factory=list)
    uyarilar: list[str] = field(default_factory=list)

    @property
    def kafif_kimlikleri(self) -> set[int]:
        """1.4'ün indireceği BENZERSİZ form sayısı.

        Satır sayısı değil: çoklu kodlu şirkette aynı bildirim birden çok
        ticker satırında görünür ama bir kez indirilir.
        """
        return {s["bildirim_id"] for s in self.satirlar}


def _uuid_gruplari(sirketler) -> dict[str, list]:
    """uuid -> o uuid'e bağlı şirket satırları (pay kodları)."""
    gruplar: dict[str, list] = {}
    for s in sirketler:
        gruplar.setdefault(s.kap_member_uuid, []).append(s)
    return gruplar


def gecmisi_topla(
    sirketler,
    cekici,
    *,
    ilerleme=None,
    kontrol_noktasi=None,
    kontrol_araligi: int = 50,
) -> Toplama:
    """Muaf olmayan her tüzel kişi için KAFİF kimliklerini toplar.

    Muafiyeti `None` (belirsiz) olan şirket **sorgulanır**: yanlış muafiyet
    şirketi panelden sessizce düşürür, fazladan sorgulamak yalnız istek
    harcar (1.1'in asimetri kuralı).
    """
    from .cekici import ÇekimHatası

    toplama = Toplama()
    bugun = date.today().isoformat()
    gruplar = _uuid_gruplari(sirketler)
    sirali = sorted(gruplar.items(), key=lambda kv: gruplar[kv[0]][0].ticker)

    for sira, (uuid, grup) in enumerate(sirali, 1):
        tickerlar = [s.ticker for s in grup]
        unvan = grup[0].unvan
        durum = SirketDurumu(
            uuid=uuid, tickerlar=tickerlar, unvan=unvan,
            durum=DURUM_MUAF, sorgu_tarihi=bugun,
        )

        # Muafiyet: True ise sorgulanmaz. None (belirsiz) sorgulanır.
        if all(s.mali_sektor_muaf is True for s in grup):
            toplama.durumlar.append(durum)
            continue

        url = SORGU_KALIBI.format(uuid=uuid)
        try:
            html = cekici.getir(url)
        except ÇekimHatası as e:
            durum.durum = DURUM_CEKIM_HATASI
            durum.not_ = str(e)[:160]
            toplama.durumlar.append(durum)
            toplama.uyarilar.append(f"{'/'.join(tickerlar)}: {e}")
            if ilerleme:
                ilerleme(sira, len(sirali), durum)
            continue

        try:
            sonuc = ayikla(html)
        except SayfaOkunamadi as e:
            # Kural 7: bu bir arıza, "bildirim yok" değil. Sessizce
            # geçilirse şirket panelden sessizce düşer.
            durum.durum = DURUM_OKUNAMADI
            durum.not_ = str(e)[:160]
            toplama.durumlar.append(durum)
            toplama.uyarilar.append(f"{'/'.join(tickerlar)}: SAYFA OKUNAMADI")
            if ilerleme:
                ilerleme(sira, len(sirali), durum)
            continue

        kafifler = sonuc.kafifler
        durum.toplam_bildirim = len(sonuc.bildirimler)
        durum.kafif_sayisi = len(kafifler)
        if sonuc.sinif == "BOS":
            durum.durum = DURUM_BOS_SONUC
        elif kafifler:
            durum.durum = DURUM_KAFIF_VAR
        else:
            durum.durum = DURUM_KAFIF_YOK

        if sonuc.eksik_ayiklama:
            toplama.uyarilar.append(
                f"{'/'.join(tickerlar)}: sunucu {sonuc.sunucu_sayisi} kayıt dedi, "
                f"{len(sonuc.bildirimler)} ayıklandı"
            )

        # Doğru şirketi sorguladığımızın bağımsız kontrolü: bildirimin kendi
        # pay kodu evrendeki kodlarla kesişmeli. Kesişmiyorsa uuid eşlemesi
        # bozuk demektir ve bu SESSİZ kalmamalı.
        for b in kafifler:
            kodlar = {k.strip() for k in (b.stock_code or "").split(",") if k.strip()}
            if kodlar and not (kodlar & set(tickerlar)):
                toplama.uyarilar.append(
                    f"KOD UYUŞMAZLIĞI {'/'.join(tickerlar)} (uuid {uuid[:8]}…): "
                    f"bildirim {b.bildirim_id} kodu {sorted(kodlar)}"
                )

        # Sorgu ekseni uuid, panel ekseni ticker: sonucu kodlara dağıt.
        for b in kafifler:
            for ticker in tickerlar:
                toplama.satirlar.append(
                    {
                        "ticker": ticker,
                        "bildirim_id": b.bildirim_id,
                        "yil": b.yil,
                        "periyot": b.periyot,
                        "gonderim_ts": b.gonderim_ts,
                        "konu": b.konu,
                        "indirildi_mi": False,
                        "duzeltme_izi": b.duzeltme_izi,
                    }
                )

        toplama.durumlar.append(durum)
        if ilerleme:
            ilerleme(sira, len(sirali), durum)
        if kontrol_noktasi and sira % kontrol_araligi == 0:
            kontrol_noktasi(toplama)

    return toplama


def dg_dogrula(sirketler, cekici, *, ornek: int = 10, tohum: int = 20260807) -> dict:
    """`disclosureClass=DG` filtresi KAFİF kaybettiriyor mu?

    Filtrenin zararsız olduğu yalnız 2 şirkette görülmüştü (1.0, n=2).
    Burada rastgele `ornek` şirkette filtreli ve FİLTRESİZ sayım
    karşılaştırılır. DG dışında bir KAFİF satırı çıkarsa filtre bırakılmalı.

    Örneklem `tohum` ile sabitlenir: aynı tohum aynı şirketleri seçer,
    yani sonuç yeniden üretilebilir.
    """
    import random

    from .cekici import ÇekimHatası

    gruplar = _uuid_gruplari(sirketler)
    adaylar = sorted(
        u for u, g in gruplar.items() if not all(s.mali_sektor_muaf is True for s in g)
    )
    secilen = random.Random(tohum).sample(adaylar, min(ornek, len(adaylar)))

    sonuc = {"ornek": len(secilen), "satirlar": [], "kayip": [], "hata": []}
    for uuid in secilen:
        tickerlar = [s.ticker for s in gruplar[uuid]]
        satir = {"ticker": "/".join(tickerlar), "uuid": uuid}
        try:
            dg = ayikla(cekici.getir(SORGU_KALIBI.format(uuid=uuid)))
            ham = ayikla(cekici.getir(SORGU_KALIBI_FILTRESIZ.format(uuid=uuid)))
        except (ÇekimHatası, SayfaOkunamadi) as e:
            satir["hata"] = f"{type(e).__name__}: {e}"[:160]
            sonuc["hata"].append(satir)
            continue

        dg_idler = {b.bildirim_id for b in dg.kafifler}
        ham_idler = {b.bildirim_id for b in ham.kafifler}
        satir.update(
            {
                "dg_kayit": len(dg.bildirimler),
                "filtresiz_kayit": len(ham.bildirimler),
                "dg_kafif": len(dg_idler),
                "filtresiz_kafif": len(ham_idler),
                "dg_disinda_kafif": sorted(ham_idler - dg_idler),
                "dg_disi_siniflar": sorted(
                    {b.sinif for b in ham.kafifler if b.bildirim_id not in dg_idler}
                ),
            }
        )
        if ham_idler - dg_idler:
            sonuc["kayip"].append(satir)
        sonuc["satirlar"].append(satir)

    sonuc["guvenli"] = not sonuc["kayip"]
    return sonuc


# --- Kalıcılık -------------------------------------------------------------

BASLIKLAR = [
    "ticker", "bildirim_id", "yil", "periyot", "gonderim_ts", "konu",
    "indirildi_mi", "duzeltme_izi",
]
DURUM_BASLIKLARI = [
    "ticker", "uuid", "unvan", "durum", "kafif_sayisi", "toplam_bildirim",
    "sorgu_tarihi", "not",
]


def _bicimle(satir: dict) -> dict:
    ts = satir["gonderim_ts"]
    return {
        "ticker": satir["ticker"],
        "bildirim_id": satir["bildirim_id"],
        "yil": "" if satir["yil"] is None else satir["yil"],
        "periyot": satir["periyot"] or "",
        "gonderim_ts": ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "",
        "konu": satir["konu"],
        "indirildi_mi": "EVET" if satir["indirildi_mi"] else "HAYIR",
        # RSC'deki `isChanged`: DUZENLENEN (düzelten) / DUZELTILEN (düzeltilen).
        # İkisi AYRI taşınıyor — aradaki fark KAP tarafından belgelenmemiş,
        # birleştirmek anlamı kaybetmek olur (2.3).
        "duzeltme_izi": satir.get("duzeltme_izi") or "",
    }


def indirilenleri_koru(satirlar: list[dict], yol: Path | str = GECMIS_CSV) -> list[dict]:
    """Önceki CSV'de `indirildi_mi=EVET` olan kimlikler EVET kalır.

    1.2 yeniden koşulduğunda 1.4'ün işaretlediği indirmeleri sıfırlamak,
    arşivi diskte dururken "yok" göstermek olurdu.
    """
    onceki = {
        s["bildirim_id"] for s in oku(yol) if s["indirildi_mi"]
    }
    for s in satirlar:
        if s["bildirim_id"] in onceki:
            s["indirildi_mi"] = True
    return satirlar


def yaz(satirlar: list[dict], yol: Path | str = GECMIS_CSV) -> Path:
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    sirali = sorted(satirlar, key=lambda s: (s["ticker"], -(s["bildirim_id"] or 0)))
    with open(yol, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=BASLIKLAR)
        w.writeheader()
        w.writerows(_bicimle(s) for s in sirali)
    return yol


def oku(yol: Path | str = GECMIS_CSV) -> list[dict]:
    yol = Path(yol)
    if not yol.exists():
        return []
    with open(yol, newline="", encoding="utf-8-sig") as f:
        return [
            {
                "ticker": r["ticker"],
                "bildirim_id": int(r["bildirim_id"]),
                "yil": int(r["yil"]) if r["yil"] else None,
                "periyot": r["periyot"] or None,
                "gonderim_ts": (
                    datetime.strptime(r["gonderim_ts"], "%Y-%m-%d %H:%M:%S")
                    if r["gonderim_ts"]
                    else None
                ),
                "konu": r["konu"],
                "indirildi_mi": r["indirildi_mi"] == "EVET",
                "duzeltme_izi": (r.get("duzeltme_izi") or "") or None,
            }
            for r in csv.DictReader(f)
        ]


def durumlari_yaz(durumlar: list[SirketDurumu], yol: Path | str = DURUM_CSV) -> Path:
    """Şirket başına sorgu sonucu — negatif kaydın kalıcı hâli.

    `bildirim_gecmisi.csv` yalnız BULUNAN bildirimleri taşır; "bu şirket
    sorgulandı ve KAFİF çıkmadı" bilgisi orada temsil edilemez. O bilgi
    olmadan muaf olan ile beyan vermeyen ayırt edilemez (1.4'ün
    BEYAN_YOK / AYIRT_EDILEMEDI ayrımının girdisi).
    """
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=DURUM_BASLIKLARI)
        w.writeheader()
        for d in sorted(durumlar, key=lambda d: d.tickerlar[0] if d.tickerlar else ""):
            w.writerow(
                {
                    "ticker": "/".join(d.tickerlar),
                    "uuid": d.uuid,
                    "unvan": d.unvan,
                    "durum": d.durum,
                    "kafif_sayisi": d.kafif_sayisi,
                    "toplam_bildirim": d.toplam_bildirim,
                    "sorgu_tarihi": d.sorgu_tarihi,
                    "not": d.not_,
                }
            )
    return yol


# --- Rapor -----------------------------------------------------------------


def ozet(toplama: Toplama) -> dict:
    """Raporun sayıları. 1.4'ün bütçesi buradan çıkıyor."""
    dagilim: dict[str, int] = {}
    for d in toplama.durumlar:
        dagilim[d.durum] = dagilim.get(d.durum, 0) + 1

    sorgulanan = [d for d in toplama.durumlar if d.durum != DURUM_MUAF]
    kafif_sayilari = [d.kafif_sayisi for d in sorgulanan]
    kova = {"0": 0, "1": 0, "2": 0, "3+": 0}
    for n in kafif_sayilari:
        kova[str(n) if n < 3 else "3+"] += 1

    zamanlar = sorted(s["gonderim_ts"] for s in toplama.satirlar if s["gonderim_ts"])
    donemler: dict[str, int] = {}
    for s in toplama.satirlar:
        anahtar = f"{s['yil']}/{s['periyot']}"
        donemler[anahtar] = donemler.get(anahtar, 0) + 1

    return {
        "tuzel_kisi": len(toplama.durumlar),
        "sorgulanan": len(sorgulanan),
        "durum_dagilimi": dagilim,
        "kafif_kova": kova,
        "ticker_satiri": len(toplama.satirlar),
        "benzersiz_form": len(toplama.kafif_kimlikleri),
        "en_eski": zamanlar[0] if zamanlar else None,
        "en_yeni": zamanlar[-1] if zamanlar else None,
        "donem_dagilimi": dict(sorted(donemler.items())),
        "uyari": len(toplama.uyarilar),
    }
