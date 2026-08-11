"""Dış dünyanın TEK giriş noktası — Faz 5.3.

Trading sistemi panelin iç yapısına **bu modül dışında bağlanmasın.** CSV
yolları, şema ayrıntıları ve üç tuzak burada toplanıyor; aşağı akış yalnız
`uygunluk_durumu`, `olaylar` ve `hisse_karti` görüyor.

## ÜÇ TUZAK — hepsi belgeli, burada AÇIKÇA ele alınıyor

**1. KARANTİNA.** 22 kayıt self-check'ten geçmedi ama panelde duruyor
(silmek 22 şirketi sessizce düşürmek olurdu, 1.4b kararı). Bayrağı yok
sayan bir tüketici **doğrulanmamış kararı sessizce alır**. Bu yüzden
`uygunluk_durumu` karantinalı kayıtları varsayılan olarak DIŞARIDA
bırakır; `karantinali=True` ile istenirse döner ve `karantinali` alanı
her zaman doğruyu söyler.

**2. MUAF ≠ ELENMİŞ.** `KAPSAM_DISI` "uygun değil" DEĞİLDİR. Katılım
esaslı finans kuruluşları (ALBRK katılım bankası, KTLEV tasarruf
finansman) KAFİF doldurmuyor ama XKTUM üyesi (spec §0.4). Bu yüzden
`Durum.uygun` **üç değerli**: `True` / `False` / `None`. `None` "hayır"
değildir; `kapsam_disi` ve `gorus_var` alanları ayrıca söylüyor.

**3. GÖRÜŞ YOK ≠ UYGUN DEĞİL.** `BEYAN_YOK`, `FORM_VAR_BILDIRIM_YOK`,
`AYIRT_EDILEMEDI`, `BELIRSIZ` ve **tarih panelin başlangıcından önceyse**
sonuç `GORUS_YOK`'tur. `None` dönülmez, sessizce `UYGUN_DEGIL`'e
düşülmez — ikisi de görüşü olmayan kaydı görüş gibi gösterirdi.

## Look-ahead

`uygunluk_durumu(ticker, tarih)` = `gecerlilik_baslangic <= tarih` olan
**en geç** kayıt. `gecerli_kayit` süzgeci UYGULANMAZ: bugün geçersiz
kılınmış bir kayıt, kendi penceresinde canlı etiketti (5.1 disiplini).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from . import olay as _olay

# --- Veri yolları: TEK YERDE ----------------------------------------------
PANEL_CSV = Path("veri/panel/panel.csv")
DONEM_CSV = Path("veri/referans/xktum_donemler.csv")
EVREN_CSV = Path("veri/evren/sirketler.csv")
BEYAN_CSV = Path("veri/evren/beyan_durumu.csv")
ENDEKS_CSV = Path("veri/evren/endeks_uyeligi.csv")
BILESEN_CSV = Path("veri/referans/xktum_bilesenler.csv")
DUZELTME_CSV = Path("veri/panel/duzeltme_olaylari.csv")

XKTUM_ADI = "BIST KATILIM TUM"

# Görüş içermeyen beyan durumları — "uygun değil" DEĞİL.
GORUSSUZ_BEYAN = ("BEYAN_YOK", "FORM_VAR_BILDIRIM_YOK", "AYIRT_EDILEMEDI")
# Panel kararlarından görüş içermeyenler.
GORUSSUZ_KARAR = ("BELIRSIZ",)
UYGUN_KARARLAR = ("UYGUN", "TOLERANSTA")

GORUS_YOK = "GORUS_YOK"
KAPSAM_DISI = "KAPSAM_DISI"


class VeriYok(RuntimeError):
    """Girdi dosyası yok/okunamadı. 'Kayıt yok' DEĞİLDİR (kural 7)."""


class BilinmeyenTicker(KeyError):
    """Evrende olmayan pay kodu. Boş sonuçla karıştırılmaz."""


# --- Model -----------------------------------------------------------------


@dataclass
class Durum:
    """Bir pay kodunun verilen tarihteki uygunluk durumu.

    `uygun` ÜÇ DEĞERLİDİR ve `None` "hayır" demek değildir — tuzak 2 ve 3.
    Karar vermeden önce `gorus_var`'a bakın.
    """

    ticker: str
    tarih: date
    karar: str                    # UYGUN | TOLERANSTA | UYGUN_DEGIL |
    #                               KAPSAM_DISI | GORUS_YOK
    uygun: bool | None            # None = görüş yok / kapsam dışı
    gorus_var: bool               # False ise `uygun` yorumlanmamalı
    kapsam_disi: bool             # muaf: KAFİF vermiyor, ELENMİŞ DEĞİL
    sebep: str
    red_kodlari: tuple[str, ...] = ()
    gelir_orani: str = ""
    varlik_orani: str = ""
    borc_orani: str = ""
    yil: str = ""
    periyot: str = ""
    gecerlilik_baslangic: datetime | None = None
    bildirim_id: str = ""
    karantinali: bool = False     # self-check KALDI — karar doğrulanmamış
    onceki_donem_tolerans: bool = False
    zincir_notu: str = ""


# --- Okuma (dosya başına bir kez, süreç içinde önbellekli) ----------------

_ONBELLEK: dict[str, object] = {}


def onbellegi_temizle() -> None:
    """Testler ve uzun süreçler için: diskten yeniden okunmasını sağlar."""
    _ONBELLEK.clear()


def _satirlar(yol: Path, ad: str) -> list[dict]:
    anahtar = f"csv:{yol}"
    if anahtar not in _ONBELLEK:
        if not Path(yol).exists():
            raise VeriYok(f"{ad} yok: {yol}")
        with open(yol, newline="", encoding="utf-8-sig") as f:
            _ONBELLEK[anahtar] = list(csv.DictReader(f))
    return _ONBELLEK[anahtar]  # type: ignore[return-value]


def _evren() -> dict[str, dict]:
    if "evren" not in _ONBELLEK:
        s = _satirlar(EVREN_CSV, "evren")
        if not s:
            raise VeriYok(f"evren satırsız: {EVREN_CSV}")
        _ONBELLEK["evren"] = {r["ticker"]: r for r in s}
    return _ONBELLEK["evren"]  # type: ignore[return-value]


def _beyan() -> dict[str, str]:
    if "beyan" not in _ONBELLEK:
        _ONBELLEK["beyan"] = {
            r["ticker"]: r["durum"] for r in _satirlar(BEYAN_CSV, "beyan durumu")
        }
    return _ONBELLEK["beyan"]  # type: ignore[return-value]


def _panel() -> dict[str, list[dict]]:
    """Pay kodu -> gönderim sırasına dizilmiş TÜM panel satırları."""
    if "panel" not in _ONBELLEK:
        s = _satirlar(PANEL_CSV, "panel")
        if not s:
            raise VeriYok(f"panel satırsız: {PANEL_CSV}")
        d: dict[str, list[dict]] = {}
        for r in s:
            r = dict(r)
            r["_ts"] = _zaman(r.get("gecerlilik_baslangic"))
            d.setdefault(r["ticker"], []).append(r)
        for v in d.values():
            v.sort(key=lambda r: (r["_ts"] is None, r["_ts"] or datetime.min))
        _ONBELLEK["panel"] = d
    return _ONBELLEK["panel"]  # type: ignore[return-value]


def _zaman(s: str | None) -> datetime | None:
    if not s:
        return None
    for k in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, k)
        except ValueError:
            continue
    return None


def panel_baslangici() -> datetime:
    """Panelin en eski kaydı. Bundan öncesi için GÖRÜŞ YOK."""
    if "panel_bas" not in _ONBELLEK:
        hepsi = [r["_ts"] for v in _panel().values() for r in v if r["_ts"]]
        if not hepsi:
            raise VeriYok("panelde zaman damgalı kayıt yok")
        _ONBELLEK["panel_bas"] = min(hepsi)
    return _ONBELLEK["panel_bas"]  # type: ignore[return-value]


def _gun_sonu(tarih: date | datetime | None) -> datetime:
    if tarih is None:
        return datetime.now()
    if isinstance(tarih, datetime):
        return tarih
    return datetime(tarih.year, tarih.month, tarih.day, 23, 59, 59)


# --- (1) uygunluk_durumu ---------------------------------------------------


def uygunluk_durumu(
    ticker: str,
    tarih: date | datetime | None = None,
    *,
    karantinali: bool = False,
) -> Durum:
    """`tarih` gününde BİLİNEN en güncel uygunluk kararı.

    Look-ahead yok: `gecerlilik_baslangic <= tarih` olan en geç kayıt.
    Sonraki bildirimler (ve düzeltmeler) görünmez.

    `karantinali=False` (varsayılan): self-check'ten geçmemiş kayıtlar
    **atlanır** ve o tarihteki bir önceki doğrulanmış karar kullanılır.
    Doğrulanmamış bir kararı sessizce vermektense eski ama doğrulanmış
    kararı vermek tercih edilir; `karantinali=True` ile ham davranış
    alınabilir ve `Durum.karantinali` her iki durumda da doğruyu söyler.
    """
    ticker = ticker.strip().upper()
    ev = _evren()
    if ticker not in ev:
        raise BilinmeyenTicker(
            f"{ticker} evrende yok ({len(ev)} pay kodu). "
            "Yazım hatası olabilir; 'kayıt yok' ile karıştırmayın."
        )
    an = _gun_sonu(tarih)
    gun = an.date()

    def _bos(karar: str, sebep: str, kapsam=False) -> Durum:
        return Durum(ticker=ticker, tarih=gun, karar=karar, uygun=None,
                     gorus_var=False, kapsam_disi=kapsam, sebep=sebep)

    # TUZAK 2 — muaf ≠ elenmiş. Kapsam dışılık uygunluğu engellemez.
    beyan = _beyan().get(ticker, "")
    if beyan == KAPSAM_DISI:
        return _bos(
            KAPSAM_DISI,
            "mali sektör muafiyeti: KAFİF doldurmuyor. "
            "Bu UYGUN DEĞİL demek DEĞİLDİR — katılım esaslı finans "
            "kuruluşları (ALBRK, KTLEV) endekste olabilir (spec §0.4).",
            kapsam=True,
        )

    # TUZAK 3 — görüş yok. Tarih panelin başlangıcından önceyse de.
    if an < panel_baslangici():
        return _bos(GORUS_YOK,
                    f"panel {panel_baslangici():%d.%m.%Y}'de başlıyor; "
                    f"{gun:%d.%m.%Y} için kaydımız yok")

    kayitlar = [r for r in _panel().get(ticker, []) if r["_ts"] and r["_ts"] <= an]
    if not kayitlar:
        if beyan in GORUSSUZ_BEYAN:
            return _bos(GORUS_YOK, f"beyan durumu {beyan}: uygunluk yargımız yok")
        return _bos(GORUS_YOK, f"{gun:%d.%m.%Y} itibarıyla panelde kaydı yok")

    if not karantinali:
        temiz = [r for r in kayitlar if (r.get("self_check") or "") != "KALDI"]
        if temiz:
            kayitlar = temiz
        # Hepsi karantinalıysa listeyi boşaltmıyoruz: aşağıda `karantinali`
        # alanı EVET dönecek ve çağıran uyarılmış olacak.

    r = kayitlar[-1]
    karar = r.get("karar", "")
    kar = (r.get("self_check") or "") == "KALDI"

    if karar in GORUSSUZ_KARAR:
        d = _bos(GORUS_YOK, f"karar {karar}: veri eksikliği (kural 2)")
        d.karantinali = kar
        d.gecerlilik_baslangic = r["_ts"]
        d.yil, d.periyot = r.get("yil", ""), r.get("periyot", "")
        d.bildirim_id = r.get("bildirim_id", "")
        return d
    if karar == KAPSAM_DISI:
        return _bos(KAPSAM_DISI, "karar KAPSAM_DISI: muaf, elenmiş değil",
                    kapsam=True)

    return Durum(
        ticker=ticker, tarih=gun, karar=karar,
        uygun=karar in UYGUN_KARARLAR, gorus_var=True, kapsam_disi=False,
        sebep=("karantinalı kayıt: self-check KALDI, karar DOĞRULANMAMIŞ"
               if kar else ""),
        red_kodlari=tuple(k for k in (r.get("red_kodlari") or "").split(",") if k),
        gelir_orani=r.get("gelir_orani", ""),
        varlik_orani=r.get("varlik_orani", ""),
        borc_orani=r.get("borc_orani", ""),
        yil=r.get("yil", ""), periyot=r.get("periyot", ""),
        gecerlilik_baslangic=r["_ts"], bildirim_id=r.get("bildirim_id", ""),
        karantinali=kar,
        onceki_donem_tolerans=(r.get("onceki_donem_tolerans") == "EVET"),
        zincir_notu=r.get("zincir_notu", "") or "",
    )


# --- (2) olaylar -----------------------------------------------------------


def olaylar(
    ticker: str | None = None,
    baslangic: date | datetime | None = None,
    bitis: date | datetime | None = None,
) -> list[_olay.Olay]:
    """Olay serisi; isteğe bağlı pay kodu ve tarih aralığı süzgeci.

    Seri `katilim.olay`'dan **yeniden üretilir**, CSV'den okunmaz: 5.1'in
    kararı gereği `kesinlik` zamana bağlıdır ve dosyaya gömülmez.
    """
    if "olaylar" not in _ONBELLEK:
        try:
            _ONBELLEK["olaylar"] = _olay.olaylari_uret(PANEL_CSV, DONEM_CSV)
        except _olay.OlayGirdisiYok as e:
            raise VeriYok(str(e)) from e
    hepsi: list[_olay.Olay] = _ONBELLEK["olaylar"]  # type: ignore[assignment]
    if ticker:
        t = ticker.strip().upper()
        if t not in _evren():
            raise BilinmeyenTicker(f"{t} evrende yok")
        hepsi = [o for o in hepsi if o.ticker == t]
    if baslangic:
        b = _gun_sonu(baslangic) if isinstance(baslangic, date) else baslangic
        b = b.replace(hour=0, minute=0, second=0) if isinstance(baslangic, date) \
            and not isinstance(baslangic, datetime) else b
        hepsi = [o for o in hepsi if o.olay_ts >= b]
    if bitis:
        hepsi = [o for o in hepsi if o.olay_ts <= _gun_sonu(bitis)]
    return hepsi


# --- Yardımcı okumalar (kart için) ----------------------------------------


def endeks_uyeligi(ticker: str) -> list[str]:
    if "endeks" not in _ONBELLEK:
        d: dict[str, list[str]] = {}
        for r in _satirlar(ENDEKS_CSV, "endeks üyeliği"):
            d.setdefault(r["ticker"], []).append(r["endeks_adi"])
        _ONBELLEK["endeks"] = d
    return sorted(_ONBELLEK["endeks"].get(ticker, []))  # type: ignore[union-attr]


def xktum_gecmisi(ticker: str) -> list[dict]:
    """XKTUM dönem geçmişi (4.1 referansı). Dosya yoksa boş liste."""
    if "bilesen" not in _ONBELLEK:
        try:
            s = _satirlar(BILESEN_CSV, "XKTUM bileşenleri")
        except VeriYok:
            s = []
        d: dict[str, list[dict]] = {}
        for r in s:
            d.setdefault(r["ticker"], []).append(r)
        _ONBELLEK["bilesen"] = d
    kayitlar = _ONBELLEK["bilesen"].get(ticker, [])  # type: ignore[union-attr]
    return sorted(kayitlar, key=lambda r: r["donem_baslangic"])


def duzeltmeler(ticker: str) -> list[dict]:
    try:
        s = _satirlar(DUZELTME_CSV, "düzeltme olayları")
    except VeriYok:
        return []
    return [r for r in s if r["ticker"] == ticker]


def karar_gecmisi(ticker: str) -> list[dict]:
    """Tüm panel satırları — geçersiz kılınanlar DAHİL (soluk gösterilir)."""
    kayitlar = _panel().get(ticker, [])
    return [
        {
            "gecerlilik_baslangic": r["_ts"],
            "yil": r.get("yil", ""), "periyot": r.get("periyot", ""),
            "karar": r.get("karar", ""),
            "gelir_orani": r.get("gelir_orani", ""),
            "varlik_orani": r.get("varlik_orani", ""),
            "borc_orani": r.get("borc_orani", ""),
            "red_kodlari": r.get("red_kodlari", ""),
            "gecerli_kayit": r.get("gecerli_kayit") == "EVET",
            "karantinali": (r.get("self_check") or "") == "KALDI",
            "duzeltme_izi": r.get("duzeltme_izi", "") or "",
            "bildirim_id": r.get("bildirim_id", ""),
            "zincir_notu": r.get("zincir_notu", "") or "",
        }
        for r in kayitlar
    ]


# --- (3) hisse_karti -------------------------------------------------------


def hisse_karti(ticker: str, tarih: date | datetime | None = None) -> dict:
    """Portal ve CLI'nin ORTAK veri kaynağı — ikinci bir doğruluk kaynağı yok."""
    ticker = ticker.strip().upper()
    ev = _evren()
    if ticker not in ev:
        raise BilinmeyenTicker(f"{ticker} evrende yok ({len(ev)} pay kodu)")
    s = ev[ticker]
    an = _gun_sonu(tarih)
    d = uygunluk_durumu(ticker, an)
    ol = olaylar(ticker)
    gecmis = karar_gecmisi(ticker)

    muafiyet = s.get("mali_sektor_muaf", "")
    return {
        "ticker": ticker,
        "unvan": s.get("unvan", ""),
        "pazar": s.get("pazar", "") or "—",
        "sektor": s.get("sektor", "") or "—",
        "muafiyet": ("MUAF" if muafiyet == "EVET"
                     else "BELİRSİZ" if muafiyet == "" else "muaf değil"),
        "beyan_durumu": _beyan().get(ticker, ""),
        "tarih": an,
        "durum": d,
        "endeksler": endeks_uyeligi(ticker),
        "xktum_gecmisi": xktum_gecmisi(ticker),
        "karar_gecmisi": gecmis,
        "olaylar": ol,
        "duzeltmeler": duzeltmeler(ticker),
        # Görünür uyarılar — karta çıkacak
        "uyarilar": _uyarilar(d, gecmis, ol, an),
    }


def _uyarilar(d: Durum, gecmis: list[dict], ol: list, an: datetime) -> list[str]:
    u = []
    if d.karantinali:
        u.append("KARANTİNA: bu kaydın self-check'i KALDI — karar doğrulanmamış.")
    elif any(g["karantinali"] for g in gecmis):
        u.append("Bu pay kodunun geçmişinde karantinalı kayıt var "
                 "(self-check KALDI); güncel karar etkilenmiyor.")
    if any(o.g1_teyitsiz and o.kesinlik(an) == _olay.KESINLIK_HAM for o in ol):
        u.append("G1 TEYİTSİZ: olumlu karar henüz bir düzeltmeyle teyit "
                 "edilmedi. 2.3 ölçtü — karar çeviren 14 düzeltmenin 9'u "
                 "esas sözleşme beyanı, 7'si HAYIR→EVET.")
    if d.zincir_notu:
        u.append(f"ZİNCİR NOTU: {d.zincir_notu}")
    if not d.gorus_var:
        u.append(f"GÖRÜŞ YOK — {d.sebep}")
    return u
