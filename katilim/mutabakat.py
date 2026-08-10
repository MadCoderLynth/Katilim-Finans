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

# Endeks revizyonları dönem başında yürürlüğe giriyor (spec §5.2).
REVIZYON_AYLARI = (5, 10)

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


def son_revizyon(bugun: date) -> date:
    """Yürürlükteki son endeks revizyonu (1 Mayıs / 1 Ekim)."""
    if bugun >= date(bugun.year, 10, 1):
        return date(bugun.year, 10, 1)
    if bugun >= date(bugun.year, 5, 1):
        return date(bugun.year, 5, 1)
    return date(bugun.year - 1, 10, 1)


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
    son: dict[str, dict] = {}
    for r in satirlar:
        t = r["ticker"]
        if t not in son or (r["gonderim_ts"] or "") > (son[t]["gonderim_ts"] or ""):
            son[t] = r
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
    revizyon = son_revizyon(bugun)
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
            s, karar, uygun, uye, ts, revizyon, uyeler, uuid_kodlari, satir is None
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
    s, karar, uygun, uye, ts, revizyon, uyeler, uuid_kodlari, panelde_yok
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

    # 3) DÖNEM UYUMSUZLUĞU — KAFİF son revizyondan sonra yayımlandı.
    if ts and ts.date() > revizyon:
        return SINIF_DONEM, (
            f"KAFİF {ts:%d.%m.%Y}, son endeks revizyonu {revizyon:%d.%m.%Y} — "
            "endeks bunu henüz görmemiş olabilir"
        )

    # 4) KOD AYRIŞMASI — aynı tüzel kişinin başka kodu bizimkinden farklı.
    kardesler = [t for t in uuid_kodlari.get(s.kap_member_uuid, []) if t != s.ticker]
    if kardesler and any((t in uyeler) != uye for t in kardesler):
        return SINIF_KOD, (
            f"aynı tüzel kişinin diğer kodu farklı: {', '.join(kardesler)} "
            "(likidite/fiili dolaşım kaynaklı, kriter kaynaklı değil)"
        )

    return SINIF_GERCEK, f"karar {karar}, XKTUM {'içinde' if uye else 'dışında'}"


# --- Oran ayrışması ile düzeltme ilişkisi ----------------------------------


def oran_ayrismasi_duzeltme_iliskisi(panel_csv: Path | str) -> dict:
    """`oran_ayrisiyor` kayıtlarının kaçı düzeltme bildirimi?

    PNLSN'de sapmanın kaynağı, şirketin kalemi düzeltip TOPLAM satırını
    güncellememesiydi. Örüntü genelse "formun özeti bayat olabilir" bulgusu
    2.3'ü (düzeltme mantığı) ve ileride H5'i bağlar.
    """
    satirlar = _oku(Path(panel_csv), "panel")
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
