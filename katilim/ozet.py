"""Şirket özet sayfası — pazar, sektör, endeks üyeliği (Faz 1.1b).

Rota: `/tr/sirket-bilgileri/ozet/{id}-{slug}` — tüzel kişi başına **tek**
istek. 795 pay kodu var ama 746 tüzel kişi; çoklu kodlu şirketler aynı
sayfayı paylaşıyor, sorgu ekseni bu yüzden slug'dır (1.1'in iki eksen
kuralı).

## Veri nerede

Üç alan da sayfanın RSC yükünde, **çip bağlantılarının href'inde** duruyor
ve değer base64 kodlu:

    /tr/Pazarlar?market=WUlMRElaIFBBWkFS      -> "YILDIZ PAZAR"
    /tr/Sektorler?sector=xLBNQUxBVA           -> "İMALAT"
    /tr/Endeksler?indice=QklTVCBLQVRJTElNIDMw -> "BIST KATILIM 30"

Bu bir **içerik imzasıdır**, konum değil (kural 4): alan sırası veya
sayfadaki yeri değişse de href kalıbı değişmedikçe ayıklama çalışır.

## "Alan yok" ile "sayfa okunamadı" ayrı (kural 7)

Sayfa üç etiketten (`Şirketin Sektörü` vb.) hiçbirini taşımıyorsa
`OzetOkunamadi` **fırlatılır** — sessizce boş sonuç dönülmez. Etiket var
ama çip yoksa alan gerçekten boştur ve `None` kalır; **boş dize değil**,
çünkü "" ile "bilinmiyor" aynı şey değil.

## Endeks üyeliği tarihsel DEĞİL

`endeks_uyeligi.csv` bugünün fotoğrafıdır. `olcum_tarihi` zorunlu alan:
tarihsiz saklanırsa ileride nokta-zaman verisi sanılır ve 4.0'ın
mutabakatı sessizce yanlış döneme bakar.
"""

from __future__ import annotations

import base64
import binascii
import csv
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import rsc

OZET_URL_KALIBI = "https://kap.org.tr/tr/sirket-bilgileri/ozet/{slug}"

EVREN_DIZINI = Path("veri/evren")
ENDEKS_CSV = EVREN_DIZINI / "endeks_uyeligi.csv"
DURUM_CSV = EVREN_DIZINI / "ozet_durumu.csv"

# Sayfanın kendi etiketleri — ayıklamanın çıpası.
ETIKETLER = (
    "Sermaye Piyasası Aracının İşlem Gördüğü Pazar",
    "Şirketin Sektörü",
    "Dahil Olduğu Endeksler",
)

_ALAN_KALIPLARI = {
    "pazar": re.compile(r"/Pazarlar\?market=([A-Za-z0-9+/=_-]+)"),
    "sektor": re.compile(r"/Sektorler\?sector=([A-Za-z0-9+/=_-]+)"),
    "endeks": re.compile(r"/Endeksler\?indice=([A-Za-z0-9+/=_-]+)"),
}

DURUM_OK = "OK"
DURUM_ALAN_EKSIK = "ALAN_EKSIK"
DURUM_OKUNAMADI = "SAYFA_OKUNAMADI"
DURUM_CEKIM_HATASI = "CEKIM_HATASI"
DURUM_SLUG_YOK = "SLUG_YOK"


class OzetOkunamadi(RuntimeError):
    """Beklenen çıpalar yok. 'Alan boş' DEĞİLDİR (kural 7)."""


def _b64_coz(kod: str) -> str | None:
    """URL'deki base64 değeri çözer. Çözülemeyen değer sessizce atılmaz."""
    s = kod.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    try:
        return base64.b64decode(s).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None


def _tekille(degerler: list[str]) -> list[str]:
    """Sırayı KORUYARAK tekilleştirir.

    Sıra anlamlı: sektör listesinde ana sektör önce, alt sektör sonra
    geliyor (ACSEL: 'İMALAT' -> 'KİMYA İLAÇ...'). `set()` kullanmak bu
    bilgiyi yok ederdi.
    """
    gorulen: list[str] = []
    for d in degerler:
        if d and d not in gorulen:
            gorulen.append(d)
    return gorulen


@dataclass
class OzetBilgi:
    pazar: str | None = None
    sektorler: list[str] = field(default_factory=list)
    endeksler: list[str] = field(default_factory=list)
    cozulemeyen: int = 0          # base64'ü açılamayan çip sayısı

    @property
    def sektor(self) -> str | None:
        """Ana ve alt sektör, sayfadaki sırayla. Yoksa None (boş dize değil)."""
        return " / ".join(self.sektorler) if self.sektorler else None

    @property
    def eksik_alanlar(self) -> list[str]:
        eksik = []
        if self.pazar is None:
            eksik.append("pazar")
        if not self.sektorler:
            eksik.append("sektor")
        if not self.endeksler:
            eksik.append("endeksler")
        return eksik


