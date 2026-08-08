"""Form indirme/arşivleme testleri — ağa çıkmaz (Faz 1.4a).

Bu modül ayrıştırmadığı için burada parser yok; test edilen şey **arşiv
disiplini**: idempotanlık, dosya adlandırma, hata sınıflaması ve KAFİF'i
olmayan şirketin sessizce atlanmaması.
"""
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from katilim import toplayici  # noqa: E402
from katilim.cekici import ÇekimHatası  # noqa: E402
from katilim.evren import Sirket  # noqa: E402


class SahteOnbellek:
    def __init__(self, negatifler=None):
        self._n = negatifler or {}

    def negatif_durum(self, url):
        return self._n.get(url)


class SahteCekici:
    """Ağ yerine sözlükten servis eder; hangi URL'in istendiğini sayar."""

    def __init__(self, harita, negatifler=None):
        self.harita = harita
        self.istekler = []
        self.onbellek = SahteOnbellek(negatifler)
        self.istatistik = {"onbellek": 0, "ag": 0, "yeniden_deneme": 0, "negatif": 0}

    def getir(self, url, *, zorla=False, onbellekle=True):
        self.istekler.append((url, onbellekle))
        if url not in self.harita:
            raise ÇekimHatası(f"HTTP 404: {url}")
        self.istatistik["ag"] += 1
        return self.harita[url]


def _satir(ticker, bid, yil=2025, periyot="Yıllık", ts="2026-03-04 18:57:54"):
    return {
        "ticker": ticker,
        "bildirim_id": bid,
        "yil": yil,
        "periyot": periyot,
        "gonderim_ts": datetime.strptime(ts, "%Y-%m-%d %H:%M:%S"),
        "konu": "Katılım Finansı İlkeleri Bilgi Formu",
        "indirildi_mi": False,
    }


def _url(bid):
    return toplayici.BILDIRIM_URL.format(bildirim_id=bid)


# --- dosya adlandırma ------------------------------------------------------


def test_dosya_adi_turkce_donemi_slugluyor():
    assert toplayici.dosya_adi("THYAO", 2025, "6 Aylık", 1472632) == \
        "THYAO_2025_6_aylik_1472632.html"
    assert toplayici.dosya_adi("ASELS", 2025, "Yıllık", 1561061) == \
        "ASELS_2025_yillik_1561061.html"


def test_dosya_adi_eksik_alanlarla_da_kimlik_tasiyor():
    ad = toplayici.dosya_adi("XYZ", None, None, 42)
    assert ad.endswith("_42.html"), ad


def test_mevcut_arsiv_kimligi_dosya_adindan_okuyor():
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d)
        (p / "THYAO_2025_yillik_1566002.html").write_text("x", encoding="utf-8")
        (p / "THYAO_2025_yillik.html").write_text("x", encoding="utf-8")  # Faz 0 fixture
        (p / "not_a_form.txt").write_text("x", encoding="utf-8")
        bulunan = toplayici.mevcut_arsiv(p)
    assert set(bulunan) == {1566002}, bulunan


# --- indirme döngüsü -------------------------------------------------------


def test_form_indirilip_arsive_yaziliyor():
    with tempfile.TemporaryDirectory() as d:
        c = SahteCekici({_url(1): "<html>form</html>"})
        ind = toplayici.formlari_indir([_satir("THYAO", 1)], c, ham_dizini=d)
        k = ind.kayitlar[0]
        assert k.durum == toplayici.DURUM_INDIRILDI
        yol = pathlib.Path(d) / k.dosya
        assert yol.read_text(encoding="utf-8") == "<html>form</html>"
        assert k.bayt == len("<html>form</html>")
        assert len(k.sha256) == 64


def test_onbellege_yazilmiyor():
    """Arşiv veri/ham'da; aynı 240 MB'ı URL önbelleğinde de tutmuyoruz."""
    with tempfile.TemporaryDirectory() as d:
        c = SahteCekici({_url(1): "<html>x</html>"})
        toplayici.formlari_indir([_satir("A", 1)], c, ham_dizini=d)
        assert c.istekler == [(_url(1), False)], c.istekler


def test_idempotanlik_bildirim_id_uzerinden():
    """Diskte kimliği olan dosya varsa ağa ÇIKILMAZ — sha ile değil, id ile."""
    with tempfile.TemporaryDirectory() as d:
        c = SahteCekici({_url(1): "<html>form</html>"})
        toplayici.formlari_indir([_satir("THYAO", 1)], c, ham_dizini=d)
        assert len(c.istekler) == 1
        # ikinci koşu: aynı kimlik, gövde DEĞİŞMİŞ olsa bile ağa çıkma
        c2 = SahteCekici({_url(1): "<html>BASKA GOVDE</html>"})
        ind = toplayici.formlari_indir([_satir("THYAO", 1)], c2, ham_dizini=d)
        assert c2.istekler == [], "kimlik diskteyken yeniden çekilmemeli"
        assert ind.kayitlar[0].durum == toplayici.DURUM_ZATEN_VARDI


def test_coklu_kodlu_bildirim_tek_kez_iniyor():
    """Aynı bildirim iki pay kodunda görünür; indirme bir kezdir."""
    with tempfile.TemporaryDirectory() as d:
        c = SahteCekici({_url(500): "<html>x</html>"})
        ind = toplayici.formlari_indir(
            [_satir("ALBRK", 500), _satir("ALK", 500)], c, ham_dizini=d
        )
        assert len(c.istekler) == 1
        assert len(ind.kayitlar) == 1
        k = ind.kayitlar[0]
        assert k.tickerlar == ["ALBRK", "ALK"]
        assert k.ticker == "ALBRK", "birincil kod deterministik olmalı"


