"""KAFİF formlarının indirilmesi ve arşivlenmesi — Faz 1.4a.

**Bu modül AYRIŞTIRMAZ.** Tek işi `/tr/Bildirim/{id}` gövdesini diske almak.
Parser'a hiç dokunmaz; bu yüzden 1.3'ün (20/20 parser kapısı) bitmesini
beklemesi gerekmiyor. Gerekçe asimetrik: **yanlış ayrıştırma sonradan
bedavaya düzeltilir, kaçırılan bildirim düzeltilemez** (kural 6: ham HTML
her zaman saklanır, şablon değişince geçmişi yeniden ayrıştırmanın tek yolu).

## Neyin arşiv, neyin önbellek olduğu

`veri/ham/` bu adımdan sonra **tek kopyası olan arşivdir.** Silme veya toplu
yeniden çekme komutu bilinçli olarak yazılmadı. Gövde URL önbelleğine
yazılmıyor (`onbellekle=False`): aynı 240 MB iki kez saklanmasın diye.
İdempotanlık zaten dosya adındaki `bildirim_id`'den geliyor — **sha256'dan
değil.** Sha yalnızca diskteki dosyanın bütünlük damgası: KAP markup'ı
istekten isteğe değişiyor, aynı bildirimi iki kez çekmek iki farklı sha
üretiyor (ROTA_KESFI_RAPORU §4).

## Sayfalama yok

Tek sabit pencere toplayıcısı. 2.0 ölçtü: sunucu bulduğunun tamamını tek
sayfada basıyor (92 = 92) ve `page`/`offset`/`size` yok sayılıyor. Buraya
sayfalama döngüsü yazmayın.

## Beyan yokluğu sessiz geçilmez

KAFİF'i olmayan şirket "atlanan" değil, **kaydedilen** bir durumdur:

  - `BEYAN_YOK`        — muaf değil, yine de beyan vermemiş (spec §0.4:
                          ihtiyatlılık gereği endeks dışında kalır)
  - `AYIRT_EDILEMEDI`  — muafiyeti belirsiz VE beyanı yok. Bu rotadan muaf
                          olan ile beyan vermeyen ayırt edilemiyor; ikisinden
                          birini varsaymak yerine durum böyle işaretlenir.
  - `KAPSAM_DISI`      — muaf, zaten sorgulanmadı (spec §0.4 listesi)
"""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .metin import normalize

BILDIRIM_URL = "https://kap.org.tr/tr/Bildirim/{bildirim_id}"

HAM_DIZINI = Path("veri/ham")
INDEKS_CSV = HAM_DIZINI / "arsiv_indeksi.csv"
BEYAN_CSV = Path("veri/evren/beyan_durumu.csv")

# Dosya adının sonundaki kimlik: idempotanlık anahtarı buradan okunuyor.
_DOSYA_ID_RE = re.compile(r"_(\d+)\.html$")

DURUM_INDIRILDI = "INDIRILDI"
DURUM_ZATEN_VARDI = "ZATEN_VARDI"
DURUM_YOK = "YOK"          # kalıcı hata (404) — bildirim erişilemiyor
DURUM_HATA = "HATA"        # geçici hata; yeniden denenebilir

BEYAN_VAR = "BEYAN_VAR"
BEYAN_YOK = "BEYAN_YOK"
AYIRT_EDILEMEDI = "AYIRT_EDILEMEDI"
KAPSAM_DISI = "KAPSAM_DISI"


# --- Dosya adlandırma ------------------------------------------------------


def periyot_slug(periyot: str | None) -> str:
    """'6 Aylık' -> '6_aylik'. Türkçe harf tuzağı `normalize`'da eleniyor."""
    n = normalize(periyot or "")
    return n.replace(" ", "_") or "donemsiz"


def dosya_adi(ticker: str, yil: int | None, periyot: str | None, bildirim_id: int) -> str:
    """`{TICKER}_{YIL}_{PERIYOT}_{bildirim_id}.html`

    Kimlik **sonda** duruyor; arşiv taraması dosya adının geri kalanına
    bakmadan kimliği okuyabilsin diye. Ticker veya dönem etiketi ileride
    değişse bile idempotanlık bozulmaz.
    """
    return f"{ticker or 'BILINMIYOR'}_{yil or 'yilsiz'}_{periyot_slug(periyot)}_{bildirim_id}.html"