def ozet_ayristir(html: str) -> OzetBilgi:
    """Özet sayfası gövdesi -> pazar / sektör / endeksler."""
    govde = rsc.govde(html)
    etiket_var = any(e in govde or e in html for e in ETIKETLER)

    bulunan: dict[str, list[str]] = {}
    cozulemeyen = 0
    for ad, kalip in _ALAN_KALIPLARI.items():
        degerler = []
        for kod in kalip.findall(govde):
            v = _b64_coz(kod)
            if v is None:
                cozulemeyen += 1
            else:
                degerler.append(v.strip())
        bulunan[ad] = _tekille(degerler)

    if not etiket_var and not any(bulunan.values()):
        raise OzetOkunamadi(
            "Özet sayfasının hiçbir çıpası bulunamadı (etiket yok, çip yok) — "
            "sayfa okunamadı. Bu 'alanlar boş' anlamına GELMEZ."
        )

    pazarlar = bulunan["pazar"]
    return OzetBilgi(
        # Tek pazar bekleniyor; birden çok çıkarsa hepsini taşı, bilgi kaybetme.
        pazar=" / ".join(pazarlar) if pazarlar else None,
        sektorler=bulunan["sektor"],
        endeksler=bulunan["endeks"],
        cozulemeyen=cozulemeyen,
    )


# --- Toplama ---------------------------------------------------------------


@dataclass
class OzetDurumu:
    slug: str | None
    tickerlar: list[str]
    unvan: str
    durum: str
    pazar: str | None = None
    sektor: str | None = None
    endeks_sayisi: int = 0
    not_: str = ""


@dataclass
class Toplama:
    durumlar: list[OzetDurumu] = field(default_factory=list)
    pazarlar: dict[str, str | None] = field(default_factory=dict)   # ticker -> pazar
    sektorler: dict[str, str | None] = field(default_factory=dict)  # ticker -> sektör
    endeksler: dict[str, list[str]] = field(default_factory=dict)   # ticker -> endeksler
    uyarilar: list[str] = field(default_factory=list)


def _slug_gruplari(sirketler) -> dict[str | None, list]:
    gruplar: dict[str | None, list] = {}
    for s in sirketler:
        gruplar.setdefault(s.kap_kfif_slug, []).append(s)
    return gruplar


def ozetleri_topla(
    sirketler,
    cekici,
    *,
    ilerleme=None,
    kontrol_noktasi=None,
    kontrol_araligi: int = 50,
) -> Toplama:
    """Tüzel kişi başına tek istek; sonucu pay kodlarına dağıtır."""
    from .cekici import ÇekimHatası

    toplama = Toplama()
    gruplar = _slug_gruplari(sirketler)
    sirali = sorted(gruplar.items(), key=lambda kv: gruplar[kv[0]][0].ticker)
    agdan = 0

    for sira, (slug, grup) in enumerate(sirali, 1):
        tickerlar = [s.ticker for s in grup]
        durum = OzetDurumu(
            slug=slug, tickerlar=tickerlar, unvan=grup[0].unvan, durum=DURUM_OK
        )

        if not slug:
            # 1.1'de slug eşleşmeyen kayıt yoktu; yine de sessiz geçilmez.
            durum.durum = DURUM_SLUG_YOK
            toplama.durumlar.append(durum)
            toplama.uyarilar.append(f"{'/'.join(tickerlar)}: slug yok, sayfa çekilemedi")
            continue

        url = OZET_URL_KALIBI.format(slug=slug)
        try:
            html = cekici.getir(url)
        except ÇekimHatası as e:
            durum.durum = DURUM_CEKIM_HATASI
            durum.not_ = str(e)[:160]
            toplama.durumlar.append(durum)
            toplama.uyarilar.append(f"{'/'.join(tickerlar)}: {e}")
            agdan += 1
            if ilerleme:
                ilerleme(sira, len(sirali), durum)
            if kontrol_noktasi and agdan % kontrol_araligi == 0:
                kontrol_noktasi(toplama)
            continue

        try:
            bilgi = ozet_ayristir(html)
        except OzetOkunamadi as e:
            durum.durum = DURUM_OKUNAMADI
            durum.not_ = str(e)[:160]
            toplama.durumlar.append(durum)
            toplama.uyarilar.append(f"{'/'.join(tickerlar)}: SAYFA OKUNAMADI")
            agdan += 1
            if ilerleme:
                ilerleme(sira, len(sirali), durum)
            continue

        durum.pazar = bilgi.pazar
        durum.sektor = bilgi.sektor
        durum.endeks_sayisi = len(bilgi.endeksler)
        if bilgi.eksik_alanlar:
            durum.durum = DURUM_ALAN_EKSIK
            durum.not_ = "eksik: " + ", ".join(bilgi.eksik_alanlar)
        if bilgi.cozulemeyen:
            toplama.uyarilar.append(
                f"{'/'.join(tickerlar)}: {bilgi.cozulemeyen} çip base64 çözülemedi"
            )

        for ticker in tickerlar:
            toplama.pazarlar[ticker] = bilgi.pazar
            toplama.sektorler[ticker] = bilgi.sektor
            toplama.endeksler[ticker] = list(bilgi.endeksler)

        toplama.durumlar.append(durum)
        agdan += 1
        if ilerleme:
            ilerleme(sira, len(sirali), durum)
        if kontrol_noktasi and agdan % kontrol_araligi == 0:
            kontrol_noktasi(toplama)

    return toplama


