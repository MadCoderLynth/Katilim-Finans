"""KAP KAFİF bildirimi HTML ayrıştırıcısı (Spec §3).

Tasarım kararı: tablolar **konuma veya başlığa göre değil, içerik imzasına
göre** tanınır. 4A tablosu, içinde 'alkollü içki' geçen tablodur. Bu yaklaşım
şablon versiyonları arasında satır sayısı değişse de (2024 revizyonunda
1. bölüm 3 sorudan 2'ye indi) ayakta kalır.

Ayrıştırma başarısını self-check belirler: oranlar tutmuyorsa çıktı
güvenilir değildir (bkz. oranlar.self_check).
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime

from bs4 import BeautifulSoup

from .metin import (
    normalize,
    parse_evet_hayir,
    parse_para_carpani,
    parse_sayi,
    parse_yil_donem,
)
from .model import KafifBildirim, Kalem

# --- İçerik imzaları -------------------------------------------------------
# Bir tabloyu tanımlayan, o tabloya özgü etiket parçası.

TABLO_IMZALARI: list[tuple[str, str]] = [
    ("OZET", "sunum para birimi"),
    ("S1", "standart madde 1 2 de sayilan faaliyetlerden"),
    ("S2", "imtiyazi bulunuyor mu"),
    ("S3", "kamuoyuna yapilmis bir aciklama"),
    ("4A", "alkollu icki"),
    ("4B", "saglig"),  # 'sağlığa zararlı tütün ürünlerinin perakende satışı'
    ("4D", "fiyat farki gelirleri"),
    ("5F", "nakit ve nakit benzerleri"),
    ("5G", "vadesiz mevduat hesaplari"),
    ("5H", "toplam varliklar"),
    ("6I", "kisa vadeli borclanmalar"),
    ("6J", "kiralama islemlerinden borclar"),
    # 4C ve 4E aynı kalemleri paylaşıyor; ayrımı özel kural yapıyor.
    ("4C_VEYA_4E", "ozkaynak yontemiyle degerlenen yatirimlarin"),
]

BEYAN_IMZALARI: dict[str, str] = {
    "b1_1": "faaliyetlerden herhangi birinin yapilabilecegi yaziyor mu",
    "b1_2": "sirketlere ortak olunabilecegi yaziyor mu",
    "b2_1": "kar payi imtiyazi",
    "b2_2": "tasfiye payi imtiyazi",
    "b3_1": "kamuoyuna yapilmis bir aciklama",
    "b3_2": "mahkemelerce alinmis",
    "b4_1": "alkollu icki",
    "b4_2": "domuz mamulleri",
    "b4_3": "tutun mamulleri uretim",
    "b4_4": "kumar",
    "b4_5": "finans sektoru faaliyeti",
    "b4_6": "yayincilik",
    "b4_7": "otel isletmeciligi",
}

OZET_IMZALARI: dict[str, str] = {
    "para": "sunum para birimi",
    "donem": "verilerin ait oldugu finansal tablo",
    "nitelik": "finansal tablo niteligi",
    "gelir_orani": "uygun olmayan gelirlerinin orani",
    "varlik_orani": "uygun olmayan varliklarinin orani",
    "borc_orani": "uygun olmayan borclarinin orani",
}

_KALEM_NO_RE = re.compile(r"^\s*(\d+)\s*\)\s*(.*)$", re.DOTALL)
_TARIH_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s*(\d{2}):(\d{2}):(\d{2})")
_ACIKLAMA_RE = re.compile(r"yukaridaki (\d+) numarali madde icin aciklama")


class AyristirmaHatasi(Exception):
    pass


# --- Yardımcılar -----------------------------------------------------------


def _satirlar(tablo) -> list[list[str]]:
    out = []
    for tr in tablo.find_all("tr"):
        hucreler = [
            c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])
        ]
        if hucreler:
            out.append(hucreler)
    return out


def _tablo_metni(satirlar: list[list[str]]) -> str:
    return normalize(" ".join(h for s in satirlar for h in s))


def _siniflandir(satirlar: list[list[str]]) -> str | None:
    metin = _tablo_metni(satirlar)
    for ad, imza in TABLO_IMZALARI:
        if imza in metin:
            if ad == "4C_VEYA_4E":
                # 4E tablosunda 1. kalem yalnızca 'Hasılat'tır; 4C'de yoktur.
                etiketler = {normalize(_kalem_adi(s[0])) for s in satirlar if s}
                return "4E" if "hasilat" in etiketler else "4C"
            return ad
    return None


def _kalem_adi(ham: str) -> str:
    m = _KALEM_NO_RE.match(ham or "")
    return m.group(2).strip() if m else (ham or "").strip()


def _kalem_no(ham: str) -> int | None:
    m = _KALEM_NO_RE.match(ham or "")
    return int(m.group(1)) if m else None


def _tutar_satirlari(satirlar: list[list[str]], tablo_adi: str) -> list[Kalem]:
    """Tutar tablosundan kalemleri çıkarır.

    Atlanan satırlar: etiketi boş olan başlık satırları (para birimi / dönem /
    nitelik tekrarları) ve TOPLAM satırı. Toplamı formdan okumuyoruz, kendimiz
    hesaplıyoruz; böylece formun toplam satırı da dolaylı doğrulanıyor.
    """
    kalemler: list[Kalem] = []
    for s in satirlar:
        if len(s) < 2:
            continue
        etiket_ham, tutar_ham = s[0], s[-1]
        etiket_n = normalize(etiket_ham)
        if not etiket_n or etiket_n == "toplam":
            continue
        if etiket_n in ("kalem adi", "tutar"):
            continue
        tutar = parse_sayi(tutar_ham)
        if tutar is None:
            continue
        kalemler.append(
            Kalem(
                tablo=tablo_adi,
                kalem_no=_kalem_no(etiket_ham),
                kalem_adi=_kalem_adi(etiket_ham),
                tutar_ham=tutar,
            )
        )
    return kalemler


def _beyan_satirlari(satirlar: list[list[str]]) -> dict[str, bool | None]:
    """Beyan tablosundan evet/hayır bayraklarını çıkarır."""
    bulunan: dict[str, bool | None] = {}
    for s in satirlar:
        if len(s) < 2:
            continue
        etiket_n = normalize(s[0])
        if not etiket_n:
            continue
        deger = None
        for hucre in s[1:]:
            deger = parse_evet_hayir(hucre)
            if deger is not None:
                break
        if deger is None:
            continue
        for anahtar, imza in BEYAN_IMZALARI.items():
            if imza in etiket_n:
                bulunan[anahtar] = deger
                break
    return bulunan


# --- Ana giriş noktası -----------------------------------------------------


def ayristir(
    html: str,
    *,
    bildirim_id: int | None = None,
    ticker: str | None = None,
) -> KafifBildirim:
    corba = BeautifulSoup(html, "html.parser")
    b = KafifBildirim(bildirim_id=bildirim_id, ticker=ticker)
    b.raw_sha256 = hashlib.sha256(html.encode("utf-8", "ignore")).hexdigest()

    gorulen_tablolar: list[str] = []

    for tablo in corba.find_all("table"):
        satirlar = _satirlar(tablo)
        if not satirlar:
            continue

        # 'Yukarıdaki N numaralı madde için açıklama' tabloları
        m = _ACIKLAMA_RE.search(_tablo_metni(satirlar))
        if m:
            for s in satirlar:
                if len(s) >= 2 and _ACIKLAMA_RE.search(normalize(s[0])):
                    b.aciklamalar[f"madde_{m.group(1)}"] = s[-1].strip()
            continue

        ad = _siniflandir(satirlar)
        if ad is None:
            continue
        gorulen_tablolar.append(ad)

        if ad == "OZET":
            _ozet_isle(b, satirlar)
        elif ad in ("S1", "S2", "S3", "4A"):
            b.beyanlar.update(_beyan_satirlari(satirlar))
        else:
            b.kalemler.extend(_tutar_satirlari(satirlar, ad))

    # 4A dışındaki bölümlerde de bayrak geçebilir; eksikleri None bırak
    for anahtar in BEYAN_IMZALARI:
        b.beyanlar.setdefault(anahtar, None)

    b.sablon_imzasi = "|".join(sorted(set(gorulen_tablolar)))

    # Gönderim tarihi sayfa gövdesinden
    tam_metin = corba.get_text(" ", strip=True)
    mt = _TARIH_RE.search(tam_metin)
    if mt:
        g, ay, yil, sa, dk, sn = (int(x) for x in mt.groups())
        b.gonderim_ts = datetime(yil, ay, g, sa, dk, sn)

    b.is_duzeltme = "duzeltme" in normalize(tam_metin[:4000])

    if not b.kalemler:
        raise AyristirmaHatasi(
            "Hiçbir tutar tablosu tanınamadı. HTML yapısı beklenenden farklı; "
            "tanı için: python -m katilim.cli dok <dosya.html>"
        )
    return b


def _ozet_isle(b: KafifBildirim, satirlar: list[list[str]]) -> None:
    for s in satirlar:
        if len(s) < 2:
            continue
        etiket_n = normalize(s[0])
        deger = s[-1].strip()
        if not etiket_n or not deger:
            continue
        if OZET_IMZALARI["para"] in etiket_n:
            b.para_birimi_carpani = parse_para_carpani(deger)
        elif OZET_IMZALARI["donem"] in etiket_n:
            b.yil, b.periyot = parse_yil_donem(deger)
        elif OZET_IMZALARI["nitelik"] in etiket_n:
            b.finansal_tablo_niteligi = deger
        elif OZET_IMZALARI["gelir_orani"] in etiket_n:
            b.ozet_gelir_orani = parse_sayi(deger)
        elif OZET_IMZALARI["varlik_orani"] in etiket_n:
            b.ozet_varlik_orani = parse_sayi(deger)
        elif OZET_IMZALARI["borc_orani"] in etiket_n:
            b.ozet_borc_orani = parse_sayi(deger)


def dok(html: str) -> str:
    """Tanı modu: tüm tabloları imzalarıyla birlikte döker.

    Ayrıştırma tutmadığında bu çıktıyı paylaşın; imza haritası ona göre
    güncellenir.
    """
    corba = BeautifulSoup(html, "html.parser")
    parcalar = []
    for i, tablo in enumerate(corba.find_all("table")):
        satirlar = _satirlar(tablo)
        if not satirlar:
            continue
        ad = _siniflandir(satirlar) or "?TANINMADI"
        parcalar.append(f"\n=== tablo #{i}  ->  {ad}  ({len(satirlar)} satır)")
        for s in satirlar[:25]:
            parcalar.append("    " + " | ".join(h[:70] for h in s))
    return "\n".join(parcalar) or "(hiç tablo bulunamadı)"