def mevcut_arsiv(dizin: Path | str = HAM_DIZINI) -> dict[int, Path]:
    """Diskte hangi bildirim_id'ler var? İdempotanlığın tek kaynağı.

    Dosya adından okunur — içerik açılmaz, sha hesaplanmaz. Arşivde 2.000
    dosya olsa bile tarama tek `iterdir` çağrısı.
    """
    dizin = Path(dizin)
    if not dizin.exists():
        return {}
    bulunan: dict[int, Path] = {}
    for p in dizin.iterdir():
        m = _DOSYA_ID_RE.search(p.name)
        if m and p.is_file():
            bulunan[int(m.group(1))] = p
    return bulunan


# --- Model -----------------------------------------------------------------


@dataclass
class ArsivKaydi:
    bildirim_id: int
    ticker: str                    # birincil pay kodu (alfabetik ilk)
    tickerlar: list[str]           # aynı bildirimi paylaşan tüm kodlar
    yil: int | None
    periyot: str | None
    gonderim_ts: datetime | None
    durum: str
    dosya: str = ""
    bayt: int = 0
    sha256: str = ""
    pencere_disi: bool = False     # keşif penceresinin dışında mı kalmıştı
    not_: str = ""


@dataclass
class Indirme:
    kayitlar: list[ArsivKaydi] = field(default_factory=list)
    uyarilar: list[str] = field(default_factory=list)

    def durum_dagilimi(self) -> dict[str, int]:
        d: dict[str, int] = {}
        for k in self.kayitlar:
            d[k.durum] = d.get(k.durum, 0) + 1
        return d


def _birincil_ticker(tickerlar: list[str]) -> str:
    """Çoklu kodlu şirkette dosya adına giren kod.

    Bildirim TEK, pay kodu birden çok olabilir (ALBRK/ALK). Dosya bir kez
    yazılır; hangi kodun adı geçtiği keyfi olduğu için deterministik
    seçiliyor ve tüm kodlar indekste ayrıca saklanıyor.
    """
    return sorted(tickerlar)[0] if tickerlar else "BILINMIYOR"


def satirlari_grupla(bildirim_gecmisi: list[dict]) -> list[dict]:
    """(ticker × bildirim) satırlarını benzersiz bildirime indirger.

    1.2 çıktısı panel ekseninde (ticker başına satır); indirme ekseni ise
    bildirim. 1.280 satır -> 1.276 indirme.
    """
    gruplar: dict[int, dict] = {}
    for s in bildirim_gecmisi:
        g = gruplar.setdefault(
            s["bildirim_id"],
            {
                "bildirim_id": s["bildirim_id"],
                "tickerlar": [],
                "yil": s["yil"],
                "periyot": s["periyot"],
                "gonderim_ts": s["gonderim_ts"],
                "konu": s["konu"],
            },
        )
        if s["ticker"] not in g["tickerlar"]:
            g["tickerlar"].append(s["ticker"])
    return sorted(gruplar.values(), key=lambda g: g["bildirim_id"])


# --- İndirme ---------------------------------------------------------------


