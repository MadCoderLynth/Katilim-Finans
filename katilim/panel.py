"""Arşivin ayrıştırılması ve snapshot paneli — Faz 1.4b.

Ağa çıkmaz. Girdi `veri/ham/` (1.4a'nın arşivi), çıktı
`veri/panel/snapshot_{YYYYMMDD}.csv`. Yanlış çıkarsa düzeltilip yeniden
koşulur; maliyeti sıfır.

## 1.3'ten gelen iki karar burada uygulanıyor

**1. Her iki oran taşınır (H5, spec §2.3).** 1.276 formun 19'unda formun
kendi 4E TOPLAM satırı kendi kalemleriyle tutmuyor ve iki oran ayrışıyor.
Panelde ikisi de var:

  - `karar` sütunu **ÖZET alanından** üretilir — H5 kabul edilmiş gibi.
    Gerekçe aritmetik değil, **hata maliyeti asimetrisi**: BIST beyan
    esaslı çalışıyor ve özeti kullanıyorsa, biz kalemi kullandığımızda
    PNLSN gibi vakalarda "UYGUN" deriz ama BIST elemiştir → uygunsuz
    şirketi uygun göstermek, yani pahalı olan hata.
  - `karar_kalem_bazli` ikinci karar sütunu olarak yanında durur.
  - `h5_ayirt_edici` bayrağı, iki oranın **gerçekten ayrıştığı** kayıtları
    işaretler. H5'i sınayabilecek tek örneklem bunlar; 4.0 doğrudan
    sorgulayabilsin diye ayrı sütun.

**2. Dönem anahtarı meta veriden.** 1.276 formun 20'sinde formun kendi
etiketi meta veriden farklı ("Yıllık" → "4. 3 Aylık Bildirim" 13 kez,
"6 Aylık" → "2. 3 Aylık Bildirim" 7 kez); yıl hiç ayrışmıyor. Anahtar
`bildirim_gecmisi.csv`'nin (`arsiv_indeksi.csv`) alanlarıdır; formun kendi
etiketi `form_donem_etiketi` olarak **taşınır ama anahtar değildir**.

## Karantina

Self-check kalan kayıt panelden SİLİNMEZ, `karantina=EVET` ile işaretlenir
ve sebebi yazılır. Silmek 22 şirketi sessizce düşürmek olurdu; işaretsiz
bırakmak ise kural 1'i çiğnerdi. Aşağı akış (4.0) bu sütunla süzer.

## Ticker artık dosya adından tahmin edilmiyor

`arsiv_indeksi.csv` bildirim başına tüm pay kodlarını taşıyor ve bunlar
evren tablosundan geliyor. Panel ekseni ticker olduğu için çoklu kodlu
bildirim (ALBRK/ALK) **her kod için bir satır** üretir — indirme tekti,
panel satırı iki. Evrende olmayan bir kod çıkarsa sessizce geçilmez.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .ayristirici import AyristirmaHatasi, ayristir
from .karar import Karar, degerlendir
from .model import KafifBildirim
from .oranlar import TOLERANS, Oranlar, self_check

HAM_DIZINI = Path("veri/ham")
INDEKS_CSV = HAM_DIZINI / "arsiv_indeksi.csv"
PANEL_DIZINI = Path("veri/panel")


class ArsivOkunamadi(RuntimeError):
    """İndeks yok veya arşivle tutmuyor. 'Kayıt yok' DEĞİLDİR (kural 7)."""


# --- Ayrıştırma ------------------------------------------------------------


@dataclass
class ArsivKayit:
    """Ayrıştırılmış bir form + meta verisi (indeksten gelen anahtarlar)."""

    bildirim: KafifBildirim
    bildirim_id: int
    tickerlar: list[str]
    yil: int | None          # META VERİDEN — formun kendi etiketinden değil
    periyot: str | None      # META VERİDEN
    gonderim_ts: datetime | None
    dosya: str


@dataclass
class AyristirmaRaporu:
    okunan: int = 0
    hatali: list[tuple[int, str]] = field(default_factory=list)
    dosyasi_yok: list[int] = field(default_factory=list)
    evrende_olmayan: list[str] = field(default_factory=list)


def _indeksi_oku(yol: Path) -> list[dict]:
    if not yol.exists():
        raise ArsivOkunamadi(
            f"{yol} yok. Önce 1.4a: python -m katilim.cli indir"
        )
    with open(yol, newline="", encoding="utf-8-sig") as f:
        satirlar = list(csv.DictReader(f))
    if not satirlar:
        raise ArsivOkunamadi(f"{yol} boş — arşiv indeksi okunamadı")
    return satirlar


def ayristir_arsiv(
    ham_dizini: Path | str = HAM_DIZINI,
    *,
    indeks_csv: Path | str | None = None,
    evren_tickerlari: set[str] | None = None,
    ilerleme=None,
) -> tuple[list[ArsivKayit], AyristirmaRaporu]:
    """`veri/ham/` altındaki formları ayrıştırır.

    Dosya listesi dizin taramasından değil **arşiv indeksinden** gelir:
    indekste olup diskte olmayan dosya sessizce atlanmaz, raporlanır.
    """
    ham_dizini = Path(ham_dizini)
    indeks = _indeksi_oku(Path(indeks_csv) if indeks_csv else ham_dizini / "arsiv_indeksi.csv")

    kayitlar: list[ArsivKayit] = []
    rapor = AyristirmaRaporu()

    for sira, satir in enumerate(indeks, 1):
        bid = int(satir["bildirim_id"])
        yol = ham_dizini / satir["dosya"]
        if not satir["dosya"] or not yol.exists():
            rapor.dosyasi_yok.append(bid)
            continue

        tickerlar = [t for t in (satir["tum_tickerlar"] or "").split("/") if t]
        if evren_tickerlari is not None:
            yabanci = [t for t in tickerlar if t not in evren_tickerlari]
            rapor.evrende_olmayan.extend(yabanci)

        try:
            b = ayristir(
                yol.read_text(encoding="utf-8", errors="ignore"),
                bildirim_id=bid,
                # Ticker evren tablosundan (indeks üzerinden) geliyor;
                # dosya adından TAHMİN EDİLMİYOR.
                ticker=tickerlar[0] if tickerlar else None,
            )
        except (AyristirmaHatasi, Exception) as e:  # noqa: BLE001
            rapor.hatali.append((bid, f"{type(e).__name__}: {e}"[:200]))
            continue

        kayitlar.append(
            ArsivKayit(
                bildirim=b,
                bildirim_id=bid,
                tickerlar=tickerlar,
                yil=int(satir["yil"]) if satir["yil"] else None,
                periyot=satir["periyot"] or None,
                gonderim_ts=(
                    datetime.strptime(satir["gonderim_ts"], "%Y-%m-%d %H:%M:%S")
                    if satir["gonderim_ts"] else None
                ),
                dosya=satir["dosya"],
            )
        )
        rapor.okunan += 1
        if ilerleme and sira % 200 == 0:
            ilerleme(sira, len(indeks))

    return kayitlar, rapor


# --- Panel satırı ----------------------------------------------------------


@dataclass
class PanelSatiri:
    ticker: str
    yil: int | None
    periyot: str | None
    form_donem_etiketi: str | None
    gelir_orani_kalem: Decimal | None
    varlik_orani_kalem: Decimal | None
    borc_orani_kalem: Decimal | None
    gelir_orani_ozet: Decimal | None
    varlik_orani_ozet: Decimal | None
    borc_orani_ozet: Decimal | None
    oran_ayrisiyor: bool
    h5_ayirt_edici: bool
    karar: str                 # ÖZET alanından (H5 varsayılanı)
    red_kodlari: list[str]
    karar_kalem_bazli: str
    red_kodlari_kalem: list[str]
    self_check: str            # GECTI | KALDI
    karantina: bool
    karantina_sebebi: str
    sablon_imzasi: str | None
    nitelik: str | None
    bildirim_id: int
    gonderim_ts: datetime | None
    is_duzeltme: bool
    dosya: str


def _ayrisma(hesaplanan: Oranlar, ozet: Oranlar) -> tuple[bool, bool]:
    """(oran_ayrisiyor, h5_ayirt_edici).

    `oran_ayrisiyor`: iki oran kümesi herhangi bir kriterde tutmuyor —
    biri `None` iken diğeri değilse de ayrışma sayılır.

    `h5_ayirt_edici`: **iki değer de var** ve TOLERANS'ı aşan bir fark var.
    Yalnız bu kayıtlar "BIST hangi oranı kullanıyor" sorusunu ayırt eder;
    biri tanımsızsa (4E=0 vakaları) hipotez için bilgi taşımaz.
    """
    ayrisiyor = False
    ayirt_edici = False
    for ad in ("gelir", "varlik", "borc"):
        h = getattr(hesaplanan, ad)
        o = getattr(ozet, ad)
        if h is None or o is None:
            if h is not o:  # biri None diğeri değil
                ayrisiyor = True
            continue
        if abs(h - o) > TOLERANS:
            ayrisiyor = True
            ayirt_edici = True
    return ayrisiyor, ayirt_edici


def satir_uret(kayit: ArsivKayit, ticker: str, *, mali_sektor_muaf: bool = False) -> PanelSatiri:
    """Tek (ticker, bildirim) için panel satırı.

    Tolerans zinciri YOK: bu bir snapshot. `onceki_donem_toleransta`
    girdisi 3.1'in işi; burada her kayıt kendi başına değerlendiriliyor.
    """
    b = kayit.bildirim
    kontrol = self_check(b)
    hesaplanan = kontrol.hesaplanan
    ozet = Oranlar(b.ozet_gelir_orani, b.ozet_varlik_orani, b.ozet_borc_orani)
    ayrisiyor, ayirt_edici = _ayrisma(hesaplanan, ozet)

    # H5 varsayılanı: karar ÖZET alanından. Gerekçe modül başlığında.
    karar_ozet = degerlendir(b, mali_sektor_muaf=mali_sektor_muaf, oranlar=ozet)
    karar_kalem = degerlendir(b, mali_sektor_muaf=mali_sektor_muaf, oranlar=hesaplanan)

    sebep = ""
    if not kontrol.gecti:
        sapma = ", ".join(
            f"{ad}={kontrol.sapmalar[ad]}" for ad in kontrol.sapmalar
        )
        sebep = f"self-check: {sapma}" if sapma else "self-check: oran tanımsız"
        if kontrol.notlar:
            sebep += " | " + "; ".join(kontrol.notlar)

    return PanelSatiri(
        ticker=ticker,
        yil=kayit.yil,
        periyot=kayit.periyot,
        form_donem_etiketi=(
            f"{b.yil}/{b.periyot}" if (b.yil or b.periyot) else None
        ),
        gelir_orani_kalem=hesaplanan.gelir,
        varlik_orani_kalem=hesaplanan.varlik,
        borc_orani_kalem=hesaplanan.borc,
        gelir_orani_ozet=ozet.gelir,
        varlik_orani_ozet=ozet.varlik,
        borc_orani_ozet=ozet.borc,
        oran_ayrisiyor=ayrisiyor,
        h5_ayirt_edici=ayirt_edici,
        karar=karar_ozet.karar.value,
        red_kodlari=list(karar_ozet.kodlar),
        karar_kalem_bazli=karar_kalem.karar.value,
        red_kodlari_kalem=list(karar_kalem.kodlar),
        self_check="GECTI" if kontrol.gecti else "KALDI",
        karantina=not kontrol.gecti,
        karantina_sebebi=sebep[:200],
        sablon_imzasi=b.sablon_imzasi,
        nitelik=b.finansal_tablo_niteligi,
        bildirim_id=kayit.bildirim_id,
        gonderim_ts=kayit.gonderim_ts,
        is_duzeltme=b.is_duzeltme,
        dosya=kayit.dosya,
    )


def snapshot_uret(kayitlar: list[ArsivKayit], *, muafiyet: dict[str, bool | None] | None = None) -> list[PanelSatiri]:
    """Panel ekseni TICKER: çoklu kodlu bildirim her kod için satır üretir.

    Muafiyet `True` olan pay kodu KAPSAM_DISI kararı alır (G0). `None`
    (belirsiz) muaf SAYILMAZ — yanlış muafiyet şirketi panelden sessizce
    düşürür (1.1'in asimetri kuralı).
    """
    muafiyet = muafiyet or {}
    satirlar = []
    for k in kayitlar:
        for ticker in k.tickerlar or ["BILINMIYOR"]:
            satirlar.append(
                satir_uret(k, ticker, mali_sektor_muaf=muafiyet.get(ticker) is True)
            )
    # Sıralama gonderim_ts ile: dönem etiketi kronoloji taşımıyor
    # (futbol kulüpleri "2024/Yıllık"ı Ağustos 2025'te veriyor).
    return sorted(satirlar, key=lambda s: (s.ticker, s.gonderim_ts or datetime.min))


# --- Kalıcılık -------------------------------------------------------------

BASLIKLAR = [
    "ticker", "yil", "periyot", "form_donem_etiketi",
    "gelir_orani_kalem", "varlik_orani_kalem", "borc_orani_kalem",
    "gelir_orani_ozet", "varlik_orani_ozet", "borc_orani_ozet",
    "oran_ayrisiyor", "h5_ayirt_edici",
    "karar", "red_kodlari", "karar_kalem_bazli", "red_kodlari_kalem",
    "self_check", "karantina", "karantina_sebebi",
    "sablon_imzasi", "nitelik", "bildirim_id", "gonderim_ts", "is_duzeltme",
    "dosya",
]

_EH = {True: "EVET", False: "HAYIR", None: ""}


def _bicimle(s: PanelSatiri) -> dict:
    return {
        "ticker": s.ticker,
        "yil": s.yil if s.yil is not None else "",
        "periyot": s.periyot or "",
        "form_donem_etiketi": s.form_donem_etiketi or "",
        "gelir_orani_kalem": "" if s.gelir_orani_kalem is None else str(s.gelir_orani_kalem),
        "varlik_orani_kalem": "" if s.varlik_orani_kalem is None else str(s.varlik_orani_kalem),
        "borc_orani_kalem": "" if s.borc_orani_kalem is None else str(s.borc_orani_kalem),
        "gelir_orani_ozet": "" if s.gelir_orani_ozet is None else str(s.gelir_orani_ozet),
        "varlik_orani_ozet": "" if s.varlik_orani_ozet is None else str(s.varlik_orani_ozet),
        "borc_orani_ozet": "" if s.borc_orani_ozet is None else str(s.borc_orani_ozet),
        "oran_ayrisiyor": _EH[s.oran_ayrisiyor],
        "h5_ayirt_edici": _EH[s.h5_ayirt_edici],
        "karar": s.karar,
        "red_kodlari": ",".join(s.red_kodlari),
        "karar_kalem_bazli": s.karar_kalem_bazli,
        "red_kodlari_kalem": ",".join(s.red_kodlari_kalem),
        "self_check": s.self_check,
        "karantina": _EH[s.karantina],
        "karantina_sebebi": s.karantina_sebebi,
        "sablon_imzasi": s.sablon_imzasi or "",
        "nitelik": s.nitelik or "",
        "bildirim_id": s.bildirim_id,
        "gonderim_ts": s.gonderim_ts.strftime("%Y-%m-%d %H:%M:%S") if s.gonderim_ts else "",
        "is_duzeltme": _EH[s.is_duzeltme],
        "dosya": s.dosya,
    }


def yaz(satirlar: list[PanelSatiri], yol: Path | str | None = None) -> Path:
    yol = Path(yol) if yol else PANEL_DIZINI / f"snapshot_{date.today():%Y%m%d}.csv"
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=BASLIKLAR)
        w.writeheader()
        w.writerows(_bicimle(s) for s in satirlar)
    return yol


# --- Rapor -----------------------------------------------------------------


# --- Tarihsel panel: tolerans zinciri (Faz 3.1) ----------------------------
#
# Snapshot (`snapshot_uret`) her kaydı kendi başına değerlendiriyordu.
# Burada `karar.seri_degerlendir` devreye giriyor ve tolerans durumu
# şirket bazında dönemler arasında TAŞINIYOR (H4).

ZINCIR_TEMIZ = ""
ZINCIR_BOSLUGU = "ZINCIR_BOSLUGU"

# Bir dönemin ATLANDIĞINI gösteren asgari sessizlik. KAFİF yarıyıllık:
# ardışık bildirimler arası ölçülen medyan 185 gün, p90 206, en uzun 259
# (1.276 formluk arşiv). 280 gün ≈ 1,5 kadans — bunu aşan aralık, arada
# bir dönemin hiç verilmediği anlamına gelir.
#
# Boşluğu `beyan_durumu` ile aramak YANLIŞ olurdu: panelde satırı olan her
# şirket zaten BEYAN_VAR'dır, yani o sinyal hiç tetiklenmez ve "boşluk yok"
# diye yanıltır. Boşluk şirketin KENDİ serisindeki sessizliktir.
ZINCIR_BOSLUK_GUN = 280


@dataclass
class KararSatiri:
    """Spec §1.5 `uygunluk_karar` şeması + zincir izi."""

    ticker: str
    yil: int | None
    periyot: str | None
    gecerlilik_baslangic: datetime | None     # = gonderim_ts (spec §5.1)
    karar: str
    red_kodlari: list[str]
    gelir_orani: Decimal | None
    varlik_orani: Decimal | None
    borc_orani: Decimal | None
    onceki_donem_tolerans: bool
    sablon_versiyon: str | None
    self_check: str
    bildirim_id: int
    zincir_notu: str = ZINCIR_TEMIZ


def panel_uret(
    kayitlar: list[ArsivKayit],
    evren_sirketler,
    *,
    beyan_durumlari: dict[str, str] | None = None,
) -> list[KararSatiri]:
    """Her (ticker, yıl, periyot) için tolerans zincirli uygunluk kararı.

    Sıra **şirket bazında kronolojik** ve kronoloji `gonderim_ts`'ten
    geliyor — dönem etiketinden değil (`karar.seri_degerlendir`).

    `BELIRSIZ` kararı tolerans durumunu SIFIRLAMAZ: veri eksikliği bir
    "temize çıkma" değildir (karar.py'nin mevcut davranışı, panelde de
    korunuyor).

    **Zincir boşluğu — spec'te TANIMLI DEĞİL.** Bir şirketin dönemleri
    arasında beyan vermediği bir aralık varsa tolerans durumunun taşınıp
    taşınmayacağı yazılı değil. Geçici davranış: **durum taşınır** ve satır
    `ZINCIR_BOSLUGU` ile işaretlenir ki karar verildiğinde etkilenen
    satırlar tek sorguyla bulunabilsin. Karar kullanıcıya bırakıldı.
    """
    from .karar import seri_degerlendir

    muafiyet = {s.ticker: s.mali_sektor_muaf for s in evren_sirketler}
    beyan_durumlari = beyan_durumlari or {}

    # Panel ekseni ticker: çoklu kodlu bildirim her kod için ayrı zincire girer.
    per_ticker: dict[str, list[ArsivKayit]] = {}
    for k in kayitlar:
        for t in k.tickerlar or ["BILINMIYOR"]:
            per_ticker.setdefault(t, []).append(k)

    satirlar: list[KararSatiri] = []
    for ticker, kayit_listesi in sorted(per_ticker.items()):
        # bildirim -> arşiv kaydı eşlemesi (meta veri anahtarları için)
        meta = {id(k.bildirim): k for k in kayit_listesi}
        # Oranlar ÖZET alanından — snapshot'ın `karar` sütunuyla AYNI kaynak
        # (H5 varsayılanı). Kalemlerden hesaplasaydık tarihsel panel ile
        # snapshot, tolerans zinciriyle ilgisi olmayan sebeplerle ayrışırdı.
        sonuclar = seri_degerlendir(
            [k.bildirim for k in kayit_listesi],
            mali_sektor_muaf=muafiyet.get(ticker) is True,
            oranlar_fn=lambda b: Oranlar(
                b.ozet_gelir_orani, b.ozet_varlik_orani, b.ozet_borc_orani
            ),
        )

        # Zincir boşluğu: şirketin KENDİ serisinde bir dönem atlanmış mı?
        # Kronolojik ardışık iki bildirim arasındaki sessizlik ölçülüyor;
        # boşluğun SONRASINDAKİ satır işaretleniyor, çünkü tolerans durumu
        # ona taşınıyor.
        onceki_ts: datetime | None = None
        bosluklu_idler: set[int] = set()
        for b, _ in sonuclar:
            ts = meta[id(b)].gonderim_ts
            if onceki_ts and ts and (ts - onceki_ts).days > ZINCIR_BOSLUK_GUN:
                bosluklu_idler.add(meta[id(b)].bildirim_id)
            if ts:
                onceki_ts = ts

        for b, s in sonuclar:
            k = meta[id(b)]
            kontrol = self_check(b)
            o = s.oranlar
            satirlar.append(
                KararSatiri(
                    ticker=ticker,
                    # Dönem anahtarı META VERİDEN (1.3'ün bulgusu).
                    yil=k.yil,
                    periyot=k.periyot,
                    gecerlilik_baslangic=k.gonderim_ts,
                    karar=s.karar.value,
                    red_kodlari=list(s.kodlar),
                    gelir_orani=o.gelir if o else None,
                    varlik_orani=o.varlik if o else None,
                    borc_orani=o.borc if o else None,
                    onceki_donem_tolerans=s.onceki_donem_toleransta,
                    sablon_versiyon=b.sablon_imzasi,
                    self_check="GECTI" if kontrol.gecti else "KALDI",
                    bildirim_id=k.bildirim_id,
                    zincir_notu=(
                        ZINCIR_BOSLUGU
                        if k.bildirim_id in bosluklu_idler else ZINCIR_TEMIZ
                    ),
                )
            )
    return satirlar


KARAR_BASLIKLARI = [
    "ticker", "yil", "periyot", "gecerlilik_baslangic", "karar", "red_kodlari",
    "gelir_orani", "varlik_orani", "borc_orani", "onceki_donem_tolerans",
    "sablon_versiyon", "self_check", "bildirim_id", "zincir_notu",
]


def panel_yaz(satirlar: list[KararSatiri], yol: Path | str = PANEL_DIZINI / "panel.csv") -> Path:
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    sirali = sorted(
        satirlar,
        key=lambda s: (s.ticker, s.gecerlilik_baslangic or datetime.min),
    )
    with open(yol, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=KARAR_BASLIKLARI)
        w.writeheader()
        for s in sirali:
            w.writerow(
                {
                    "ticker": s.ticker,
                    "yil": s.yil if s.yil is not None else "",
                    "periyot": s.periyot or "",
                    "gecerlilik_baslangic": (
                        s.gecerlilik_baslangic.strftime("%Y-%m-%d %H:%M:%S")
                        if s.gecerlilik_baslangic else ""
                    ),
                    "karar": s.karar,
                    "red_kodlari": ",".join(s.red_kodlari),
                    "gelir_orani": "" if s.gelir_orani is None else str(s.gelir_orani),
                    "varlik_orani": "" if s.varlik_orani is None else str(s.varlik_orani),
                    "borc_orani": "" if s.borc_orani is None else str(s.borc_orani),
                    "onceki_donem_tolerans": _EH[s.onceki_donem_tolerans],
                    "sablon_versiyon": s.sablon_versiyon or "",
                    "self_check": s.self_check,
                    "bildirim_id": s.bildirim_id,
                    "zincir_notu": s.zincir_notu,
                }
            )
    return yol


def panel_ozet(satirlar: list[KararSatiri], snapshot: list[PanelSatiri] | None = None) -> dict:
    """Zincirin ne değiştirdiğini gösterir — asıl merak edilen bu."""
    dagilim: dict[str, int] = {}
    for s in satirlar:
        dagilim[s.karar] = dagilim.get(s.karar, 0) + 1

    cikti = {
        "satir": len(satirlar),
        "ticker": len({s.ticker for s in satirlar}),
        "karar_dagilimi": dict(sorted(dagilim.items(), key=lambda kv: -kv[1])),
        "onceki_donem_tolerans": sum(1 for s in satirlar if s.onceki_donem_tolerans),
        "zincir_boslugu": sum(1 for s in satirlar if s.zincir_notu == ZINCIR_BOSLUGU),
        "karantina": sum(1 for s in satirlar if s.self_check == "KALDI"),
    }
    if snapshot is not None:
        # Zincirsiz snapshot ile karşılaştır: hangi satırlar çevrildi?
        snap = {(s.ticker, s.bildirim_id): s.karar for s in snapshot}
        cevrilen = [
            (s.ticker, s.yil, s.periyot, snap[(s.ticker, s.bildirim_id)], s.karar)
            for s in satirlar
            if (s.ticker, s.bildirim_id) in snap
            and snap[(s.ticker, s.bildirim_id)] != s.karar
        ]
        cikti["zincirin_cevirdigi"] = len(cevrilen)
        cikti["cevrilen_liste"] = cevrilen
    return cikti


def ozet(satirlar: list[PanelSatiri], rapor: AyristirmaRaporu) -> dict:
    def say(anahtar):
        d: dict = {}
        for s in satirlar:
            v = anahtar(s)
            d[v] = d.get(v, 0) + 1
        return dict(sorted(d.items(), key=lambda kv: -kv[1]))

    ayrisan = [s for s in satirlar if s.h5_ayirt_edici]
    karar_ceviren = [s for s in ayrisan if s.karar != s.karar_kalem_bazli]
    zamanlar = sorted(s.gonderim_ts for s in satirlar if s.gonderim_ts)

    return {
        "panel_satiri": len(satirlar),
        "benzersiz_bildirim": len({s.bildirim_id for s in satirlar}),
        "benzersiz_ticker": len({s.ticker for s in satirlar}),
        "ayristirilan": rapor.okunan,
        "ayristirma_hatasi": len(rapor.hatali),
        "dosyasi_yok": len(rapor.dosyasi_yok),
        "karar_dagilimi": say(lambda s: s.karar),
        "karar_kalem_dagilimi": say(lambda s: s.karar_kalem_bazli),
        "self_check": say(lambda s: s.self_check),
        "karantina": sum(1 for s in satirlar if s.karantina),
        "oran_ayrisiyor": sum(1 for s in satirlar if s.oran_ayrisiyor),
        "h5_ayirt_edici": len(ayrisan),
        "h5_karar_ceviren": len(karar_ceviren),
        "h5_karar_ceviren_liste": [
            f"{s.ticker} {s.yil}/{s.periyot} özet={s.karar} kalem={s.karar_kalem_bazli}"
            for s in karar_ceviren
        ],
        "sablon_imzasi": say(lambda s: s.sablon_imzasi),
        "nitelik": say(lambda s: s.nitelik),
        "donem": say(lambda s: f"{s.yil}/{s.periyot}"),
        "form_etiketi_ayrisan": sum(
            1 for s in satirlar
            if s.form_donem_etiketi and s.form_donem_etiketi != f"{s.yil}/{s.periyot}"
        ),
        "duzeltme": sum(1 for s in satirlar if s.is_duzeltme),
        "en_eski": zamanlar[0] if zamanlar else None,
        "en_yeni": zamanlar[-1] if zamanlar else None,
    }
