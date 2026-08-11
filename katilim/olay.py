"""Look-ahead'sız uygunluk olay serisi — Faz 5.1.

Panel bir **durum** tablosudur: her (ticker, bildirim) için o anın etiketi.
Bu modül ondan bir **olay** serisi çıkarır — durumun ne zaman ve hangi yönde
değiştiği. Momentum sistemine bağlanacak olan budur.

## Neden düzeltme penceresi tasarıma giriyor

2.3 ölçtü (n=181): düzeltme gecikmesi **medyan 21 gün · p90 35 · p95 38 ·
max 55**; karar çeviren 14 düzeltmenin hepsi ≤31 gün. Düzeltme oranı 163
dönem / ~1.100 geçerli kayıt ≈ **%15**.

Bu, bilgi öncüllüğü penceresini büyük ölçüde tüketiyor. DEVIR_NOTU §2.5
"4-8 hafta" diyordu; gerçek kullanılabilir pencere daha dar:

    DOGUB 2026/6 Aylık  30.07.2026 -> revizyon 01.10 = 63 gün
                        p95 (38 gün) düşünce temiz sinyal ~25 gün
    PNLSN 2025/Yıllık   25.02.2026 -> revizyon 01.05 = 65 gün -> ~27 gün

Yani sinyal var ama **2-4 hafta**. Max gecikmeyi (55 gün) beklemek pencereyi
neredeyse kapatıyor. Ödünleşme gerçek: erken işlem pencereyi genişletir ama
düzeltme riskini üstlenir.

## Olgunluk tarih olarak saklanır, etiket olarak DEĞİL

`kesinlik` zamana bağlıdır: bugün HAM olan bir olay 40 gün sonra OLGUN olur.
Tek bir etiket saklamak, backtest'i o etiketin hesaplandığı ana kilitler.
Bu yüzden olay iki **eşik zamanı** taşır:

    olgunlasma_ts  = olay_ts + 38 gün          (p95 düzeltme penceresi)
    kesinlesme_ts  = sonraki DÖNEMİN ilk yayını (dönem kapandı)

Backtester t anında `kesinlik(olay, t)` çağırır; ileriye dönük bir bilgi
kullanmış olmaz, çünkü karşılaştırma kendi saatiyle yapılır. `kesinlesme_ts`
olay anına göre gelecektedir ve **karar alanlarını asla etkilemez** —
`test_olay.py` bunu ayrıca denetliyor.

## Düzeltme İPTAL değil KARŞI OLAY üretir

Bir olayı sonradan silmek look-ahead'a davetiyedir: geçmiş bir tarihte
gerçekten yayımlanmış ve işlem yapılabilir olan bir sinyali yok saymak,
backtest'i imkânsız biçimde iyi gösterir. Düzeltme geldiğinde eski olay
yerinde kalır; düzeltmenin kendi zaman damgasıyla **ters yönde yeni bir
olay** üretilir (`karsi_olay=True`).

## G1 kapısı en güvenilmez (2.3 bulgusu)

Karar çeviren 14 düzeltmenin **9'u `b1_1`/`b1_2`** (esas sözleşme beyanları)
ve **7'si False→True**. Esas sözleşme üç haftada değişmez; bunlar eksik
beyanın düzeltilmesidir. Yani ilk bildirimin "G1 temiz" demesi, düzeltilmiş
bir bildirimin aynı şeyi demesinden **zayıf kanıttır**. Henüz düzeltmeyle
teyit edilmemiş olumlu kararlar `g1_teyitsiz` ile işaretlenir.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .karar import LIMIT

OLAY_CSV = Path("veri/panel/olaylar.csv")

# --- Olay tipleri ----------------------------------------------------------

UYGUNLUK_KAYBI = "UYGUNLUK_KAYBI"
UYGUNLUK_KAZANIMI = "UYGUNLUK_KAZANIMI"
TOLERANSA_DUSUS = "TOLERANSA_DUSUS"
TOLERANSTAN_CIKIS = "TOLERANSTAN_CIKIS"
KILPAYI_UYARI = "KILPAYI_UYARI"

OLUMLU_KARARLAR = ("UYGUN", "TOLERANSTA")

# --- Ölçülmüş eşikler (2.3, n=181) — TAHMİN DEĞİL --------------------------
#
# Bu sabitler gevşetilirse olgunluk etiketi gerçeğinden erken "güvenli"
# der ve düzeltme riski görünmez olur. Değiştirilecekse önce yeniden
# ölçülmeli (`veri/panel/duzeltme_olaylari.csv`).
DUZELTME_MEDYAN_GUN = 21
DUZELTME_P95_GUN = 38
DUZELTME_MAX_GUN = 55
# Karar çeviren düzeltmelerin hepsi bu sürenin altında geldi.
KARAR_CEVIREN_MAX_GUN = 31

# --- İKİNCİ düzeltme penceresi: AYRI BİR DAĞILIM ---------------------------
#
# 38 gün, **ilk bildirimden ilk düzeltmeye** dağılımının p95'idir. Karşı olay
# zaten bir düzeltmedir; onun riski "ikinci bir düzeltme gelir mi" sorusudur
# ve o dağılım çok daha dar (ölçüldü: 163 düzeltme grubunun 16'sında, yani
# %9,8'inde ikinci düzeltme var; ilk→ikinci gecikme medyan 4 · p95 22 · max 22).
#
# İlk olayın eşiğini karşı olaya uygulamak, karşı olay penceresini **yapay
# olarak negatif** gösteriyordu (5.1 raporu: −10 gün). Doğru eşikle pencere
# gerçek değerine dönüyor.
IKINCI_DUZELTME_ORANI = 0.098
IKINCI_DUZELTME_MEDYAN_GUN = 4
IKINCI_DUZELTME_P95_GUN = 22
IKINCI_DUZELTME_MAX_GUN = 22


def olgunlasma_penceresi(karsi_olay: bool) -> int:
    """Olayın olgunlaşması için beklenecek gün — olay tipine duyarlı.

    İlk bildirim p95=38 gün (ilk→ilk düzeltme), karşı olay p95=22 gün
    (ilk→ikinci düzeltme). İkisi ayrı dağılımdır; tek eşik kullanmak
    karşı olayları haksız yere değersiz gösterir.
    """
    return IKINCI_DUZELTME_P95_GUN if karsi_olay else DUZELTME_P95_GUN

# Kılpayı bandı: limite bu kadar puan kalmışsa uyarı. Gerekçe THY 2025:
# gelir oranı %4,92, limit %5 — 0,08 puan mesafede ve endeks dışı.
KILPAYI_ESIK = Decimal("0.5")

# Olgunluk kademeleri
KESINLIK_HAM = "HAM"        # yeni yayım; p95 düzeltme penceresi açık
KESINLIK_OLGUN = "OLGUN"    # >38 gün geçti, düzeltme gelmedi
KESINLIK_KESIN = "KESIN"    # sonraki dönem yayımlandı, dönem kapandı


class OlayGirdisiYok(RuntimeError):
    """Girdi dosyası yok/okunamadı. 'Olay yok' DEĞİLDİR (kural 7)."""


# --- Model -----------------------------------------------------------------


@dataclass
class Olay:
    ticker: str
    olay_tipi: str
    olay_ts: datetime                 # = KAFİF gonderim_ts (spec §5.1)
    endeks_yururluk_ts: date | None   # olaydan sonraki ilk revizyon
    onceki_karar: str
    yeni_karar: str
    red_kodlari: str
    bildirim_id: str
    yil: str
    periyot: str
    duzeltme_izi: str
    karsi_olay: bool = False          # düzeltmenin ürettiği ters olay
    g1_teyitsiz: bool = False         # olumlu karar, düzeltmeyle teyit edilmemiş
    kilpayi_kriterleri: str = ""      # KILPAYI_UYARI için hangi oran(lar)

    # --- Olgunluk: TARİH olarak saklanır, etiket olarak değil -------------
    olgunlasma_ts: datetime | None = None   # olay_ts + p95
    kesinlesme_ts: datetime | None = None   # sonraki dönemin ilk yayını

    # --- Look-ahead denetimi ----------------------------------------------
    # Bu olayın KARAR alanlarını üretirken okunan her girdinin zaman
    # damgası. Hepsi `olay_ts`'ten küçük veya eşit OLMALI; `test_olay.py`
    # bunu satır satır doğruluyor. Olgunluk alanları buraya GİRMEZ —
    # onlar bilinçli olarak ileriye dönüktür ve karar alanlarını etkilemez.
    girdi_ts: tuple[datetime, ...] = field(default_factory=tuple)

    def kesinlik(self, an: datetime | date | None = None) -> str:
        """`an` anındaki olgunluk kademesi. Look-ahead yok: karşılaştırma
        çağıranın kendi saatiyle yapılır."""
        an = an or datetime.now()
        if isinstance(an, date) and not isinstance(an, datetime):
            an = datetime(an.year, an.month, an.day, 23, 59, 59)
        if self.kesinlesme_ts and an >= self.kesinlesme_ts:
            return KESINLIK_KESIN
        if self.olgunlasma_ts and an >= self.olgunlasma_ts:
            return KESINLIK_OLGUN
        return KESINLIK_HAM


# --- Girdiler --------------------------------------------------------------


def _oku(yol: Path, ad: str) -> list[dict]:
    if not Path(yol).exists():
        raise OlayGirdisiYok(f"{ad} yok: {yol}")
    with open(yol, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _ts(deger: str | None) -> datetime | None:
    if not deger:
        return None
    for kalip in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(deger, kalip)
        except ValueError:
            continue
    return None


def _oran(deger: str | None) -> Decimal | None:
    if deger in (None, ""):
        return None
    try:
        return Decimal(deger)
    except InvalidOperation:
        return None


def panel_oku(panel_csv: Path | str) -> dict[str, list[dict]]:
    """Pay kodu -> gönderim sırasına dizilmiş TÜM panel satırları.

    `gecerli_kayit` süzgeci YOK ve bu bilinçli: geçersiz kılınmış bir kayıt
    da kendi penceresinde canlı bir sinyaldi. Onu atlamak düzeltmenin
    ürettiği karşı olayı da yok ederdi.
    """
    satirlar = _oku(Path(panel_csv), "panel")
    if not satirlar:
        raise OlayGirdisiYok(
            f"panel satırsız: {panel_csv} — 'olay yok' ile 'panel okunamadı' "
            "aynı şey değil (kural 7)"
        )
    ts_alan = ("gonderim_ts" if "gonderim_ts" in satirlar[0]
               else "gecerlilik_baslangic")
    seri: dict[str, list[dict]] = {}
    for r in satirlar:
        r["_ts"] = _ts(r.get(ts_alan))
        seri.setdefault(r["ticker"], []).append(r)
    for v in seri.values():
        # Zaman damgasız kayıt sona — bilinmeyen tarihi geçmişe koymak
        # sonraki olayları sessizce değiştirirdi (3.1 ile aynı disiplin).
        v.sort(key=lambda r: (r["_ts"] is None, r["_ts"] or datetime.min))
    return seri


@dataclass(frozen=True)
class RevizyonTakvimi:
    """Duyurusu geçmişte kalmış revizyonlar — ileriye bakmadan yürürlük."""

    kayitlar: tuple[tuple[date, date, date], ...]   # (duyuru, baslangic, bitis)

    def sonraki_yururluk(self, an: datetime) -> date | None:
        """`an` anında bilinen bir sonraki revizyon yürürlük tarihi.

        **Look-ahead'sız türetme.** `an` anında yalnız DUYURUSU geçmiş
        revizyonlar bilinir. Bunların en sonuncusunun bitiş tarihi de o
        duyuruyla birlikte yayımlanmıştır; bir sonraki revizyon o bitişin
        ertesi günü yürürlüğe girer.

        Bu kural, duyurudan sonra yayımlanan KAFİF'i de doğru ele alır:
        28.09.2025'te yayımlanan bir form, 24.09'da duyurulmuş 01.10.2025
        listesini etkileyemez ve kural doğru biçimde 01.05.2026 döner.
        """
        gecmis = [k for k in self.kayitlar if k[0] <= an.date()]
        if not gecmis:
            return None
        return max(gecmis, key=lambda k: k[0])[2] + timedelta(days=1)

    def duyuru_ts(self, an: datetime) -> datetime | None:
        """Yürürlük türetiminde kullanılan girdinin zaman damgası."""
        gecmis = [k for k in self.kayitlar if k[0] <= an.date()]
        if not gecmis:
            return None
        d = max(gecmis, key=lambda k: k[0])[0]
        return datetime(d.year, d.month, d.day)


def takvim_oku_yardimci(
    donem_csv: Path | str = "veri/referans/xktum_donemler.csv",
) -> RevizyonTakvimi:
    """Testler ve tanı için: takvimi varsayılan yoldan okur."""
    return takvim_oku(donem_csv)


def takvim_oku(donem_csv: Path | str) -> RevizyonTakvimi:
    satirlar = _oku(Path(donem_csv), "revizyon dönemleri")
    if not satirlar:
        raise OlayGirdisiYok(f"revizyon takvimi satırsız: {donem_csv}")
    kayitlar = []
    for r in satirlar:
        if not r.get("duyuru_tarihi"):
            raise OlayGirdisiYok(
                f"{r['donem_baslangic']} döneminin duyuru tarihi yok — "
                "yürürlük türetimi duyuruya dayanıyor"
            )
        kayitlar.append((
            date.fromisoformat(r["duyuru_tarihi"]),
            date.fromisoformat(r["donem_baslangic"]),
            date.fromisoformat(r["donem_bitis"]),
        ))
    return RevizyonTakvimi(tuple(sorted(kayitlar)))


# --- Olay üretimi ----------------------------------------------------------


def _gecis_tipi(onceki: str, yeni: str) -> str | None:
    """İki karar arasındaki geçişin olay tipi. Değişim yoksa `None`."""
    if onceki == yeni:
        return None
    onceki_olumlu = onceki in OLUMLU_KARARLAR
    yeni_olumlu = yeni in OLUMLU_KARARLAR
    if onceki_olumlu and not yeni_olumlu:
        return UYGUNLUK_KAYBI
    if not onceki_olumlu and yeni_olumlu:
        return UYGUNLUK_KAZANIMI
    # İkisi de olumlu: tolerans bandına giriş/çıkış
    if onceki == "UYGUN" and yeni == "TOLERANSTA":
        return TOLERANSA_DUSUS
    if onceki == "TOLERANSTA" and yeni == "UYGUN":
        return TOLERANSTAN_CIKIS
    # İkisi de olumsuz (ör. UYGUN_DEGIL -> BELIRSIZ): uygunluk yönü
    # değişmedi, olay üretilmez.
    return None


def _kilpayi_kriterleri(satir: dict) -> list[str]:
    """Limite `KILPAYI_ESIK` puandan yakın ama AŞMAMIŞ oranlar.

    Aşan oran zaten kendi kapısından olay üretiyor; kılpayı bunun
    öncesindeki uyarı seviyesidir (THY %4,92 vakası).
    """
    yakin = []
    for ad, sutun in (("gelir", "gelir_orani"), ("varlik", "varlik_orani"),
                      ("borc", "borc_orani")):
        o = _oran(satir.get(sutun))
        if o is None:
            continue
        lim = LIMIT[ad]
        if lim - KILPAYI_ESIK <= o <= lim:
            yakin.append(f"{ad}={o}")
    return yakin


def olaylari_uret(
    panel_csv: Path | str = "veri/panel/panel.csv",
    donem_csv: Path | str = "veri/referans/xktum_donemler.csv",
    *,
    kesim: datetime | None = None,
) -> list[Olay]:
    """Panelden look-ahead'sız olay serisi üretir.

    `kesim` verilirse panel o ana kadar kırpılır — yani seri, o tarihte
    elimizde olan veriyle yeniden üretilir. Nokta-zaman doğrulamasının
    (ve `test_olay.py`'deki look-ahead denetiminin) dayanağı budur.
    """
    return olay_serisi(panel_oku(panel_csv), takvim_oku(donem_csv), kesim=kesim)


def olay_serisi(
    seri: dict[str, list[dict]],
    takvim: RevizyonTakvimi,
    *,
    kesim: datetime | None = None,
) -> list[Olay]:
    """Okunmuş panel serisinden olayları üretir.

    Her şirketin kayıtları **gönderim sırasıyla** yürütülür ve o ana kadar
    canlı olan karar taşınır. Bir düzeltme geldiğinde eski olay silinmez;
    düzeltme kendi zaman damgasıyla ters yönde yeni bir olay üretir.
    """
    if kesim is not None:
        seri = {
            t: [r for r in v if r["_ts"] is not None and r["_ts"] <= kesim]
            for t, v in seri.items()
        }
    olaylar: list[Olay] = []

    for ticker, satirlar in sorted(seri.items()):
        canli_karar = ""            # o ana kadar yayımlanmış son karar
        kilpayi_acik = False        # kılpayı uyarısı hâlihazırda açık mı
        gorulen_donemler: set[tuple] = set()

        # Dönem -> o dönemin ilk yayın anı. `kesinlesme_ts` için gerekli;
        # KARAR alanlarında KULLANILMAZ (aşağıda ayrıca işaretli).
        donem_ilk_yayin: dict[tuple, datetime] = {}
        for r in satirlar:
            a = (r.get("yil"), r.get("periyot"))
            if r["_ts"] and a not in donem_ilk_yayin:
                donem_ilk_yayin[a] = r["_ts"]
        donem_sirasi = sorted(donem_ilk_yayin, key=lambda a: donem_ilk_yayin[a])
        sonraki_donem_yayini = {
            d: donem_ilk_yayin[donem_sirasi[i + 1]]
            for i, d in enumerate(donem_sirasi) if i + 1 < len(donem_sirasi)
        }

        for r in satirlar:
            ts = r["_ts"]
            if ts is None:
                # Zaman damgası olmayan kayıttan olay üretilmez: olayın
                # zamanı spec §5.1 gereği gonderim_ts'tir, uydurulamaz.
                continue
            anahtar = (r.get("yil"), r.get("periyot"))
            yeni_karar = r.get("karar", "")
            duzeltme_izi = r.get("duzeltme_izi", "") or ""
            ayni_donem_tekrari = anahtar in gorulen_donemler
            gorulen_donemler.add(anahtar)

            yururluk = takvim.sonraki_yururluk(ts)
            duyuru_ts = takvim.duyuru_ts(ts)
            # KARAR alanlarının girdileri: bu panel satırı + yürürlüğü
            # türeten revizyon duyurusu. İkisi de olay anından ÖNCE.
            girdi = tuple(t for t in (ts, duyuru_ts) if t is not None)

            def _olay(tip: str, onceki: str, *, karsi_olay: bool, **kw) -> Olay:
                return Olay(
                    ticker=ticker, olay_tipi=tip, olay_ts=ts,
                    endeks_yururluk_ts=yururluk,
                    onceki_karar=onceki, yeni_karar=yeni_karar,
                    red_kodlari=r.get("red_kodlari", "") or "",
                    bildirim_id=r.get("bildirim_id", "") or "",
                    yil=r.get("yil", "") or "", periyot=r.get("periyot", "") or "",
                    duzeltme_izi=duzeltme_izi,
                    karsi_olay=karsi_olay,
                    # Eşik olay tipine duyarlı: karşı olay zaten bir
                    # düzeltmedir, riski "ikinci düzeltme" dağılımından gelir.
                    olgunlasma_ts=ts + timedelta(
                        days=olgunlasma_penceresi(karsi_olay)
                    ),
                    kesinlesme_ts=sonraki_donem_yayini.get(anahtar),
                    girdi_ts=girdi,
                    **kw,
                )

            tip = _gecis_tipi(canli_karar, yeni_karar) if canli_karar else None
            if tip:
                olaylar.append(_olay(
                    tip, canli_karar,
                    # Aynı dönemin ikinci kaydı ⇒ bu bir düzeltmenin
                    # ürettiği KARŞI OLAY. Eski olay silinmiyor.
                    karsi_olay=ayni_donem_tekrari,
                    # G1 zayıflığı (2.3): olumlu karar henüz bir
                    # düzeltmeyle teyit edilmemişse işaretlenir.
                    g1_teyitsiz=(yeni_karar in OLUMLU_KARARLAR
                                 and not duzeltme_izi),
                ))

            # Kılpayı uyarısı geçişten bağımsız: aynı kayıt hem uygunluk
            # olayı hem kılpayı uyarısı doğurabilir.
            kriterler = _kilpayi_kriterleri(r)
            if kriterler and not kilpayi_acik:
                olaylar.append(_olay(
                    KILPAYI_UYARI, canli_karar,
                    kilpayi_kriterleri="; ".join(kriterler),
                    karsi_olay=ayni_donem_tekrari,
                    g1_teyitsiz=(yeni_karar in OLUMLU_KARARLAR
                                 and not duzeltme_izi),
                ))
            kilpayi_acik = bool(kriterler)

            canli_karar = yeni_karar

    olaylar.sort(key=lambda o: (o.olay_ts, o.ticker, o.olay_tipi))
    return olaylar


# --- Kalıcılık -------------------------------------------------------------

BASLIKLAR = [
    "ticker", "olay_tipi", "olay_ts", "endeks_yururluk_ts",
    "onceki_karar", "yeni_karar", "red_kodlari", "bildirim_id",
    "yil", "periyot", "duzeltme_izi", "karsi_olay", "g1_teyitsiz",
    "kilpayi_kriterleri", "olgunlasma_ts", "kesinlesme_ts",
    "oncul_gun",
]

_EH = {True: "EVET", False: "HAYIR"}


def _satir(o: Olay) -> dict:
    oncul = ""
    if o.endeks_yururluk_ts:
        oncul = (o.endeks_yururluk_ts - o.olay_ts.date()).days
    return {
        "ticker": o.ticker,
        "olay_tipi": o.olay_tipi,
        "olay_ts": o.olay_ts.strftime("%Y-%m-%d %H:%M:%S"),
        "endeks_yururluk_ts": o.endeks_yururluk_ts.isoformat()
        if o.endeks_yururluk_ts else "",
        "onceki_karar": o.onceki_karar,
        "yeni_karar": o.yeni_karar,
        "red_kodlari": o.red_kodlari,
        "bildirim_id": o.bildirim_id,
        "yil": o.yil,
        "periyot": o.periyot,
        "duzeltme_izi": o.duzeltme_izi,
        "karsi_olay": _EH[o.karsi_olay],
        "g1_teyitsiz": _EH[o.g1_teyitsiz],
        "kilpayi_kriterleri": o.kilpayi_kriterleri,
        "olgunlasma_ts": o.olgunlasma_ts.strftime("%Y-%m-%d %H:%M:%S")
        if o.olgunlasma_ts else "",
        "kesinlesme_ts": o.kesinlesme_ts.strftime("%Y-%m-%d %H:%M:%S")
        if o.kesinlesme_ts else "",
        "oncul_gun": oncul,
    }


def yaz(olaylar: list[Olay], yol: Path | str = OLAY_CSV) -> Path:
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=BASLIKLAR)
        w.writeheader()
        w.writerows(_satir(o) for o in olaylar)
    return yol


# --- Özet ------------------------------------------------------------------


def ozet(olaylar: list[Olay], an: datetime | None = None) -> dict:
    """Rapor için sayımlar. `an` verilmezse olgunluk BUGÜNE göre."""
    an = an or datetime.now()
    tip: dict[str, int] = {}
    kesinlik: dict[str, int] = {}
    for o in olaylar:
        tip[o.olay_tipi] = tip.get(o.olay_tipi, 0) + 1
        k = o.kesinlik(an)
        kesinlik[k] = kesinlik.get(k, 0) + 1
    onculler = [
        (o.endeks_yururluk_ts - o.olay_ts.date()).days
        for o in olaylar if o.endeks_yururluk_ts
    ]
    onculler.sort()
    # Temiz pencere olay tipine duyarlı hesaplanır: ilk bildirimde p95=38,
    # karşı olayda p95=22 gün. Tek eşik kullanmak karşı olayları haksız
    # yere değersiz gösterirdi.
    temiz = sorted(
        (o.endeks_yururluk_ts - o.olay_ts.date()).days
        - olgunlasma_penceresi(o.karsi_olay)
        for o in olaylar if o.endeks_yururluk_ts
    )
    return {
        "olay": len(olaylar),
        "pay_kodu": len({o.ticker for o in olaylar}),
        "tip": dict(sorted(tip.items(), key=lambda kv: -kv[1])),
        "kesinlik": dict(sorted(kesinlik.items())),
        "karsi_olay": sum(1 for o in olaylar if o.karsi_olay),
        "g1_teyitsiz": sum(1 for o in olaylar if o.g1_teyitsiz),
        "oncul_gun_medyan": onculler[len(onculler) // 2] if onculler else None,
        "oncul_gun_min": onculler[0] if onculler else None,
        "oncul_gun_max": onculler[-1] if onculler else None,
        "temiz_pencere_medyan": temiz[len(temiz) // 2] if temiz else None,
    }