def formlari_indir(
    bildirim_gecmisi: list[dict],
    cekici,
    *,
    ham_dizini: Path | str = HAM_DIZINI,
    pencere_gun: int = 365,
    simdi: datetime | None = None,
    ilerleme=None,
    kontrol_noktasi=None,
    kontrol_araligi: int = 50,
) -> Indirme:
    """Her benzersiz `bildirim_id` için formu indirir ve arşive yazar.

    İdempotan: diskte kimliği olan dosya varsa ağa çıkılmaz.
    """
    from .cekici import ÇekimHatası

    ham_dizini = Path(ham_dizini)
    ham_dizini.mkdir(parents=True, exist_ok=True)

    gruplar = satirlari_grupla(bildirim_gecmisi)
    diskte = mevcut_arsiv(ham_dizini)
    simdi = simdi or datetime.now()
    pencere_basi = simdi - timedelta(days=pencere_gun)

    indirme = Indirme()
    agdan = 0

    for sira, g in enumerate(gruplar, 1):
        bid = g["bildirim_id"]
        ticker = _birincil_ticker(g["tickerlar"])
        kayit = ArsivKaydi(
            bildirim_id=bid,
            ticker=ticker,
            tickerlar=sorted(g["tickerlar"]),
            yil=g["yil"],
            periyot=g["periyot"],
            gonderim_ts=g["gonderim_ts"],
            durum=DURUM_ZATEN_VARDI,
            # "Keşif penceresi dışında" = bu kimlik bugün sorgu sonucunda
            # görünmezdi. Hipotezin test kümesi tam olarak bunlar.
            pencere_disi=bool(g["gonderim_ts"] and g["gonderim_ts"] < pencere_basi),
        )

        if bid in diskte:
            p = diskte[bid]
            kayit.dosya = p.name
            kayit.bayt = p.stat().st_size
            indirme.kayitlar.append(kayit)
            if ilerleme:
                ilerleme(sira, len(gruplar), kayit)
            continue

        url = BILDIRIM_URL.format(bildirim_id=bid)
        try:
            # onbellekle=False: arşiv veri/ham'da, aynı gövdeyi iki kez saklama.
            govde = cekici.getir(url, onbellekle=False)
        except ÇekimHatası as e:
            negatif = cekici.onbellek.negatif_durum(url)
            kayit.durum = DURUM_YOK if negatif else DURUM_HATA
            kayit.not_ = (f"HTTP {negatif[0]}" if negatif else str(e))[:160]
            indirme.kayitlar.append(kayit)
            indirme.uyarilar.append(f"{ticker} {bid}: {kayit.not_}")
            agdan += 1
            if ilerleme:
                ilerleme(sira, len(gruplar), kayit)
            if kontrol_noktasi and agdan % kontrol_araligi == 0:
                kontrol_noktasi(indirme)
            continue

        ad = dosya_adi(ticker, g["yil"], g["periyot"], bid)
        yol = ham_dizini / ad
        yol.write_text(govde, encoding="utf-8")
        kayit.durum = DURUM_INDIRILDI
        kayit.dosya = ad
        kayit.bayt = len(govde.encode("utf-8"))
        # Kural 6: sha içerik değişikliğinin göstergesi DEĞİL, diskteki
        # dosyanın bütünlük damgası.
        kayit.sha256 = hashlib.sha256(govde.encode("utf-8")).hexdigest()
        indirme.kayitlar.append(kayit)
        agdan += 1

        if ilerleme:
            ilerleme(sira, len(gruplar), kayit)
        if kontrol_noktasi and agdan % kontrol_araligi == 0:
            kontrol_noktasi(indirme)

    return indirme


# --- Beyan durumu (KAFİF'i olmayan şirketler) ------------------------------


def beyan_durumlari(sirketler, sorgu_durumlari: list[dict]) -> list[dict]:
    """Pay kodu başına beyan durumu. KAFİF'i olmayan şirket sessizce atlanmaz.

    `sorgu_durumlari`, 1.2'nin `veri/evren/sorgu_durumu.csv` çıktısıdır:
    tüzel kişi başına bir satır, `ticker` alanı çoklu kodda '/' ile birleşik.

    Muaf olan ile beyan vermeyen **ayrı** kaydedilir. Muafiyeti belirsiz olan
    beyan da vermemişse ikisi bu rotadan ayırt EDİLEMEZ; o kayıt
    `AYIRT_EDILEMEDI` olur — `MUAF` varsayılmaz. Yanlış muafiyet şirketi
    panelden sessizce düşürür (1.1'in asimetri kuralı).
    """
    muafiyet = {s.ticker: s.mali_sektor_muaf for s in sirketler}
    unvan = {s.ticker: s.unvan for s in sirketler}

    cikti = []
    for satir in sorgu_durumlari:
        kafif_var = int(satir.get("kafif_sayisi") or 0) > 0
        for ticker in [t for t in (satir.get("ticker") or "").split("/") if t]:
            muaf = muafiyet.get(ticker)
            if kafif_var:
                durum = BEYAN_VAR
            elif muaf is True:
                durum = KAPSAM_DISI
            elif muaf is None:
                durum = AYIRT_EDILEMEDI
            else:
                durum = BEYAN_YOK
            cikti.append(
                {
                    "ticker": ticker,
                    "unvan": unvan.get(ticker, satir.get("unvan", "")),
                    "durum": durum,
                    "kafif_sayisi": int(satir.get("kafif_sayisi") or 0),
                    "sorgu_durumu": satir.get("durum", ""),
                    "mali_sektor_muaf": {True: "EVET", False: "HAYIR", None: ""}[muaf],
                }
            )
    return sorted(cikti, key=lambda r: r["ticker"])


