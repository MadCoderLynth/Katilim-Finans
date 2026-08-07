"""`/tr/bist-sirketler` gövdesinden test parçası keser.

Fixture uydurulmuyor, **gerçek gövdeden kesiliyor**: RSC kayıtları kaçış
karakterleriyle birlikte, DOM satırları olduğu gibi kopyalanıyor. Böylece
test, KAP'ın gerçekten ürettiği biçime karşı çalışıyor.

Seçilen şirketler her biri bir test durumunu temsil ediyor:

  THYAO   normal tek kodlu şirket, muaf değil
  ALBRK   'ALBRK, ALK' — tek tüzel kişi, iki pay kodu; banka → muaf
  ISYAT   'İŞ YATIRIM ORTAKLIĞI' — belirsiz (MKYO mu değil mi)
  AKYHO   'AKDENİZ YATIRIM HOLDİNG' — hem 'yatirim' hem 'holding' geçiyor,
          holding istisnası muafiyet kalıbını yenmeli
  AGHOL   RSC'de var ama DOM satırı BİLEREK atlandı → eşleşmeyen kayıt

Yeniden üretmek için önbellekte sayfanın bulunması gerekir:
    python -m katilim.cli evren --yenile
    python tests/fixtures/olustur_evren_parca.py
"""

from __future__ import annotations

import pathlib
import sys

from bs4 import BeautifulSoup

KOK = pathlib.Path(__file__).resolve().parents[2]
ONBELLEK = KOK / "veri" / "onbellek"
CIKTI = pathlib.Path(__file__).parent / "bist_sirketler_parca.html"

# (ticker, DOM satırı da alınsın mı)
SECILENLER = [
    ("THYAO", True),
    ("ALBRK", True),
    ("ISYAT", True),
    ("AKYHO", True),
    ("AGHOL", False),  # eşleşmeyen kayıt testi
]


def _onbellekten_oku() -> str:
    ix = ONBELLEK / "index.tsv"
    if not ix.exists():
        sys.exit("veri/onbellek/index.tsv yok. Önce: python -m katilim.cli evren --yenile")
    for satir in ix.open(encoding="utf-8"):
        ad, url = satir.rstrip("\n").split("\t")
        if url.endswith("/tr/bist-sirketler"):
            return (ONBELLEK / ad).read_text(encoding="utf-8")
    sys.exit("bist-sirketler önbellekte yok. Önce: python -m katilim.cli evren --yenile")


def _ham_kayit(html: str, ticker: str) -> str:
    """RSC kaydını kaçışlarıyla birlikte, olduğu gibi keser."""
    imza = f'\\"stockCode\\":\\"{ticker}'
    i = html.find(imza)
    if i < 0:
        sys.exit(f"{ticker}: RSC kaydı bulunamadı")
    bas = html.rfind('{\\"mkkMemberOid', 0, i)
    son_imza = '\\"}'
    son = html.find(son_imza, html.find('\\"kapMemberType', i)) + len(son_imza)
    return html[bas:son]


def _ham_satir(html: str, ticker: str) -> str:
    corba = BeautifulSoup(html, "html.parser")
    for tr in corba.find_all("tr"):
        hucreler = tr.find_all("td")
        if hucreler and ticker in hucreler[0].get_text(" ", strip=True).split():
            return str(tr)
    sys.exit(f"{ticker}: DOM satırı bulunamadı")


def main() -> int:
    html = _onbellekten_oku()
    kayitlar = [_ham_kayit(html, t) for t, _ in SECILENLER]
    satirlar = [_ham_satir(html, t) for t, dom in SECILENLER if dom]

    # Gerçek sayfadaki sarmalayıcıyla aynı biçim: script string'i içinde
    # kaçışlı JSON. Ayrıştırıcı bu kaçışı geri almak zorunda.
    yuk = ",".join(kayitlar)
    parca = (
        "<html><body>\n"
        '<table><tr><th>Kod</th><th>Şirket Ünvanı</th><th>Şehir</th>'
        "<th>Bağımsız Denetim Kuruluşu</th></tr>\n"
        + "\n".join(satirlar)
        + "\n</table>\n"
        '<script>self.__next_f.push([1,"3:[\\"$\\",\\"$L20\\",null,'
        '{\\"data\\":[{\\"code\\":\\"T\\",\\"content\\":[' + yuk + "]}]}]\\n\"])</script>\n"
        "</body></html>\n"
    )
    CIKTI.write_text(parca, encoding="utf-8")
    print(f"{len(kayitlar)} RSC kaydı, {len(satirlar)} DOM satırı -> {CIKTI}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