def evrene_bas(sirketler, toplama: Toplama) -> int:
    """`pazar` ve `sektor` alanlarını şirket kayıtlarına yazar.

    Bulunmayan alan `None` bırakılır — boş dizeye çevrilmez.
    """
    yazilan = 0
    for s in sirketler:
        if s.ticker in toplama.pazarlar:
            s.pazar = toplama.pazarlar[s.ticker]
            s.sektor = toplama.sektorler[s.ticker]
            yazilan += 1
    return yazilan


# --- Kalıcılık -------------------------------------------------------------

ENDEKS_BASLIKLARI = ["ticker", "endeks_adi", "olcum_tarihi"]
DURUM_BASLIKLARI = [
    "ticker", "slug", "unvan", "durum", "pazar", "sektor", "endeks_sayisi", "not",
]


def endeks_uyeligi_yaz(
    toplama: Toplama, yol: Path | str = ENDEKS_CSV, *, olcum_tarihi: date | None = None
) -> Path:
    """(ticker, endeks_adi, olcum_tarihi) — uzun format.

    `olcum_tarihi` ZORUNLU: bu tablo bugünün üyeliğidir, tarihsel değil.
    Tarihsiz saklanırsa 4.0 onu nokta-zaman verisi sanır.
    """
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    tarih = (olcum_tarihi or date.today()).isoformat()
    with open(yol, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=ENDEKS_BASLIKLARI)
        w.writeheader()
        for ticker in sorted(toplama.endeksler):
            for endeks in toplama.endeksler[ticker]:
                w.writerow(
                    {"ticker": ticker, "endeks_adi": endeks, "olcum_tarihi": tarih}
                )
    return yol


def durumlari_yaz(toplama: Toplama, yol: Path | str = DURUM_CSV) -> Path:
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=DURUM_BASLIKLARI)
        w.writeheader()
        for d in sorted(toplama.durumlar, key=lambda d: d.tickerlar[0] if d.tickerlar else ""):
            w.writerow(
                {
                    "ticker": "/".join(d.tickerlar),
                    "slug": d.slug or "",
                    "unvan": d.unvan,
                    "durum": d.durum,
                    "pazar": d.pazar or "",
                    "sektor": d.sektor or "",
                    "endeks_sayisi": d.endeks_sayisi,
                    "not": d.not_,
                }
            )
    return yol


