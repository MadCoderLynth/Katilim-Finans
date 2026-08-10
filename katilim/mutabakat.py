"""Kararlarımız ile XKTUM üyeliğinin karşılaştırılması — Faz 4.0.

Ağa çıkmaz: `veri/panel/snapshot_*.csv` ile `veri/evren/endeks_uyeligi.csv`
karşılaştırılır. Bu **nokta-zaman ön mutabakattır**, tarihsel mutabakatın
(4.2) yerini tutmaz; onu erkene çeker ki parser ve karar hataları Faz 3'e
taşınmadan yakalansın.

## Dört sınıf — üçü uyuşmazlık DEĞİL

Çelişkiyi doğrudan "uyuşmazlık" saymak, modelleme boşluğunu hipotez hatası
gibi gösterir. Bu yüzden her çelişki önce üç açıklamaya karşı sınanır:

1. **KAPSAM** — kararımız `KAPSAM_DISI` / `BEYAN_YOK` / `AYIRT_EDILEMEDI` /
   `BELIRSIZ`, ya da pay kodu XKTUM'un **pazar ön şartını** sağlamıyor.
2. **DÖNEM UYUMSUZLUĞU** — elimizdeki KAFİF, endeksin son yürürlük
   tarihinden (1 May / 1 Eki) SONRA yayımlanmış; endeks onu henüz
   görmemiş olabilir. Çelişki beklenen davranıştır.
3. **KOD AYRIŞMASI** — aynı tüzel kişinin bir pay kodu endekste, diğeri
   değil. Likidite ve fiili dolaşım şartları kod bazında değerlendirildiği
   için bu **kriter kaynaklı değildir** ve H1–H4'ün reddi sayılmaz.
4. **GERÇEK UYUŞMAZLIK** — üçü de geçerli değil. Asıl inceleme konusu.

## MUAF ≠ ELENMİŞ

Spec §0.4'ün uyarısı burada koda giriyor: **muafiyet uygunsuzluk değil,
kapsam dışılıktır ve endeks üyeliğini engellemez.** Katılım esaslı finans
kuruluşları (ALBRK katılım bankası, KTLEV tasarruf finansman) KAFİF
doldurmuyor ama XKTUM üyesi. `KAPSAM_DISI` bir kaydı "elenmiş" saymak
4.0'ın uyuşmazlık oranını sahte biçimde şişirir.

## H5 sınanmıyor

`h5_ayirt_edici` işaretli 19 kaydın yalnız 1'i farklı KARAR üretiyor ve o
da geçersiz kılınmış bir düzeltme (1.4b ölçümü). Bu modül H5 hakkında
sonuç üretmez; onun yerine `oran_ayrisiyor` ile `is_duzeltme` ilişkisini
ÖLÇER — "formun özeti bayat olabilir" örüntüsü 2.3'ü bağlıyor.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

XKTUM_ADI = "BIST KATILIM TUM"

# Referans tabloları (4.1 üretti). Takvim BURADAN OKUNUR.
DONEM_CSV = Path("veri/referans/xktum_donemler.csv")
OLAY_CSV = Path("veri/referans/xktum_olaylar.csv")

# ⚠ `REVIZYON_AYLARI = (5, 10)` SİLİNDİ (4.2, 10 Ağu 2026).
#
# Takvim düzenli değil — 4.1 kaynağın kendi başlıklarından ölçtü:
#     01.07.2024 → 01.12.2024 → 01.05.2025 → 01.10.2025 → 01.05.2026
# 2024'te Temmuz/Aralık'tı; 01.10.2025–30.04.2026 yedi ay sürdü. Ay
# sabitinden türetmek 01.03.2025 için "01.10.2024" derdi, gerçeği
# 01.12.2024 — tarihsel mutabakatta sahte uyuşmazlık üretirdi.
#
# İkinci düzeltme: **kesim noktası yürürlük değil DUYURU tarihidir.**
# BIST listeyi 4–7 gün önce duyuruyor (ölçüldü n=5); duyurudan sonra
# yayımlanan KAFİF o revizyonu etkileyemez. Yürürlük tarihini kullanmak
# BIST'e görmediği veriyi görmüş gibi davranmak olurdu.

# XKTUM ön şartı (spec §0.4): pay kodu bu pazarlardan birinde işlem görmeli.
ON_SART_PAZARLAR = ("YILDIZ PAZAR", "ANA PAZAR", "ALT PAZAR")

UYGUN_KARARLAR = ("UYGUN", "TOLERANSTA")
KAPSAM_KARARLARI = ("KAPSAM_DISI", "BEYAN_YOK", "AYIRT_EDILEMEDI", "BELIRSIZ")

SINIF_UYUMLU = "UYUMLU"
SINIF_KAPSAM = "KAPSAM"
SINIF_DONEM = "DONEM_UYUMSUZLUGU"
SINIF_KOD = "KOD_AYRISMASI"
SINIF_GERCEK = "GERCEK_UYUSMAZLIK"
SINIF_PANELDE_YOK = "PANELDE_YOK"


class MutabakatGirdisiYok(RuntimeError):
    """Girdi dosyası yok. 'Uyuşmazlık yok' DEĞİLDİR (kural 7)."""


@dataclass(frozen=True)
class Donem:
    """Bir endeks revizyon dönemi. Tarihler ÖLÇÜLDÜ, türetilmedi (4.1)."""
    baslangic: date          # yürürlük
    bitis: date
    duyuru: date             # gerçek veri kesim noktası
    kaynak_dosya: str

    @property
    def etiket(self) -> str:
        return f"{self.baslangic:%Y-%m}"


def revizyon_donemleri(donem_csv: Path | str = DONEM_CSV) -> list[Donem]:
    """Revizyon takvimini referans tablosundan okur — ay sabitinden DEĞİL."""
    satirlar = _oku(Path(donem_csv), "revizyon dönemleri")
    if not satirlar:
        raise MutabakatGirdisiYok(
            f"revizyon dönemi tablosu satırsız: {donem_csv} — "
            "takvim bilinmeden hiçbir kesim noktası hesaplanamaz"
        )
    donemler = []
    for r in satirlar:
        if not r.get("duyuru_tarihi"):
            # Kural 7: duyurusuz dönem sessizce yürürlük tarihine düşmez.
            raise MutabakatGirdisiYok(
                f"{r['donem_baslangic']} döneminin duyuru tarihi yok — "
                "yürürlük tarihine düşmek BIST'e görmediği veriyi atfeder"
            )
        donemler.append(Donem(
            baslangic=date.fromisoformat(r["donem_baslangic"]),
            bitis=date.fromisoformat(r["donem_bitis"]),
            duyuru=date.fromisoformat(r["duyuru_tarihi"]),
            kaynak_dosya=r["kaynak_dosya"],
        ))
    return sorted(donemler, key=lambda d: d.baslangic)


def son_revizyon(bugun: date, donemler: list[Donem] | None = None) -> date:
    """Verilen tarihte yürürlükte olan revizyonun BAŞLANGICI.

    Takvim `donemler`den gelir (4.1 ölçümü). Geriye uyumluluk için
    parametre isteğe bağlı; verilmezse referans tablosu okunur.
    """
    donemler = donemler if donemler is not None else revizyon_donemleri()
    gecmis = [d for d in donemler if d.baslangic <= bugun]
    if not gecmis:
        raise MutabakatGirdisiYok(
            f"{bugun:%d.%m.%Y} takvimin başlangıcından önce — "
            f"en eski dönem {donemler[0].baslangic:%d.%m.%Y}"
        )
    return gecmis[-1].baslangic


def kesim_noktasi(bugun: date, donemler: list[Donem] | None = None) -> date:
    """Yürürlükteki revizyonun DUYURU tarihi — gerçek veri kesim noktası."""
    donemler = donemler if donemler is not None else revizyon_donemleri()
    bas = son_revizyon(bugun, donemler)
    return next(d.duyuru for d in donemler if d.baslangic == bas)


# --- Girdiler --------------------------------------------------------------


def _oku(yol: Path, ad: str) -> list[dict]:
    """Dosya YOKSA hata. Dosya var ama satırsızsa bu ayrı bir durumdur.

    Kural 7'nin aynısı: "kayıt yok" ile "okuyamadım" karıştırılmaz.
    Boşluğun zehirleyici olduğu yerde çağıran ayrıca denetliyor.
    """
    if not Path(yol).exists():
        raise MutabakatGirdisiYok(f"{ad} yok: {yol}")
    with open(yol, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def xktum_uyeleri(endeks_csv: Path | str) -> set[str]:
    """`BIST KATILIM TÜM` üyeliği. Karşılaştırma **ticker düzeyinde**.

    Dosya satırsızsa hata fırlatılır: sessizce boş küme dönmek "kimse
    XKTUM'da değil" demek olur ve TÜM panel uyuşmazlık gibi görünür.
    Satır var ama XKTUM üyesi yoksa bu gerçek (ve alarm verici) bir
    ölçümdür, hata değil.
    """
    satirlar = _oku(Path(endeks_csv), "endeks üyeliği")
    if not satirlar:
        raise MutabakatGirdisiYok(
            f"endeks üyeliği dosyası satırsız: {endeks_csv} — "
            "boş küme dönmek tüm paneli uyuşmazlık gösterirdi"
        )
    uyeler = set()
    for r in satirlar:
        ad = (r["endeks_adi"] or "").upper().replace("Ü", "U").strip()
        if ad == XKTUM_ADI:
            uyeler.add(r["ticker"])
    return uyeler


def son_kararlar(panel_csv: Path | str) -> dict[str, dict]:
    """Pay kodu başına EN GEÇ bildirim (look-ahead disiplini: `gonderim_ts`).

    Dönem etiketi kronoloji taşımıyor (futbol kulüpleri "2024/Yıllık"ı
    Ağustos 2025'te veriyor), bu yüzden sıralama zaman damgasıyla.
    """
    satirlar = _oku(Path(panel_csv), "panel")
    if not satirlar:
        raise MutabakatGirdisiYok(
            f"panel satırsız: {panel_csv} — karşılaştırılacak karar yok"
        )
    # İki panel şeması destekleniyor: snapshot (`gonderim_ts`) ve tolerans
    # zincirli panel (`gecerlilik_baslangic` + `gecerli_kayit`). İkincisinde
    # yalnız dönemin GEÇERLİ kaydı dikkate alınır (spec §3.2): düzeltilmiş
    # eski kayıtlar panelde durur ama "bugünkü karar" onlar değildir.
    ts_alan = "gonderim_ts" if "gonderim_ts" in satirlar[0] else "gecerlilik_baslangic"
    gecerli_alan = "gecerli_kayit" if "gecerli_kayit" in satirlar[0] else None

    son: dict[str, dict] = {}
    for r in satirlar:
        if gecerli_alan and r.get(gecerli_alan) != "EVET":
            continue
        t = r["ticker"]
        if t not in son or (r[ts_alan] or "") > (son[t][ts_alan] or ""):
            son[t] = r
    # Karşılaştırma kodu `gonderim_ts` bekliyor; şemayı normalize et.
    if ts_alan != "gonderim_ts":
        for r in son.values():
            r["gonderim_ts"] = r[ts_alan]
    return son


def beyan_durumlari(beyan_csv: Path | str) -> dict[str, str]:
    return {r["ticker"]: r["durum"] for r in _oku(Path(beyan_csv), "beyan durumu")}


# --- Karşılaştırma ---------------------------------------------------------


@dataclass
class Satir:
    ticker: str
    unvan: str
    uuid: str
    pazar: str | None
    xktum_uyesi: bool
    bizim_karar: str
    red_kodlari: str
    gonderim_ts: datetime | None
    sinif: str
    sebep: str
    yanlis_pozitif: bool = False   # biz UYGUN, BIST dışarıda — pahalı hata


@dataclass
class Mutabakat:
    satirlar: list[Satir] = field(default_factory=list)
    revizyon: date | None = None

    def sinif_dagilimi(self) -> dict[str, int]:
        d: dict[str, int] = {}
        for s in self.satirlar:
            d[s.sinif] = d.get(s.sinif, 0) + 1
        return dict(sorted(d.items(), key=lambda kv: -kv[1]))

    @property
    def gercek_uyusmazliklar(self) -> list[Satir]:
        return [s for s in self.satirlar if s.sinif == SINIF_GERCEK]

    @property
    def panelde_yok(self) -> list[Satir]:
        return [s for s in self.satirlar if s.sinif == SINIF_PANELDE_YOK]

    def uyusmazlik_orani(self) -> tuple[float, int, int]:
        """(oran, gerçek uyuşmazlık, karşılaştırılabilir kayıt).

        Payda YALNIZ karşılaştırılabilir kayıtlar: kapsam dışı, dönem
        uyumsuz, kod ayrışması ve panelde olmayanlar hariç. Bunları paydaya
        koymak oranı sahte biçimde düşürür.
        """
        karsilastirilabilir = [
            s for s in self.satirlar if s.sinif in (SINIF_UYUMLU, SINIF_GERCEK)
        ]
        gercek = len(self.gercek_uyusmazliklar)
        n = len(karsilastirilabilir)
        return (gercek / n if n else 0.0), gercek, n


def karsilastir(
    sirketler,
    *,
    panel_csv: Path | str,
    endeks_csv: Path | str,
    beyan_csv: Path | str,
    bugun: date | None = None,
) -> Mutabakat:
    bugun = bugun or date.today()
    donemler = revizyon_donemleri()
    revizyon = son_revizyon(bugun, donemler)
    # 4.2 düzeltmesi: dönem denetimi YÜRÜRLÜK değil DUYURU tarihine bakar.
    kesim = kesim_noktasi(bugun, donemler)
    uyeler = xktum_uyeleri(endeks_csv)
    kararlar = son_kararlar(panel_csv)
    beyanlar = beyan_durumlari(beyan_csv)

    # Kod ayrışması için: aynı uuid'in kodlarından biri endekste mi?
    uuid_kodlari: dict[str, list[str]] = {}
    for s in sirketler:
        uuid_kodlari.setdefault(s.kap_member_uuid, []).append(s.ticker)

    m = Mutabakat(revizyon=revizyon)
    for s in sirketler:
        uye = s.ticker in uyeler
        satir = kararlar.get(s.ticker)

        if satir is None:
            # Panelde satırı yok: kararı beyan durumundan geliyor.
            karar = beyanlar.get(s.ticker, "BEYAN_YOK")
            if karar == "BEYAN_VAR":       # panel satırı yoksa tutarsızlık
                karar = "BELIRSIZ"
            ts = None
            kodlar = ""
        else:
            karar = satir["karar"]
            kodlar = satir["red_kodlari"]
            ts = (
                datetime.strptime(satir["gonderim_ts"], "%Y-%m-%d %H:%M:%S")
                if satir["gonderim_ts"] else None
            )

        uygun = karar in UYGUN_KARARLAR
        sinif, sebep = _siniflandir(
            s, karar, uygun, uye, ts, revizyon, kesim, uyeler, uuid_kodlari,
            satir is None
        )
        m.satirlar.append(
            Satir(
                ticker=s.ticker, unvan=s.unvan, uuid=s.kap_member_uuid,
                pazar=s.pazar, xktum_uyesi=uye, bizim_karar=karar,
                red_kodlari=kodlar, gonderim_ts=ts, sinif=sinif, sebep=sebep,
                yanlis_pozitif=(uygun and not uye and sinif == SINIF_GERCEK),
            )
        )
    return m


def _siniflandir(
    s, karar, uygun, uye, ts, revizyon, kesim, uyeler, uuid_kodlari, panelde_yok
) -> tuple[str, str]:
    # 1) XKTUM üyesi ama panelde hiç satırı yok — matrise girmiyor.
    #    Çözülmeden mutabakat oranı anlamsız (spec §0.4 kutusu).
    if uye and panelde_yok:
        return SINIF_PANELDE_YOK, f"XKTUM üyesi ama panelde kaydı yok ({karar})"

    # 2) KAPSAM — kararımız zaten bir "uygunluk yargısı" DEĞİL.
    #    Uyum denetiminden ÖNCE geliyor, çünkü görüşümüz olmayan bir kayıt
    #    ne uyumlu ne uyumsuz sayılabilir. `BEYAN_YOK` bir şirketin XKTUM
    #    dışında olması "kararımız tuttu" demek değildir — o kaydı UYUMLU
    #    saymak mutabakat oranını sahte biçimde iyileştirir.
    #    MUAF ≠ ELENMİŞ: muafiyet endeks üyeliğini engellemez (spec §0.4).
    if karar in KAPSAM_KARARLARI:
        return SINIF_KAPSAM, f"kararımız uygunluk yargısı değil: {karar}"

    if uygun == uye:
        return SINIF_UYUMLU, ""

    # --- Çelişki var; kalan iki açıklamaya karşı sınanıyor ----------------

    # 2b) KAPSAM — XKTUM'un pazar ön şartı sağlanmıyor (spec §0.4).
    #     Biz UYGUN desek de bu kod endekse giremez.
    if not uye and uygun:
        pazar = s.pazar or ""
        if not any(p in pazar for p in ON_SART_PAZARLAR):
            return SINIF_KAPSAM, f"XKTUM pazar ön şartı yok (pazar: {pazar or '—'})"

    # 3) DÖNEM UYUMSUZLUĞU — KAFİF, revizyonun DUYURUSUNDAN sonra yayımlandı.
    #    Ölçüt yürürlük değil duyuru (4.2): BIST listeyi 4-7 gün önce
    #    açıklıyor, o andan sonra gelen beyanı görmüş olamaz. Yürürlük
    #    tarihini kullanmak bu sınıfı olduğundan dar gösteriyordu (7 -> 18).
    if ts and ts.date() > kesim:
        return SINIF_DONEM, (
            f"KAFİF {ts:%d.%m.%Y}, revizyon duyurusu {kesim:%d.%m.%Y} "
            f"(yürürlük {revizyon:%d.%m.%Y}) — endeks bunu görmüş olamaz"
        )

    # 4) KOD AYRIŞMASI — aynı tüzel kişinin başka kodu bizimkinden farklı.
    kardesler = [t for t in uuid_kodlari.get(s.kap_member_uuid, []) if t != s.ticker]
    if kardesler and any((t in uyeler) != uye for t in kardesler):
        return SINIF_KOD, (
            f"aynı tüzel kişinin diğer kodu farklı: {', '.join(kardesler)} "
            "(likidite/fiili dolaşım kaynaklı, kriter kaynaklı değil)"
        )

    return SINIF_GERCEK, f"karar {karar}, XKTUM {'içinde' if uye else 'dışında'}"


# ===========================================================================
# DEĞİŞİM BAZLI MUTABAKAT — Faz 4.2
# ===========================================================================
#
# 4.0 DURUM karşılaştırmasıydı ve bilgilendirici vaka sayısı 2'ydi: kayıtların
# çoğu uygunluğun hiç değişmediği kararlı vakalardı ve orada yarım çalışan bir
# motor da uyuşur. Buradaki soru farklı:
#
#     Resmî liste bir sınırda DEĞİŞTİĞİNDE, bizim panelimiz de değişti mi
#     ve aynı yönde mi?
#
# Örneklem 4.1'in ürettiği giriş/çıkış olayları. Kararlı vakalar dışarıda —
# H1–H4 ilk kez ayırt edici bir kümeyle karşılaşıyor.
#
# ## İki kademe, çünkü panelin derinliği asimetrik
#
# Kesim noktası bir revizyonun DUYURU tarihi (yürürlük değil). Panelimiz
# 05.08.2025'te başlıyor:
#
#   * **A kademesi — SONRA durumu.** Kesim noktasındaki kararımız, olayın
#     sonrasındaki resmî durumla uyuşuyor mu? İki sınırda da uygulanabilir.
#   * **B kademesi — YÖN.** Kararımız sınırın iki yanında farklı mı? Yalnız
#     önceki kesim noktasında da kaydımız varsa uygulanabilir; 2025-10
#     sınırında önceki kesim 25.04.2025 ve o tarihte hiç kaydımız yok.
#
# B'yi uygulanamadığı yerde "eşleşmedi" saymak veri eksikliğini hipotez
# hatası gibi gösterirdi (kural 2'nin mutabakat karşılığı).

SINIF_ESLESTI = "ESLESTI"
SINIF_YANLIS_POZITIF = "YANLIS_POZITIF"      # BIST çıkardı, biz UYGUN diyoruz
SINIF_YANLIS_NEGATIF = "YANLIS_NEGATIF"      # BIST aldı, biz UYGUN_DEGIL
SINIF_OLAGANUSTU = "OLAGANUSTU_CIKARMA_ADAYI"
SINIF_GORUS_YOK = "GORUS_YOK"

YON_AYNI = "AYNI_YON"
YON_DEGISIM_YOK = "DEGISIM_YOK"
YON_TERS = "TERS_YON"
YON_OLCULEMEZ = "OLCULEMEZ"

# Kapı → hipotez. Prompt 4.2'nin verdiği eşleme; G1/G3 kesin kapılar ve
# arkalarında sınanacak bir hipotez YOK — "hipotez yok" da bir bilgidir.
KAPI_HIPOTEZ = {
    "G1_ESAS_SOZLESME": "—",
    "G2_IMTIYAZ": "H2",
    "G3_MADDE_15": "—",
    "G4_DOGRUDAN_AYKIRI": "H1",
    "G5_GELIR": "H3",
    "G6_VARLIK": "H3",
    "G7_BORC": "H3",
}


@dataclass
class OlayKarsilastirmasi:
    ticker: str
    donem: str                     # yürürlük tarihi (2025-10-01)
    olay: str                      # GIREN | CIKAN
    kesim: date                    # bu revizyonun duyuru tarihi
    onceki_kesim: date | None
    onceki_karar: str | None
    simdiki_karar: str | None
    simdiki_kodlar: str
    simdiki_ts: datetime | None
    self_check: str
    onceki_donem_tolerans: str
    sinif: str
    yon: str
    on_teshis: str
    hipotez: str
    onceki_cikis: str = ""      # daha önce endeksten çıkmış mıydı?

    @property
    def uyusmazlik(self) -> bool:
        return self.sinif in (SINIF_YANLIS_POZITIF, SINIF_YANLIS_NEGATIF)


@dataclass
class DegisimMutabakati:
    donem: Donem
    onceki_donem: Donem | None
    olaylar: list[OlayKarsilastirmasi] = field(default_factory=list)

    def sinif_dagilimi(self) -> dict[str, int]:
        d: dict[str, int] = {}
        for o in self.olaylar:
            d[o.sinif] = d.get(o.sinif, 0) + 1
        return dict(sorted(d.items(), key=lambda kv: -kv[1]))

    @property
    def uyusmazliklar(self) -> list[OlayKarsilastirmasi]:
        return [o for o in self.olaylar if o.uyusmazlik]

    @property
    def yanlis_pozitifler(self) -> list[OlayKarsilastirmasi]:
        return [o for o in self.olaylar if o.sinif == SINIF_YANLIS_POZITIF]

    def matris(self) -> dict[tuple[str, str], int]:
        """Dört hücre: (bizim yargı, BIST sonrası durum) -> sayı.

        Yalnız görüşümüz olan olaylar. `GORUS_YOK` matrise girmez —
        görüşü olmayan kaydı bir hücreye koymak oranı bozar (4.0 dersi).
        """
        h: dict[tuple[str, str], int] = {}
        for o in self.olaylar:
            if o.sinif in (SINIF_GORUS_YOK, SINIF_OLAGANUSTU):
                continue
            bizim = "UYGUN" if o.simdiki_karar in UYGUN_KARARLAR else "UYGUN_DEGIL"
            bist = "ICERIDE" if o.olay == "GIREN" else "DISARIDA"
            h[(bizim, bist)] = h.get((bizim, bist), 0) + 1
        return h

    def uyusmazlik_orani(self) -> tuple[float, int, int]:
        """(oran, uyuşmazlık, karşılaştırılabilir olay).

        Payda yalnız görüşümüz olan olaylar: `GORUS_YOK` ve olağanüstü
        çıkarma adayları hariç. Onları paydaya koymak oranı sahte biçimde
        düşürür (4.0'da aynı hata düzeltilmişti).
        """
        n = sum(1 for o in self.olaylar
                if o.sinif not in (SINIF_GORUS_YOK, SINIF_OLAGANUSTU))
        k = len(self.uyusmazliklar)
        return (k / n if n else 0.0), k, n


def xktum_olaylari(olay_csv: Path | str = OLAY_CSV) -> dict[str, list[tuple[str, str]]]:
    """Dönem başlangıcı -> [(ticker, GIREN|CIKAN)]."""
    satirlar = _oku(Path(olay_csv), "XKTUM olayları")
    if not satirlar:
        raise MutabakatGirdisiYok(
            f"olay tablosu satırsız: {olay_csv} — "
            "'hiç değişim olmadı' ile 'tabloyu okuyamadım' aynı şey değil"
        )
    d: dict[str, list[tuple[str, str]]] = {}
    for r in satirlar:
        d.setdefault(r["donem_baslangic"], []).append((r["ticker"], r["olay"]))
    return d


def panel_zaman_serisi(panel_csv: Path | str) -> dict[str, list[dict]]:
    """Pay kodu -> gönderim sırasına dizilmiş TÜM panel satırları.

    `gecerli_kayit` süzgeci YOK ve bu bilinçli: bir kesim noktasında
    geçerli olan kayıt, bugün geçersiz kılınmış olabilir. Look-ahead
    disiplini (spec §5.1) o günün canlı etiketini ister.
    """
    satirlar = _oku(Path(panel_csv), "panel")
    if not satirlar:
        raise MutabakatGirdisiYok(f"panel satırsız: {panel_csv}")
    ts_alan = ("gonderim_ts" if "gonderim_ts" in satirlar[0]
               else "gecerlilik_baslangic")
    seri: dict[str, list[dict]] = {}
    for r in satirlar:
        r["_ts"] = r.get(ts_alan) or ""
        seri.setdefault(r["ticker"], []).append(r)
    for v in seri.values():
        v.sort(key=lambda r: r["_ts"])
    return seri


def karar_zamanda(seri: dict[str, list[dict]], ticker: str,
                  tarih: date) -> dict | None:
    """`tarih` gününün SONUNA kadar yayımlanmış EN GEÇ panel satırı.

    Look-ahead yok: sonraki bildirimler görünmez.
    """
    sinir = f"{tarih:%Y-%m-%d} 23:59:59"
    uygun = [r for r in seri.get(ticker, []) if r["_ts"] and r["_ts"] <= sinir]
    return uygun[-1] if uygun else None


def _on_teshis(olay: str, satir: dict | None, karar: str | None,
               evrende: bool) -> tuple[str, str]:
    """(ön teşhis, şüphelenilen hipotez) — otomatik, sıralı."""
    if satir is None:
        return "kesim noktasında panel kaydımız yok", "—"
    if karar in KAPSAM_KARARLARI:
        if karar == "BELIRSIZ":
            return "kararımız BELİRSİZ — veri eksikliği (kural 2)", "—"
        return f"kararımız uygunluk yargısı değil: {karar}", "—"

    # Parser şüphesi her şeyin önünde: self-check kaldıysa oranlara ve
    # dolayısıyla G5-G7'ye güvenilmez.
    if (satir.get("self_check") or "").upper().startswith("KAL"):
        return "self-check KALDI — parser/kaynak şüphesi, oranlar güvenilmez", "—"

    kodlar = [k.strip() for k in (satir.get("red_kodlari") or "").split(",")
              if k.strip()]
    # Tolerans zinciri devredeyse şüphe H4'te: zincir şirket bazında mı
    # yürüyor, kriter bazında mı?
    if satir.get("onceki_donem_tolerans") == "EVET":
        return ("tolerans zinciri devrede (önceki dönem TOLERANSTA)", "H4")
    if karar == "TOLERANSTA":
        return ("tolerans bandında — zincir/bant sınırı şüphesi", "H4")

    for k in kodlar:
        kok = k.replace("_TOLERANS", "")
        if kok in KAPI_HIPOTEZ:
            hip = KAPI_HIPOTEZ[kok]
            return (f"karar {kok} kapısında verildi", hip)

    if olay == "GIREN" and not kodlar:
        # Biz UYGUN diyoruz ve BIST de aldı; buraya yalnız yön uyuşmazlığı
        # düşer. Kapı yok, dolayısıyla hipotez de yok.
        return "red kodu yok — kararımız temiz", "—"
    if olay == "CIKAN" and not kodlar:
        return ("BIST çıkardı ama bizde red kodu yok — modellenmemiş kriter"
                + ("" if evrende else " (kod evrende yok)"), "H3")
    return "sınıflandırılamadı", "—"


def karsilastir_degisim(
    *,
    panel_csv: Path | str,
    donem: str,
    evren_tickerlari: set[str],
    donem_csv: Path | str = DONEM_CSV,
    olay_csv: Path | str = OLAY_CSV,
) -> DegisimMutabakati:
    """Bir revizyon sınırındaki giriş/çıkışları panelimizle karşılaştırır.

    `donem`: yürürlük tarihi ya da `YYYY-MM` etiketi (`2025-10`).
    """
    donemler = revizyon_donemleri(donem_csv)
    eslesen = [d for d in donemler
               if d.baslangic.isoformat() == donem or d.etiket == donem]
    if not eslesen:
        raise MutabakatGirdisiYok(
            f"{donem} bilinen bir revizyon dönemi değil. Takvim: "
            + ", ".join(d.etiket for d in donemler)
        )
    d = eslesen[0]
    i = donemler.index(d)
    onceki = donemler[i - 1] if i > 0 else None

    olaylar_tablosu = xktum_olaylari(olay_csv)
    # Yeniden giriş tespiti: bu sınırdan ÖNCE bir çıkışı var mıydı?
    onceki_cikislar: dict[str, str] = {}
    for bas, kayitlar in olaylar_tablosu.items():
        if bas >= d.baslangic.isoformat():
            continue
        for t, o in kayitlar:
            if o == "CIKAN" and bas > onceki_cikislar.get(t, ""):
                onceki_cikislar[t] = bas
    bu_donem = olaylar_tablosu.get(d.baslangic.isoformat(), [])
    if not bu_donem:
        raise MutabakatGirdisiYok(
            f"{d.etiket} döneminde hiç giriş/çıkış olayı yok — "
            "referans tablosu eksik olabilir"
        )

    seri = panel_zaman_serisi(panel_csv)
    m = DegisimMutabakati(donem=d, onceki_donem=onceki)

    for ticker, olay in sorted(bu_donem):
        simdiki = karar_zamanda(seri, ticker, d.duyuru)
        oncekisi = (karar_zamanda(seri, ticker, onceki.duyuru)
                    if onceki else None)
        karar = simdiki["karar"] if simdiki else None
        onceki_karar = oncekisi["karar"] if oncekisi else None
        evrende = ticker in evren_tickerlari

        # --- Sınıflandırma -------------------------------------------------
        if simdiki is None or karar in KAPSAM_KARARLARI:
            # Görüşümüz yok. Olağanüstü çıkarma ihtimali burada AYRILIYOR:
            # bugünkü evrende olmayan bir kodun çıkışı, uygunluk kararı
            # değil kotasyon iptali/birleşme olabilir (4.1 sınırı).
            sinif = (SINIF_OLAGANUSTU if olay == "CIKAN" and not evrende
                     else SINIF_GORUS_YOK)
        else:
            uygun = karar in UYGUN_KARARLAR
            if olay == "GIREN":
                sinif = SINIF_ESLESTI if uygun else SINIF_YANLIS_NEGATIF
            else:
                if not uygun:
                    sinif = SINIF_ESLESTI
                elif not evrende:
                    sinif = SINIF_OLAGANUSTU
                else:
                    sinif = SINIF_YANLIS_POZITIF

        # --- Yön (B kademesi) ----------------------------------------------
        if oncekisi is None or simdiki is None:
            yon = YON_OLCULEMEZ
        else:
            o_uygun = onceki_karar in UYGUN_KARARLAR
            s_uygun = karar in UYGUN_KARARLAR
            if o_uygun == s_uygun:
                yon = YON_DEGISIM_YOK
            elif (olay == "GIREN" and s_uygun) or (olay == "CIKAN" and not s_uygun):
                yon = YON_AYNI
            else:
                yon = YON_TERS

        teshis, hipotez = _on_teshis(olay, simdiki, karar, evrende)
        m.olaylar.append(OlayKarsilastirmasi(
            ticker=ticker, donem=d.baslangic.isoformat(), olay=olay,
            kesim=d.duyuru, onceki_kesim=onceki.duyuru if onceki else None,
            onceki_karar=onceki_karar, simdiki_karar=karar,
            simdiki_kodlar=(simdiki.get("red_kodlari") or "") if simdiki else "",
            simdiki_ts=(
                datetime.strptime(simdiki["_ts"], "%Y-%m-%d %H:%M:%S")
                if simdiki and simdiki["_ts"] else None
            ),
            self_check=(simdiki.get("self_check") or "") if simdiki else "",
            onceki_donem_tolerans=(
                (simdiki.get("onceki_donem_tolerans") or "") if simdiki else ""
            ),
            sinif=sinif, yon=yon, on_teshis=teshis, hipotez=hipotez,
            onceki_cikis=onceki_cikislar.get(ticker, ""),
        ))
    return m


def hipotez_ozeti(m: DegisimMutabakati) -> dict[str, dict]:
    """Hangi hipotez kaç olayı karara bağladı ve kaçında tuttu?

    Uyuşmazlık listesi boş çıkabilir; o zaman bu tablo tek bilgilendirici
    çıktıdır. "Uyuşmazlık yok" ile "hipotez sınandı" ayrı şeyler —
    bir hipotez hiç olay karara bağlamadıysa SINANMAMIŞTIR.
    """
    ozet: dict[str, dict] = {}
    for o in m.olaylar:
        if o.sinif in (SINIF_GORUS_YOK, SINIF_OLAGANUSTU):
            continue
        h = o.hipotez or "—"
        d = ozet.setdefault(h, {"olay": 0, "eslesti": 0, "uyusmazlik": 0,
                                "tickerlar": []})
        d["olay"] += 1
        d["eslesti" if o.sinif == SINIF_ESLESTI else "uyusmazlik"] += 1
        d["tickerlar"].append(o.ticker)
    return dict(sorted(ozet.items(), key=lambda kv: -kv[1]["olay"]))


def taban_oran(panel_csv: Path | str, kesim: date) -> tuple[float, int]:
    """Kesim noktasında panelin genel UYGUN oranı — testin GÜCÜ için.

    "0 uyuşmazlık" tek başına bir şey söylemez: motor her şeye aynı yanıtı
    verse ve o yanıt çoğunlukta olsa da düşük uyuşmazlık çıkardı. Taban
    oran yazı-turaya yakınsa örneklem gerçekten ayırt edicidir.
    """
    seri = panel_zaman_serisi(panel_csv)
    kararlar = [karar_zamanda(seri, t, kesim) for t in seri]
    kararlar = [r["karar"] for r in kararlar if r]
    if not kararlar:
        return 0.0, 0
    uygun = sum(1 for k in kararlar if k in UYGUN_KARARLAR)
    return uygun / len(kararlar), len(kararlar)


def degisim_raporu(m: DegisimMutabakati, iz: dict | None = None,
                   taban: tuple[float, int] | None = None) -> str:
    """`MUTABAKAT_{donem}.md` gövdesi."""
    oran, k, n = m.uyusmazlik_orani()
    mat = m.matris()
    o = m.donem
    sat = []
    A = sat.append

    A(f"# Değişim Bazlı Mutabakat — {o.etiket} revizyonu")
    A("")
    A("**Plan adımı:** 4.2 — kararlarımız vs. resmî XKTUM listesi, "
      "**durum değil DEĞİŞİM**")
    A(f"**Endeks dönemi:** {o.baslangic:%d.%m.%Y} – {o.bitis:%d.%m.%Y}")
    A(f"**Kesim noktası:** {o.duyuru:%d.%m.%Y} (DUYURU tarihi — yürürlük "
      f"{o.baslangic:%d.%m.%Y} değil)")
    if m.onceki_donem:
        A(f"**Önceki kesim:** {m.onceki_donem.duyuru:%d.%m.%Y}")
    A(f"**Kaynak:** {o.kaynak_dosya}")
    A("**Ağ isteği: 0.**")
    A("")
    A("> Bu adım 4.0'dan niteliksel olarak farklı. 4.0 nokta-zaman DURUM")
    A("> karşılaştırmasıydı ve kayıtların çoğu uygunluğun hiç değişmediği")
    A("> kararlı vakalardı. Buradaki örneklem yalnız **giriş/çıkış**")
    A("> olayları: resmî liste değiştiğinde bizim de değişip değişmediğimiz.")
    A("")
    A("---")
    A("")
    A("## 1. Karışıklık matrisi")
    A("")
    A("| | BIST içeride (GİREN) | BIST dışarıda (ÇIKAN) |")
    A("|---|---|---|")
    A(f"| **biz UYGUN/TOLERANSTA** | {mat.get(('UYGUN','ICERIDE'),0)} ✔ | "
      f"**{mat.get(('UYGUN','DISARIDA'),0)} YANLIŞ POZİTİF** |")
    A(f"| **biz UYGUN_DEGIL** | {mat.get(('UYGUN_DEGIL','ICERIDE'),0)} yanlış negatif | "
      f"{mat.get(('UYGUN_DEGIL','DISARIDA'),0)} ✔ |")
    A("")
    A(f"**Uyuşmazlık oranı: {k} / {n} = %{oran*100:.2f}**")
    A("")
    A("Payda yalnız görüşümüz olan olaylar. `GORUS_YOK` ve olağanüstü "
      "çıkarma adayları paydaya konmadı — 4.0'da aynı hata düzeltilmişti.")
    A("")
    A(f"Sınıf dağılımı: `{m.sinif_dagilimi()}`")
    A("")
    yon = {}
    for e in m.olaylar:
        yon[e.yon] = yon.get(e.yon, 0) + 1
    A(f"Yön dağılımı: `{yon}`")
    A("")
    if yon.get(YON_OLCULEMEZ) == len(m.olaylar):
        A("⚠ **Yön ÖLÇÜLEMEDİ.** Önceki kesim noktasında "
          f"({m.onceki_donem.duyuru:%d.%m.%Y}) hiç panel kaydımız yok — "
          "panel 05.08.2025'te başlıyor. Bu sınırda yalnız *sonra* durumu "
          "sınanabiliyor; \"değişim gösterdik mi\" sorusu cevaplanamıyor ve "
          "eksik veri **eşleşmeme sayılmadı** (kural 2'nin karşılığı).")
        A("")

    if taban:
        p, tn = taban
        giren = [e for e in m.olaylar
                 if e.olay == "GIREN" and e.sinif not in
                 (SINIF_GORUS_YOK, SINIF_OLAGANUSTU)]
        cikan = [e for e in m.olaylar
                 if e.olay == "CIKAN" and e.sinif not in
                 (SINIF_GORUS_YOK, SINIF_OLAGANUSTU)]
        import math
        log10p = (len(giren) * math.log10(p) + len(cikan) * math.log10(1 - p)
                  if 0 < p < 1 else 0.0)
        A("### Testin gücü — \"0 uyuşmazlık\" kendiliğinden bir şey söylemez")
        A("")
        A(f"Kesim noktasında panelin geneli: **%{p*100:.1f} UYGUN / "
          f"%{(1-p)*100:.1f} UYGUN_DEGIL** (n={tn} pay kodu). Taban oran "
          "yazı-turaya yakın, yani \"hep aynı yanıtı veren\" bir motor bu "
          "örneklemi geçemez.")
        A("")
        A(f"{len(giren)} GİRİŞ'in tamamına UYGUN, {len(cikan)} ÇIKIŞ'ın "
          f"tamamına UYGUN_DEGIL demenin şans eseri olma olasılığı "
          f"≈ **10^{log10p:.0f}**.")
        A("")

    A("## 2. Yanlış pozitifler — pahalı olan hata")
    A("")
    yp = m.yanlis_pozitifler
    if not yp:
        A("**Yok.** BIST'in çıkardığı payların hiçbirine UYGUN demedik.")
    else:
        A("| Ticker | Kararımız | Red kodu | KAFİF | Ön teşhis | Hipotez |")
        A("|---|---|---|---|---|---|")
        for e in yp:
            A(f"| {e.ticker} | {e.simdiki_karar} | `{e.simdiki_kodlar or '—'}` | "
              f"{e.simdiki_ts:%d.%m.%Y} | {e.on_teshis} | {e.hipotez} |")
    A("")

    A("## 3. Tüm uyuşmazlıklar")
    A("")
    if not m.uyusmazliklar:
        A("**Yok.** Görüşümüz olan olayların tamamı resmî listeyle uyuştu.")
    else:
        A("| Ticker | Olay | Kararımız | Gerekçe | BIST | Ön teşhis | Hipotez |")
        A("|---|---|---|---|---|---|---|")
        for e in m.uyusmazliklar:
            A(f"| {e.ticker} | {e.olay} | {e.simdiki_karar} | "
              f"`{e.simdiki_kodlar or '—'}` | "
              f"{'içeride' if e.olay == 'GIREN' else 'dışarıda'} | "
              f"{e.on_teshis} | {e.hipotez} |")
    A("")

    A("## 4. Hipotez bazında — hangisi fiilen sınandı")
    A("")
    A("Bir hipotez hiç olay karara bağlamadıysa **sınanmamıştır**; "
      "\"uyuşmazlık yok\" onu desteklemez.")
    A("")
    A("| Hipotez | Karara bağladığı olay | Eşleşen | Uyuşmazlık | Örnek |")
    A("|---|---|---|---|---|")
    for h, d in hipotez_ozeti(m).items():
        ornek = ", ".join(d["tickerlar"][:4])
        A(f"| {h} | {d['olay']} | {d['eslesti']} | {d['uyusmazlik']} | {ornek} |")
    A("")

    dy = [e for e in m.olaylar if e.yon == YON_DEGISIM_YOK]
    if dy:
        A("### Zamanlama sapması — kararımız sınırın iki yanında AYNI")
        A("")
        A("Bu olaylarda A kademesi tuttu (sonra durumu doğru) ama kararımız "
          "zaten o durumdaydı: **BIST'ten bir dönem erken davranmışız.** "
          "`onceki_cikis` doluysa bu bir YENİDEN GİRİŞ ve gecikme, spec "
          "§2.3'teki H6 adayını (gecikmeli yeniden giriş) doğrudan ilgilendirir.")
        A("")
        A("| Ticker | Olay | Önceki kesimde | Şimdi | Önceki çıkış | Okuma |")
        A("|---|---|---|---|---|---|")
        for e in dy:
            okuma = ("YENİDEN GİRİŞ — H6 adayı" if e.onceki_cikis
                     else "ilk kez giriyor; gecikme likidite/dolaşım şartı olabilir")
            A(f"| {e.ticker} | {e.olay} | {e.onceki_karar} | {e.simdiki_karar} | "
              f"{e.onceki_cikis or '—'} | {okuma} |")
        A("")
        A("⚠ **H6 REVİZE EDİLMEDİ.** Spec §2.3'te aday olarak duruyor ve "
          "kodda karşılığı yok; burada yalnız kanıt birikiyor.")
        A("")

    gy = [e for e in m.olaylar if e.sinif == SINIF_GORUS_YOK]
    ol = [e for e in m.olaylar if e.sinif == SINIF_OLAGANUSTU]
    A("## 5. Görüşümüz olmayan olaylar")
    A("")
    A(f"- **GÖRÜŞ YOK ({len(gy)}):** "
      + (", ".join(f"{e.ticker} ({e.olay})" for e in gy) if gy else "—"))
    A(f"- **OLAĞANÜSTÜ ÇIKARMA ADAYI ({len(ol)}):** "
      + (", ".join(e.ticker for e in ol) if ol else "—"))
    A("")
    A("Olağanüstü çıkarmalar dönemsel değişiklik PDF'lerinde görünmüyor "
      "(4.1 sınırı: EFORC, DAGHL, PEHOL). Bugünkü evrende olmayan bir kodun "
      "çıkışı kotasyon iptali/birleşme olabilir — **uyuşmazlık sayılmadan "
      "önce ayrı sınıflandı.**")
    A("")

    if iz:
        A("## 6. İZ — karar çeviren düzeltme → endeks olayı")
        A("")
        A("2.3'ün 14 karar çeviren düzeltmesi (bir beyan HAYIR↔EVET döndü) "
          "bir endeks olayıyla eşleşiyor mu? **Test simetrik:** eleyen "
          "düzeltme ÇIKIŞ, temizleyen düzeltme GİRİŞ bekler. Sıra şartı "
          "zorunlu — düzeltme olayın kesim noktasından önce olmalı.")
        A("")
        A(f"```")
        A(f"karar çeviren düzeltme   : {iz['karar_ceviren_duzeltme']}")
        A(f"beklenen yönde EŞLEŞEN   : {iz['eslesen']}")
        A(f"TERS yönde               : {iz['ters_yon']}")
        A(f"olay düzeltmeden ÖNCE    : {iz['olay_duzeltmeden_once']}  (sayılmadı)")
        A(f"hiç olay yok             : {iz['hic_olay_yok']}")
        A(f"```")
        A("")
        A("| Ticker | Yön | Değişen beyan | Endeks olayı |")
        A("|---|---|---|---|")
        for e in iz["eslesen_kayitlar"]:
            A(f"| {e['ticker']} | {e['yon']} | `{e['degisen_beyanlar']}` | {e['olay']} |")
        A("")
    return "\n".join(sat) + "\n"


# --- İZ: karar çeviren düzeltme -> endeks çıkışı ---------------------------


def _duzeltme_yonu(degisen_beyanlar: str) -> str:
    """Düzeltme şirketi ELEYEN yönde mi, TEMİZLEYEN yönde mi?

    G1–G4 kapıları "herhangi biri EVET" mantığıyla çalışıyor: bir beyanın
    HAYIR→EVET dönmesi elemeye yeter, tersi ancak son EVET de kalkarsa
    temizler. Bu yüzden tek bir `-> True` bütün düzeltmeyi eleyici yapar.
    """
    if "-> True" in degisen_beyanlar:
        return "ELEYEN"
    if "-> False" in degisen_beyanlar:
        return "TEMIZLEYEN"
    return "BELIRSIZ"


def duzeltme_olay_eslemesi(
    duzeltme_csv: Path | str,
    *,
    olay_csv: Path | str = OLAY_CSV,
    donem_csv: Path | str = DONEM_CSV,
) -> dict:
    """2.3'ün karar çeviren düzeltmelerinin kaçı bir endeks OLAYIYLA eşleşiyor?

    4.1'de görülen iz: ASUZU ve BEYAZ 2025/6 Aylık'ta `b1_1`'i HAYIR→EVET
    düzeltti, ikisi de 01.10.2025'te endeksten çıktı. Düzeltme geldi, sonra
    endeks işledi — G1 kapısının fiilen çalıştığına dair somut kanıt.

    **Test SİMETRİK.** Yalnız çıkışa bakmak testin yarısını atlar:
    `EVET→HAYIR` düzelten şirket kendini *temizliyor* ve beklenen olay
    GİRİŞ'tir. Tek yönlü bakıldığında bu vakalar "eşleşmedi" görünüyordu;
    oysa dördünün üçü tam o sınırda endekse girmiş.

    **Sıra şartı zorunlu:** düzeltme, olayın kesim noktasından ÖNCE
    yayımlanmış olmalı. Sonra gelen düzeltme o olayı açıklayamaz (BORLS
    böyle) — saymak nedenselliği ters çevirmek olurdu.
    """
    olaylar = _oku(Path(olay_csv), "XKTUM olayları")
    donemler = revizyon_donemleri(donem_csv)
    gecmis: dict[str, list[tuple[Donem, str]]] = {}
    for r in olaylar:
        d = next((x for x in donemler
                  if x.baslangic.isoformat() == r["donem_baslangic"]), None)
        if d:
            gecmis.setdefault(r["ticker"], []).append((d, r["olay"]))

    satirlar = _oku(Path(duzeltme_csv), "düzeltme olayları")
    ceviren = [r for r in satirlar if r.get("karar_ceviren_beyan") == "EVET"]

    eslesen, ters_yon, sonradan, olaysiz = [], [], [], []
    for r in ceviren:
        ts = (r.get("duzeltme_gonderim_ts") or "")[:10]
        yon = _duzeltme_yonu(r.get("degisen_beyanlar", ""))
        beklenen = {"ELEYEN": "CIKAN", "TEMIZLEYEN": "GIREN"}.get(yon)
        kayit = {
            "ticker": r["ticker"],
            "donem": f"{r['yil']}/{r['periyot']}",
            "duzeltme_ts": r.get("duzeltme_gonderim_ts", ""),
            "degisen_beyanlar": r.get("degisen_beyanlar", ""),
            "yon": yon,
            "beklenen_olay": beklenen or "—",
            "olay": "",
        }
        adaylar = gecmis.get(r["ticker"], [])
        # Düzeltmeden SONRAKİ ilk kesim noktasındaki olay.
        sonraki = sorted((d for d, _o in adaylar if ts and ts <= d.duyuru.isoformat()),
                         key=lambda d: d.baslangic)
        if sonraki:
            d0 = sonraki[0]
            gerceklesen = next(o for dd, o in adaylar if dd is d0)
            kayit["olay"] = f"{gerceklesen} @ {d0.baslangic:%Y-%m-%d}"
            (eslesen if gerceklesen == beklenen else ters_yon).append(kayit)
        elif adaylar:
            d0 = sorted((d for d, _o in adaylar), key=lambda d: d.baslangic)[-1]
            gerceklesen = next(o for dd, o in adaylar if dd is d0)
            kayit["olay"] = f"{gerceklesen} @ {d0.baslangic:%Y-%m-%d} (DÜZELTMEDEN ÖNCE)"
            sonradan.append(kayit)
        else:
            olaysiz.append(kayit)

    return {
        "karar_ceviren_duzeltme": len(ceviren),
        "eslesen": len(eslesen),
        "ters_yon": len(ters_yon),
        "olay_duzeltmeden_once": len(sonradan),
        "hic_olay_yok": len(olaysiz),
        "eslesen_kayitlar": eslesen,
        "ters_yon_kayitlar": ters_yon,
        "sonradan_kayitlar": sonradan,
        "olaysiz_kayitlar": olaysiz,
    }


# --- Oran ayrışması ile düzeltme ilişkisi ----------------------------------


def oran_ayrismasi_duzeltme_iliskisi(panel_csv: Path | str) -> dict:
    """`oran_ayrisiyor` kayıtlarının kaçı düzeltme bildirimi?

    PNLSN'de sapmanın kaynağı, şirketin kalemi düzeltip TOPLAM satırını
    güncellememesiydi. Örüntü genelse "formun özeti bayat olabilir" bulgusu
    2.3'ü (düzeltme mantığı) ve ileride H5'i bağlar.
    """
    satirlar = _oku(Path(panel_csv), "panel")
    if not satirlar or "oran_ayrisiyor" not in satirlar[0]:
        # Tolerans zincirli panelde bu sütunlar yok; ölçüm snapshot'ta yapılır.
        # Sessizce 0 dönmek "ayrışma yok" demek olurdu (kural 7).
        return {"uygulanamaz": "panel şemasında oran sütunları yok"}
    ayrisan = [r for r in satirlar if r["oran_ayrisiyor"] == "EVET"]
    h5 = [r for r in ayrisan if r["h5_ayirt_edici"] == "EVET"]
    return {
        "panel_satiri": len(satirlar),
        "oran_ayrisiyor": len(ayrisan),
        "bunlardan_duzeltme": sum(1 for r in ayrisan if r["is_duzeltme"] == "EVET"),
        "h5_ayirt_edici": len(h5),
        "h5_duzeltme": sum(1 for r in h5 if r["is_duzeltme"] == "EVET"),
        "genel_duzeltme_orani": (
            sum(1 for r in satirlar if r["is_duzeltme"] == "EVET") / len(satirlar)
        ),
        "ayrisan_duzeltme_orani": (
            sum(1 for r in ayrisan if r["is_duzeltme"] == "EVET") / len(ayrisan)
            if ayrisan else 0.0
        ),
        "ayrisan_tickerlar": sorted({r["ticker"] for r in ayrisan}),
    }