# --- Kalıcılık -------------------------------------------------------------

INDEKS_BASLIKLARI = [
    "bildirim_id", "ticker", "tum_tickerlar", "yil", "periyot", "gonderim_ts",
    "durum", "dosya", "bayt", "sha256", "pencere_disi", "not",
]
BEYAN_BASLIKLARI = [
    "ticker", "unvan", "durum", "kafif_sayisi", "sorgu_durumu", "mali_sektor_muaf",
]


def indeksi_yaz(indirme: Indirme, yol: Path | str = INDEKS_CSV) -> Path:
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=INDEKS_BASLIKLARI)
        w.writeheader()
        for k in sorted(indirme.kayitlar, key=lambda k: k.bildirim_id):
            w.writerow(
                {
                    "bildirim_id": k.bildirim_id,
                    "ticker": k.ticker,
                    "tum_tickerlar": "/".join(k.tickerlar),
                    "yil": k.yil or "",
                    "periyot": k.periyot or "",
                    "gonderim_ts": k.gonderim_ts.strftime("%Y-%m-%d %H:%M:%S")
                    if k.gonderim_ts else "",
                    "durum": k.durum,
                    "dosya": k.dosya,
                    "bayt": k.bayt,
                    "sha256": k.sha256,
                    "pencere_disi": "EVET" if k.pencere_disi else "HAYIR",
                    "not": k.not_,
                }
            )
    return yol


def beyan_durumlarini_yaz(satirlar: list[dict], yol: Path | str = BEYAN_CSV) -> Path:
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=BEYAN_BASLIKLARI)
        w.writeheader()
        w.writerows(satirlar)
    return yol


# --- Rapor -----------------------------------------------------------------


def ozet(indirme: Indirme, beyan: list[dict]) -> dict:
    inen = [k for k in indirme.kayitlar if k.durum in (DURUM_INDIRILDI, DURUM_ZATEN_VARDI)]
    zamanlar = sorted(k.gonderim_ts for k in inen if k.gonderim_ts)
    disi = [k for k in indirme.kayitlar if k.pencere_disi]
    beyan_dagilim: dict[str, int] = {}
    for b in beyan:
        beyan_dagilim[b["durum"]] = beyan_dagilim.get(b["durum"], 0) + 1

    boyutlar = sorted(k.bayt for k in inen if k.bayt)
    return {
        "bildirim": len(indirme.kayitlar),
        "durum_dagilimi": indirme.durum_dagilimi(),
        "arsivdeki_form": len(inen),
        "en_eski": zamanlar[0] if zamanlar else None,
        "en_yeni": zamanlar[-1] if zamanlar else None,
        "pencere_disi": len(disi),
        "pencere_disi_inen": sum(
            1 for k in disi if k.durum in (DURUM_INDIRILDI, DURUM_ZATEN_VARDI)
        ),
        "pencere_disi_yok": sum(1 for k in disi if k.durum == DURUM_YOK),
        "beyan_dagilimi": beyan_dagilim,
        "bayt_toplam": sum(boyutlar),
        "bayt_medyan": boyutlar[len(boyutlar) // 2] if boyutlar else 0,
        "bayt_min": boyutlar[0] if boyutlar else 0,
        "bayt_max": boyutlar[-1] if boyutlar else 0,
    }