def endeks_uyeligi_oku(yol: Path | str = ENDEKS_CSV) -> dict[str, list[str]]:
    yol = Path(yol)
    if not yol.exists():
        return {}
    cikti: dict[str, list[str]] = {}
    with open(yol, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            cikti.setdefault(r["ticker"], []).append(r["endeks_adi"])
    return cikti


# --- Muafiyet yeniden değerlendirmesi --------------------------------------
#
# Spec §0.4'ün muafiyet listesi: aracı kurumlar, bankalar, emeklilik
# şirketleri, finansal kiralama ve faktoring, menkul kıymet yatırım
# ortaklıkları, sigorta, varlık yönetim. Holding ve GSYO DAHİL DEĞİL.
#
# Buradaki eşleme, unvan tabanlı sınıflamanın `None` bıraktığı kayıtları
# SEKTÖR alanıyla yeniden değerlendirir. Yön asimetriktir ve öyle kalmalı:
# yanlış `True` şirketi panelden sessizce düşürür, yanlış `None` yalnız
# el ile bakılacak listeyi uzatır.

# ŞEMSİYE kategoriler: tek başlarına asla belirleyici değildir.
# KAP'ın üst sektörü "FİNANS VE SİGORTA FAALİYETLERİ" — içinde "sigorta"
# geçiyor ama altında §0.4'te olmayanlar da var (tasarruf finansman,
# GYO, holding). Bunu doğrudan eşleştirmek her finans şirketini muaf
# yapardı; yanlış muafiyet şirketi panelden SESSİZCE düşürür.
_SEKTOR_KAPSAYICI = (
    "finans ve sigorta faaliyetleri",
    "finansal kuruluslar",
    "mali kuruluslar",
)

# Şemsiye çıkarıldıktan SONRA kalan metinde bu kalıplardan biri geçiyorsa
# muafiyet kesinleşir. Hepsi spec §0.4'ün listesinden birebir.
_SEKTOR_MUAF = (
    "bankacilik",
    "banka",
    "sigorta",
    "reasurans",
    "emeklilik",
    "araci kurum",
    "finansal kiralama",
    "faktoring",
    "portfoy yonetim",
    # KÖK kullanılıyor: KAP çoğul yazıyor ("MENKUL KIYMET YATIRIM
    # ORTAKLIKLARI"), spec §0.4 tekil ("menkul kıymet yatırım ortaklığı").
    # Tekil kalıp çoğulun içinde geçmiyor (ortakligi ≠ ortakliklari) ve
    # 6 şirket bu yüzden kapanmadan kalıyordu.
    "menkul kiymet yatirim ortaklik",
)

# Bunlar §0.4'e göre muaf DEĞİL; sektör "finans" dese bile muaf sayılmaz.
_SEKTOR_MUAF_DEGIL = (
    "gayrimenkul yatirim ortakligi",
    "girisim sermayesi",
    "holding",
)


def muafiyet_yeniden_degerlendir(unvan: str, sektor: str | None) -> tuple[bool | None, str]:
    """(yeni_muafiyet, gerekçe). `None` = hâlâ karar verilemedi.

    Sektör alanı **tek başına yeterli değil**: KAP'ın sektör sınıflaması
    ("FİNANS VE SİGORTA FAALİYETLERİ") spec §0.4'ün listesinden daha geniş
    — bir GYO veya holding de o sektörde görünebiliyor. Bu yüzden yalnız
    kalıp KESİN olduğunda kapatılır.
    """
    from .metin import normalize

    n_sektor = normalize(sektor or "")
    n_unvan = normalize(unvan or "")

    if not n_sektor:
        return None, "sektör alanı boş — kapatılamadı"
    if any(k in n_sektor or k in n_unvan for k in _SEKTOR_MUAF_DEGIL):
        return False, f"§0.4 muafiyet listesinde yok (sektör: {sektor})"

    # Şemsiye kategoriyi düş; karar ancak ALT sektörle verilir.
    belirleyici = n_sektor
    for kapsayici in _SEKTOR_KAPSAYICI:
        belirleyici = belirleyici.replace(kapsayici, " ")
    belirleyici = " ".join(belirleyici.split())

    if not belirleyici:
        return None, (
            f"sektör yalnız şemsiye kategori ('{sektor}') — §0.4'ün listesi "
            "daha dar, alt sektör olmadan kapatılamaz; BELİRSİZ kaldı"
        )
    for kalip in _SEKTOR_MUAF:
        if kalip in belirleyici:
            return True, f"alt sektör '{sektor}' §0.4'teki '{kalip}' ile eşleşti"
    return None, f"sektör '{sektor}' §0.4 listesine birebir oturmuyor — belirsiz kaldı"


def belirsizleri_yeniden_degerlendir(sirketler) -> list[tuple]:
    """Muafiyeti `None` olan kayıtları sektör alanıyla yeniden değerlendirir.

    **Yalnız `None` olanlara dokunur.** Zaten `True`/`False` olan bir kaydı
    değiştirmez: unvan tabanlı sınıflama 1.1'de doğrulandı, sektör onu
    ezmemeli.

    Dönen liste (sirket, eski, yeni, gerekçe) dörtlüleridir — kapatılan da
    kapatılamayan da raporlanır, sessiz değişiklik olmaz.
    """
    sonuc = []
    for s in sirketler:
        if s.mali_sektor_muaf is not None:
            continue
        yeni, gerekce = muafiyet_yeniden_degerlendir(s.unvan, s.sektor)
        sonuc.append((s, s.mali_sektor_muaf, yeni, gerekce))
        if yeni is not None:
            s.mali_sektor_muaf = yeni
    return sonuc
