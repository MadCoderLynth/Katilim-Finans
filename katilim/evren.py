"""BIST şirket evreni — Spec §1.1, Faz 1.1.

Kaynak: `/tr/bist-sirketler`. Tek istek, 746 şirket.

**Veri DOM tablosundan değil, sayfaya gömülü RSC (Next.js flight) yükündeki
JSON'dan okunur.** Ölçüm (ROTA_KESFI_RAPORU.md §2) sayfanın aynı listeyi iki
kez taşıdığını gösterdi: bir kez `<table>` içinde, bir kez yapılandırılmış
JSON olarak. İkincisi ayrıştırma gerektirmiyor, alan adları açık.

Sayısal id + slug (`/tr/kfif/{id}-{slug}` rotasının anahtarı) yalnız DOM'da,
satırın `<a href>`'inde. Yani iki yapıyı **eşlemek** gerekiyor.

Değiştirilemez kural 4 burada da geçerli: eşleme **konuma göre yapılmaz.**
"İkisi de 746 kayıt, sırayla eşleşir" varsayımı, KAP tarafında tek satır
kaymasında sessizce yanlış şirkete slug atar — ve bu hata hiçbir yerde
hata vermez, yalnızca yanlış veri üretir. Eşleme iki içerik anahtarıyla
yapılır: satırın ticker hücresi ve unvandan türetilen slug.

Eşleşmeyen kayıt **düşürülmez**; `kap_kfif_slug=None` ile listede kalır ve
`EvrenRaporu` içinde sayılır.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

from .metin import normalize

BIST_SIRKETLER_URL = "https://kap.org.tr/tr/bist-sirketler"

EVREN_DIZINI = Path("veri/evren")
EVREN_CSV = EVREN_DIZINI / "sirketler.csv"
ARSIV_DIZINI = EVREN_DIZINI / "arsiv"

# RSC yükündeki kayıt: alanları sabit sırada, tek satırda.
_KAYIT_RE = re.compile(r"\{\"mkkMemberOid\":.*?\"kapMemberType\":\"[^\"]*\"\}")
_OZET_HREF_RE = re.compile(r"/tr/sirket-bilgileri/ozet/(\d+-[a-z0-9-]+)")
_TICKER_RE = re.compile(r"^[A-Z0-9]{3,6}$")


# --- Muafiyet sınıflaması --------------------------------------------------
#
# Spec §0.4'teki "KAFİF doldurmayan" listesinden, unvan üzerinden türetilir.
# Yön asimetrik: yanlış MUAF işareti şirketi panelden sessizce düşürür,
# yanlış BELİRSİZ işareti yalnızca el ile bakılacak listeyi uzatır.
# Bu yüzden şüphede olan her kalıp `None`'a gider, `True`'ya değil.

# Bunlar muafiyet kalıplarını YENER. Spec §0.4: "Holding ve GSYO dahil —
# onlar dolduruyor." GYO da doldurur; yalnız menkul kıymet YO muaftır.
_MUAF_DEGIL = (
    "holding",
    "gayrimenkul yatirim ortakligi",
    "girisim sermayesi yatirim ortakligi",
)

# Belirsiz kalıbını yenen kesin muafiyet. 'X Menkul Kıymet Yatırım Ortaklığı'
# hem buraya hem 'yatirim ortakligi' belirsizine uyar; MKYO olduğu açık.
_MUAF_KESIN = (
    "menkul kiymet yatirim ortakligi",
    "menkul kiymetler yatirim ortakligi",   # ATLAS böyle yazıyor (çoğul)
)

_MUAF = (
    # 'banka' değil 'bank': AKBANK, ŞEKERBANK, ANADOLUBANK normalize edilince
    # 'akbank' oluyor ve 'banka' kalıbı tutmuyor — 8 tüzel kişi kaçıyordu.
    "bank",               # akbank, şekerbank, bankası, bankacılık, katılım bankası
    "emeklilik",
    "finansal kiralama",
    "leasing",
    "faktoring",
    "sigorta",
    "varlik yonetim",
    "menkul degerler",    # aracı kurum
    "menkul kiymetler",
    "araci kurum",
)

# Muaf olabilir ama spec §0.4 listesinde birebir yok. El ile bakılacak.
# _MUAF'tan ÖNCE bakılır: 'AKTİF BANK SUKUK VARLIK KİRALAMA' bir sukuk
# aracıdır, banka değil — 'bank' kalıbına takılıp muaf sayılmamalı.
_BELIRSIZ = (
    "yatirim ortakligi",   # sade 'Yatırım Ortaklığı' — MKYO mu, başka mı?
    "varlik kiralama",     # sukuk SPV'si; unvanında banka adı geçebiliyor
    "reasurans",           # sigorta mevzuatına tabi ama listede adı geçmiyor
    "tasarruf finansman",  # KTLEV KAFİF doldurmuyor (Spec §0.4) ama listede yok
    "portfoy yonetim",
)


def mali_sektor_muaf_mi(unvan: str) -> bool | None:
    """Unvandan muafiyet çıkarımı. `None` = karar verilemedi, el ile bakılacak.

    Öncelik sırası, çakışan kalıplar yüzünden anlamlı:

      1. muaf DEĞİL istisnaları  — holding, GYO, GSYO (Spec §0.4)
      2. kesin muaf              — MKYO; 'yatirim ortakligi' belirsizini yener
      3. belirsiz                — şüpheli; 'bank' gibi geniş kalıplardan ÖNCE
      4. muaf kalıpları
      5. hiçbiri                 — muaf değil
    """
    n = normalize(unvan)
    if not n:
        return None
    if any(k in n for k in _MUAF_DEGIL):
        return False
    if any(k in n for k in _MUAF_KESIN):
        return True
    if any(k in n for k in _BELIRSIZ):
        return None
    if any(k in n for k in _MUAF):
        return True
    return False


# --- Model -----------------------------------------------------------------


@dataclass
class Sirket:
    """Spec §1.1. `pazar` ve `sektor` bu kaynakta yok (ROTA_KESFI_RAPORU §2)."""

    ticker: str
    unvan: str
    kap_member_uuid: str          # mkkMemberOid — bildirim sorgusunun anahtarı
    kap_kfif_slug: str | None     # '1107-turk-hava-yollari-a-o' — kfif rotası
    sehir: str | None = None
    denetci: str | None = None
    pazar: str | None = None      # ikinci kaynak gerekiyor
    sektor: str | None = None     # ikinci kaynak gerekiyor
    mali_sektor_muaf: bool | None = None

    @property
    def eslesme_eksik(self) -> bool:
        return self.kap_kfif_slug is None


@dataclass
class EvrenRaporu:
    """Ayrıştırmanın kendi kendini denetleme çıktısı.

    Sessiz kayıp olmasın diye var: eşleşmeyen her satır burada sayılır.
    """

    rsc_kayit: int = 0       # tüzel kişi sayısı
    dom_ticker: int = 0      # DOM'daki benzersiz pay kodu (satır değil)
    eslesen: int = 0
    coklu_kod: list[str] = field(default_factory=list)
    slug_bulunamayan: list[str] = field(default_factory=list)
    domda_olup_rscde_olmayan: list[str] = field(default_factory=list)
    zayif_eslesme: list[str] = field(default_factory=list)
    muaf: int = 0
    muaf_degil: int = 0
    belirsiz: list[str] = field(default_factory=list)

    def rapor(self) -> str:
        satirlar = [
            f"  RSC kaydı        : {self.rsc_kayit} tüzel kişi",
            f"  DOM pay kodu     : {self.dom_ticker}",
            f"  çoklu pay kodu   : {len(self.coklu_kod)} tüzel kişi "
            f"({', '.join(self.coklu_kod[:5])}{'…' if len(self.coklu_kod) > 5 else ''})",
            f"  slug eşleşen     : {self.eslesen}",
        ]
        if self.zayif_eslesme:
            satirlar.append(
                f"  ZAYIF eşleşme    : {len(self.zayif_eslesme)} "
                f"(unvan-slug tutmadı, satırda tek link vardı): "
                + ", ".join(self.zayif_eslesme[:10])
            )
        if self.slug_bulunamayan:
            satirlar.append(
                f"  SLUG YOK         : {len(self.slug_bulunamayan)} -> "
                + ", ".join(self.slug_bulunamayan[:10])
            )
        if self.domda_olup_rscde_olmayan:
            satirlar.append(
                f"  DOM'da fazla     : {len(self.domda_olup_rscde_olmayan)} -> "
                + ", ".join(self.domda_olup_rscde_olmayan[:10])
            )
        satirlar.append(
            f"  muafiyet         : {self.muaf} muaf / {self.muaf_degil} değil "
            f"/ {len(self.belirsiz)} belirsiz"
        )
        return "\n".join(satirlar)


# --- Ayrıştırma ------------------------------------------------------------


def rsc_kayitlari(html: str) -> list[dict]:
    """Gömülü RSC yükündeki şirket kayıtları.

    Yük bir script string'inin içinde, yani tırnaklar kaçışlı. Önce kaçış
    geri alınır, sonra JSON okunur.
    """
    duz = html.replace('\\"', '"')
    kayitlar = []
    for ham in _KAYIT_RE.findall(duz):
        try:
            kayitlar.append(json.loads(ham))
        except json.JSONDecodeError:
            continue
    return kayitlar


def unvan_slug(unvan: str) -> str:
    """KAP'ın URL slug'ı unvandan türüyor.

    'TÜRK HAVA YOLLARI A.O.' -> 'turk-hava-yollari-a-o'

    `normalize` zaten Türkçe harf tuzağını (noktasız 'ı') hallediyor;
    burada yalnız boşluklar tireye çevrilir.
    """
    return normalize(unvan).replace(" ", "-")


def dom_satirlari(html: str) -> dict[str, list[str]]:
    """ticker -> o satırdaki '{id}-{slug}' adayları.

    Anahtar satırın ticker hücresi; konum indeksi değil. Bir satırda birden
    çok link var (şirket + bağımsız denetim kuruluşu), ayıklama `_slug_sec`de.

    **Bir hücrede birden çok kod olabilir.** Albaraka satırı 'ALBRK ALK'
    yazıyor: aynı tüzel kişinin iki pay kodu. Hücreyi tek ticker sanmak
    45 şirketi (746 kaydın 701 satıra sığmasının sebebi) eşleşmeden düşürür.
    """
    corba = BeautifulSoup(html, "html.parser")
    harita: dict[str, list[str]] = {}
    for tr in corba.find_all("tr"):
        hucreler = tr.find_all("td")
        if not hucreler:
            continue
        kodlar = [
            k for k in hucreler[0].get_text(" ", strip=True).split()
            if _TICKER_RE.match(k)
        ]
        if not kodlar:
            continue
        adaylar = []
        for a in tr.find_all("a", href=True):
            m = _OZET_HREF_RE.search(a["href"])
            if m and m.group(1) not in adaylar:
                adaylar.append(m.group(1))
        for kod in kodlar:
            mevcut = harita.setdefault(kod, [])
            mevcut.extend(a for a in adaylar if a not in mevcut)
    return harita


def _slug_sec(kayit: dict, adaylar: list[str], rapor: EvrenRaporu) -> str | None:
    """Satırdaki adaylardan doğru olanı unvana bakarak seçer.

    Satırda hem şirketin hem bağımsız denetim kuruluşunun linki var.
    "İlkini al" konum varsayımıdır; onun yerine slug'ın unvandan türediği
    gerçeği kullanılır. Tutmazsa ve tek aday varsa alınır ama ZAYIF
    işaretlenir — sessizce kabul edilmez.
    """
    if not adaylar:
        return None
    hedef = unvan_slug(kayit["kapMemberTitle"])
    for aday in adaylar:
        if aday.split("-", 1)[1] == hedef:
            return aday
    denetci_slug = unvan_slug(kayit.get("relatedMemberTitle") or "")
    kalan = [a for a in adaylar if a.split("-", 1)[1] != denetci_slug]
    if len(kalan) == 1:
        rapor.zayif_eslesme.append(kayit["stockCode"])
        return kalan[0]
    return None


def evreni_ayristir(html: str) -> tuple[list[Sirket], EvrenRaporu]:
    """`/tr/bist-sirketler` gövdesi -> şirket listesi + denetim raporu."""
    kayitlar = rsc_kayitlari(html)
    dom = dom_satirlari(html)
    rapor = EvrenRaporu(rsc_kayit=len(kayitlar), dom_ticker=len(dom))

    sirketler = []
    for k in kayitlar:
        # Bir tüzel kişinin birden çok pay kodu olabilir: stockCode alanı
        # 'ALBRK, ALK' gibi virgüllü gelir. Ticker birincil anahtar olduğu
        # için (Spec §1.1) her kod ayrı satır olur; uuid, unvan ve slug
        # ortaktır — aynı şirket tek KAFİF doldurur.
        kodlar = [t.strip() for t in (k.get("stockCode") or "").split(",") if t.strip()]
        if len(kodlar) > 1:
            rapor.coklu_kod.append("+".join(kodlar))
        if not kodlar:
            kodlar = [""]

        muaf = mali_sektor_muaf_mi(k.get("kapMemberTitle") or "")

        for ticker in kodlar:
            slug = _slug_sec(k, dom.get(ticker, []), rapor)
            if slug:
                rapor.eslesen += 1
            else:
                rapor.slug_bulunamayan.append(ticker or "(ticker yok)")

            if muaf is True:
                rapor.muaf += 1
            elif muaf is False:
                rapor.muaf_degil += 1
            else:
                rapor.belirsiz.append(ticker)

            sirketler.append(
                Sirket(
                    ticker=ticker,
                    unvan=k.get("kapMemberTitle") or "",
                    kap_member_uuid=k.get("mkkMemberOid") or "",
                    kap_kfif_slug=slug,
                    sehir=k.get("cityName") or None,
                    denetci=k.get("relatedMemberTitle") or None,
                    mali_sektor_muaf=muaf,
                )
            )

    bilinen = {s.ticker for s in sirketler}
    rapor.domda_olup_rscde_olmayan = sorted(set(dom) - bilinen)
    return sirketler, rapor


def sirketleri_getir(cekici) -> list[Sirket]:
    """Evreni ağdan (veya önbellekten) çeker. Tek istek."""
    sirketler, _ = evreni_ayristir(cekici.getir(BIST_SIRKETLER_URL))
    return sirketler


# --- Kalıcılık -------------------------------------------------------------

BASLIKLAR = [
    "ticker", "unvan", "kap_member_uuid", "kap_kfif_slug",
    "sehir", "denetci", "pazar", "sektor", "mali_sektor_muaf",
]

# CSV'de üç durumlu alan: EVET / HAYIR / boş. Boş = "bilinmiyor", HAYIR değil.
_UCLU = {True: "EVET", False: "HAYIR", None: ""}
_UCLU_TERS = {"EVET": True, "HAYIR": False, "": None}


def _satira_cevir(s: Sirket) -> dict:
    d = asdict(s)
    d["mali_sektor_muaf"] = _UCLU[s.mali_sektor_muaf]
    return {b: ("" if d[b] is None else d[b]) for b in BASLIKLAR}


def yaz(
    sirketler: list[Sirket],
    yol: Path | str = EVREN_CSV,
    *,
    arsivle: bool = True,
) -> Path | None:
    """CSV'ye yazar; varsa önceki sürümü arşive taşır.

    Arşiv adı önceki dosyanın yazıldığı tarihi taşır, bugünün tarihini değil:
    dosya "hangi güne ait evren" sorusuna cevap vermeli. Evrenin değişmesi
    (halka arz, kotasyon iptali) kendi başına bir sinyal.
    """
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)

    arsiv_yolu = None
    if arsivle and yol.exists():
        onceki = date.fromtimestamp(yol.stat().st_mtime)
        ARSIV_DIZINI.mkdir(parents=True, exist_ok=True)
        arsiv_yolu = ARSIV_DIZINI / f"sirketler_{onceki:%Y%m%d}.csv"
        arsiv_yolu.write_bytes(yol.read_bytes())

    # utf-8-sig: Excel'de Türkçe karakterler bozulmasın
    with open(yol, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=BASLIKLAR)
        w.writeheader()
        w.writerows(_satira_cevir(s) for s in sirketler)
    return arsiv_yolu


def oku(yol: Path | str = EVREN_CSV) -> list[Sirket]:
    yol = Path(yol)
    if not yol.exists():
        return []
    with open(yol, newline="", encoding="utf-8-sig") as f:
        return [
            Sirket(
                ticker=r["ticker"],
                unvan=r["unvan"],
                kap_member_uuid=r["kap_member_uuid"],
                kap_kfif_slug=r["kap_kfif_slug"] or None,
                sehir=r["sehir"] or None,
                denetci=r["denetci"] or None,
                pazar=r["pazar"] or None,
                sektor=r["sektor"] or None,
                mali_sektor_muaf=_UCLU_TERS.get(r["mali_sektor_muaf"]),
            )
            for r in csv.DictReader(f)
        ]


def fark(onceki: list[Sirket], yeni: list[Sirket]) -> tuple[list[str], list[str]]:
    """(eklenen, çıkan) ticker listesi. Evren değişimi Faz 5 için olaydır."""
    a = {s.ticker for s in onceki}
    b = {s.ticker for s in yeni}
    return sorted(b - a), sorted(a - b)