def test_404_ile_gecici_hata_ayri_siniflaniyor():
    """Kalıcı yokluk ile geçici arıza aynı şey değil (kural 7'nin kardeşi)."""
    with tempfile.TemporaryDirectory() as d:
        c = SahteCekici({}, negatifler={_url(1): (404, "2026-08-08")})
        ind = toplayici.formlari_indir([_satir("A", 1), _satir("B", 2)], c, ham_dizini=d)
        durumlar = {k.bildirim_id: k.durum for k in ind.kayitlar}
        assert durumlar[1] == toplayici.DURUM_YOK, "404 -> YOK"
        assert durumlar[2] == toplayici.DURUM_HATA, "negatif kaydı olmayan -> HATA"
        assert len(ind.uyarilar) == 2


def test_pencere_disi_isaretleniyor():
    """Hipotezin test kümesi: bugün sorguda GÖRÜNMEYECEK kimlikler."""
    simdi = datetime(2026, 8, 8, 12, 0, 0)
    eski = (simdi - timedelta(days=400)).strftime("%Y-%m-%d %H:%M:%S")
    yeni = (simdi - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    with tempfile.TemporaryDirectory() as d:
        c = SahteCekici({_url(1): "<html>a</html>", _url(2): "<html>b</html>"})
        ind = toplayici.formlari_indir(
            [_satir("A", 1, ts=eski), _satir("B", 2, ts=yeni)],
            c, ham_dizini=d, simdi=simdi,
        )
        disi = {k.bildirim_id: k.pencere_disi for k in ind.kayitlar}
    assert disi == {1: True, 2: False}, disi


def test_kontrol_noktasi_her_n_agda_bir_cagriliyor():
    """Uzun koşu kesilirse iş kaybolmasın."""
    with tempfile.TemporaryDirectory() as d:
        c = SahteCekici({_url(i): "<html>x</html>" for i in range(1, 7)})
        cagri = []
        toplayici.formlari_indir(
            [_satir("A", i) for i in range(1, 7)], c, ham_dizini=d,
            kontrol_noktasi=lambda ind: cagri.append(len(ind.kayitlar)),
            kontrol_araligi=2,
        )
        assert cagri == [2, 4, 6], cagri


# --- beyan durumu ----------------------------------------------------------


def _sirket(ticker, muaf):
    return Sirket(ticker=ticker, unvan=f"{ticker} A.Ş.", kap_member_uuid="u",
                  kap_kfif_slug=None, mali_sektor_muaf=muaf)


def test_beyan_yok_ile_ayirt_edilemedi_ayri():
    sirketler = [
        _sirket("AAA", False),   # muaf değil, beyanı yok -> BEYAN_YOK
        _sirket("BBB", None),    # muafiyeti belirsiz, beyanı yok -> AYIRT_EDILEMEDI
        _sirket("CCC", True),    # muaf -> KAPSAM_DISI
        _sirket("DDD", False),   # KAFİF var -> BEYAN_VAR
    ]
    durumlar = [
        {"ticker": "AAA", "durum": "KAFIF_YOK", "kafif_sayisi": "0", "unvan": ""},
        {"ticker": "BBB", "durum": "BOS_SONUC", "kafif_sayisi": "0", "unvan": ""},
        {"ticker": "CCC", "durum": "MUAF_SORGULANMADI", "kafif_sayisi": "0", "unvan": ""},
        {"ticker": "DDD", "durum": "KAFIF_VAR", "kafif_sayisi": "2", "unvan": ""},
    ]
    d = {r["ticker"]: r["durum"] for r in toplayici.beyan_durumlari(sirketler, durumlar)}
    assert d == {
        "AAA": toplayici.BEYAN_YOK,
        "BBB": toplayici.AYIRT_EDILEMEDI,
        "CCC": toplayici.KAPSAM_DISI,
        "DDD": toplayici.BEYAN_VAR,
    }, d


def test_beyan_durumu_coklu_kodu_aciyor():
    sirketler = [_sirket("ALBRK", False), _sirket("ALK", False)]
    durumlar = [{"ticker": "ALBRK/ALK", "durum": "KAFIF_VAR", "kafif_sayisi": "2",
                 "unvan": "ALBARAKA"}]
    r = toplayici.beyan_durumlari(sirketler, durumlar)
    assert [x["ticker"] for x in r] == ["ALBRK", "ALK"]
    assert all(x["durum"] == toplayici.BEYAN_VAR for x in r)


def test_indeks_csv_yaziliyor():
    with tempfile.TemporaryDirectory() as d:
        c = SahteCekici({_url(1): "<html>x</html>"})
        ind = toplayici.formlari_indir([_satir("THYAO", 1)], c, ham_dizini=d)
        yol = toplayici.indeksi_yaz(ind, pathlib.Path(d) / "indeks.csv")
        metin = yol.read_text(encoding="utf-8-sig")
    assert "bildirim_id" in metin and "1" in metin and "sha256" in metin


if __name__ == "__main__":
    import traceback

    t = [(a, f) for a, f in sorted(globals().items()) if a.startswith("test_")]
    kotu = 0
    for a, f in t:
        try:
            f()
            print(f"  ok    {a}")
        except Exception:
            kotu += 1
            print(f"  HATA  {a}\n{traceback.format_exc()}")
    print(f"\n{len(t)-kotu}/{len(t)} test geçti")
    raise SystemExit(1 if kotu else 0)
