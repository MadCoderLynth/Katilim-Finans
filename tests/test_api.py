"""`katilim.api` ve portal testleri — ağa çıkmaz (Faz 5.3).

Bu dosyanın asıl konusu **üç tuzak**. Hepsi belgeli ve hepsi sessiz veri
yanlış okumasına açık:

1. **KARANTİNA** — self-check'ten geçmemiş kayıt panelde duruyor; bayrağı
   yok sayan tüketici doğrulanmamış kararı sessizce alır.
2. **MUAF ≠ ELENMİŞ** — `KAPSAM_DISI` "uygun değil" DEĞİLDİR.
3. **GÖRÜŞ YOK ≠ UYGUN DEĞİL** — `None` dönmek ya da `UYGUN_DEGIL`'e
   düşmek, görüşü olmayan kaydı görüş gibi gösterir.

Portal testi **sunucu ayağa kaldırılmadan**, fonksiyon düzeyinde koşar.
"""
import csv
import pathlib
import sys
import tempfile
import traceback
from datetime import date, datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from katilim import api as A  # noqa: E402
from katilim import portal as P  # noqa: E402

KOK = pathlib.Path(__file__).resolve().parents[1]

PANEL_BASLIK = ["ticker", "yil", "periyot", "gecerlilik_baslangic", "karar",
                "red_kodlari", "gelir_orani", "varlik_orani", "borc_orani",
                "onceki_donem_tolerans", "sablon_versiyon", "self_check",
                "bildirim_id", "zincir_notu", "duzeltme_izi", "gecerli_kayit"]
EVREN_BASLIK = ["ticker", "unvan", "kap_member_uuid", "kap_kfif_slug",
                "sehir", "denetci", "pazar", "sektor", "mali_sektor_muaf"]
BEYAN_BASLIK = ["ticker", "unvan", "durum", "kafif_sayisi", "sorgu_durumu",
                "mali_sektor_muaf"]
ENDEKS_BASLIK = ["ticker", "endeks_adi", "olcum_tarihi"]
DONEM_BASLIK = ["donem_baslangic", "donem_bitis", "duyuru_tarihi",
                "uye_sayisi", "giren_sayisi", "cikan_sayisi", "kaynak_dosya"]


def _yaz(yol, basliklar, satirlar):
    with open(yol, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=basliklar)
        w.writeheader()
        for r in satirlar:
            w.writerow({k: r.get(k, "") for k in basliklar})


def _p(ticker, karar, ts, *, yil="2025", periyot="6 Aylık", kodlar="",
       self_check="GECTI", gecerli="EVET", bid="1", duzeltme=""):
    return {"ticker": ticker, "karar": karar, "gecerlilik_baslangic": ts,
            "yil": yil, "periyot": periyot, "red_kodlari": kodlar,
            "self_check": self_check, "gecerli_kayit": gecerli,
            "bildirim_id": bid, "duzeltme_izi": duzeltme,
            "gelir_orani": "1.0", "varlik_orani": "2.0", "borc_orani": "3.0",
            "onceki_donem_tolerans": "HAYIR"}


class _Ortam:
    """api'nin dosya yollarını geçici dizine çevirir ve önbelleği temizler."""

    def __init__(self, panel, evren, beyan, endeks=(), donem=None):
        self.panel, self.evren, self.beyan = panel, evren, beyan
        self.endeks, self.donem = endeks, donem

    def __enter__(self):
        self._t = tempfile.TemporaryDirectory()
        d = pathlib.Path(self._t.name)
        _yaz(d / "panel.csv", PANEL_BASLIK, self.panel)
        _yaz(d / "evren.csv", EVREN_BASLIK, self.evren)
        _yaz(d / "beyan.csv", BEYAN_BASLIK, self.beyan)
        _yaz(d / "endeks.csv", ENDEKS_BASLIK, self.endeks)
        _yaz(d / "donem.csv", DONEM_BASLIK, self.donem or [
            {"donem_baslangic": "2025-05-01", "donem_bitis": "2025-09-30",
             "duyuru_tarihi": "2025-04-25", "uye_sayisi": "241",
             "giren_sayisi": "21", "cikan_sayisi": "36", "kaynak_dosya": "a.pdf"},
            {"donem_baslangic": "2025-10-01", "donem_bitis": "2026-04-30",
             "duyuru_tarihi": "2025-09-24", "uye_sayisi": "235",
             "giren_sayisi": "23", "cikan_sayisi": "29", "kaynak_dosya": "b.pdf"},
        ])
        self._eski = {k: getattr(A, k) for k in
                      ("PANEL_CSV", "EVREN_CSV", "BEYAN_CSV", "ENDEKS_CSV",
                       "DONEM_CSV", "BILESEN_CSV", "DUZELTME_CSV")}
        A.PANEL_CSV = d / "panel.csv"
        A.EVREN_CSV = d / "evren.csv"
        A.BEYAN_CSV = d / "beyan.csv"
        A.ENDEKS_CSV = d / "endeks.csv"
        A.DONEM_CSV = d / "donem.csv"
        A.BILESEN_CSV = d / "yok_bilesen.csv"
        A.DUZELTME_CSV = d / "yok_duzeltme.csv"
        A.onbellegi_temizle()
        return d

    def __exit__(self, *a):
        for k, v in self._eski.items():
            setattr(A, k, v)
        A.onbellegi_temizle()
        self._t.cleanup()
        return False


_EVREN = [{"ticker": "AAA", "unvan": "AAA A.Ş.", "pazar": "YILDIZ PAZAR",
           "sektor": "İMALAT", "mali_sektor_muaf": "HAYIR"},
          {"ticker": "MUAFCO", "unvan": "Muaf Bank A.Ş.", "pazar": "YILDIZ PAZAR",
           "sektor": "MALİ KURULUŞLAR", "mali_sektor_muaf": "EVET"},
          {"ticker": "BEYANSIZ", "unvan": "Beyansız A.Ş.", "pazar": "ANA PAZAR",
           "sektor": "İMALAT", "mali_sektor_muaf": "HAYIR"}]
_BEYAN = [{"ticker": "AAA", "durum": "BEYAN_VAR"},
          {"ticker": "MUAFCO", "durum": "KAPSAM_DISI"},
          {"ticker": "BEYANSIZ", "durum": "BEYAN_YOK"}]


# ===========================================================================
# LOOK-AHEAD
# ===========================================================================


def test_look_ahead_dunku_tarih_dunku_karari_veriyor():
    """`gecerlilik_baslangic <= tarih` olan EN GEÇ kayıt; sonrası görünmez."""
    with _Ortam([_p("AAA", "UYGUN", "2025-08-10 18:00:00", bid="1"),
                 _p("AAA", "UYGUN_DEGIL", "2025-09-20 18:00:00", bid="2",
                    yil="2025", periyot="Yıllık")], _EVREN, _BEYAN):
        d = A.uygunluk_durumu("AAA", date(2025, 9, 1))
        assert d.karar == "UYGUN" and d.bildirim_id == "1", d
        assert d.uygun is True
        sonra = A.uygunluk_durumu("AAA", date(2025, 10, 1))
        assert sonra.karar == "UYGUN_DEGIL" and sonra.bildirim_id == "2"


def test_look_ahead_gecersiz_kilinan_kayit_kendi_penceresinde_gecerli():
    """`gecerli_kayit` süzgeci UYGULANMAZ — o kayıt o gün canlıydı."""
    with _Ortam([_p("AAA", "UYGUN_DEGIL", "2025-08-10 18:00:00", bid="1",
                    gecerli="HAYIR"),
                 _p("AAA", "UYGUN", "2025-09-05 18:00:00", bid="2",
                    duzeltme="DUZENLENEN")], _EVREN, _BEYAN):
        assert A.uygunluk_durumu("AAA", date(2025, 8, 20)).karar == "UYGUN_DEGIL"
        assert A.uygunluk_durumu("AAA", date(2025, 9, 10)).karar == "UYGUN"


def test_panel_baslangicindan_once_gorus_yok():
    """TUZAK 3'ün dördüncü hâli: tarih panelin başlangıcından önce."""
    with _Ortam([_p("AAA", "UYGUN", "2025-08-10 18:00:00")], _EVREN, _BEYAN):
        d = A.uygunluk_durumu("AAA", date(2024, 1, 1))
        assert d.karar == A.GORUS_YOK
        assert d.uygun is None and d.gorus_var is False
        assert "panel" in d.sebep


# ===========================================================================
# TUZAK 1 — KARANTİNA
# ===========================================================================


def test_karantinali_kayit_varsayilan_olarak_disarida():
    with _Ortam([_p("AAA", "UYGUN_DEGIL", "2025-08-10 18:00:00", bid="1"),
                 _p("AAA", "UYGUN", "2025-09-05 18:00:00", bid="2",
                    self_check="KALDI")], _EVREN, _BEYAN):
        d = A.uygunluk_durumu("AAA", date(2025, 9, 30))
        assert d.bildirim_id == "1", "karantinalı kayıt sessizce kullanıldı"
        assert d.karantinali is False
        ham = A.uygunluk_durumu("AAA", date(2025, 9, 30), karantinali=True)
        assert ham.bildirim_id == "2" and ham.karantinali is True


def test_karantina_bayragi_her_zaman_dogruyu_soyluyor():
    """Tek kayıt karantinalıysa gizlenmez — bayrakla döner."""
    with _Ortam([_p("AAA", "UYGUN", "2025-08-10 18:00:00", self_check="KALDI")],
                _EVREN, _BEYAN):
        d = A.uygunluk_durumu("AAA", date(2025, 9, 1))
        assert d.karantinali is True
        assert "DOĞRULANMAMIŞ" in d.sebep


# ===========================================================================
# TUZAK 2 — MUAF ≠ ELENMİŞ
# ===========================================================================


def test_kapsam_disi_ayri_temsil_ediliyor():
    """ALBRK/KTLEV örüntüsü: KAFİF vermiyor ama XKTUM'da olabilir."""
    with _Ortam([_p("AAA", "UYGUN", "2025-08-10 18:00:00")], _EVREN, _BEYAN):
        d = A.uygunluk_durumu("MUAFCO", date(2025, 9, 1))
    assert d.karar == A.KAPSAM_DISI
    assert d.kapsam_disi is True
    assert d.uygun is None, "kapsam dışı UYGUN_DEGIL'e düşmemeli"
    assert d.gorus_var is False
    assert "DEĞİLDİR" in d.sebep


def test_kapsam_disi_uygun_degil_ile_karistirilamaz():
    with _Ortam([_p("AAA", "UYGUN_DEGIL", "2025-08-10 18:00:00")],
                _EVREN, _BEYAN):
        elenen = A.uygunluk_durumu("AAA", date(2025, 9, 1))
        muaf = A.uygunluk_durumu("MUAFCO", date(2025, 9, 1))
    assert elenen.uygun is False and elenen.gorus_var is True
    assert muaf.uygun is None and muaf.gorus_var is False
    assert elenen.karar != muaf.karar


# ===========================================================================
# TUZAK 3 — GÖRÜŞ YOK ≠ UYGUN DEĞİL
# ===========================================================================


def test_uc_gorus_yok_durumu():
    """BEYAN_YOK · BELIRSIZ · panelde kayıt yok — üçü de GORUS_YOK."""
    with _Ortam([_p("AAA", "BELIRSIZ", "2025-08-10 18:00:00")], _EVREN, _BEYAN):
        beyansiz = A.uygunluk_durumu("BEYANSIZ", date(2025, 9, 1))
        belirsiz = A.uygunluk_durumu("AAA", date(2025, 9, 1))
    for d in (beyansiz, belirsiz):
        assert d.karar == A.GORUS_YOK, d
        assert d.uygun is None, "None dönmeli — UYGUN_DEGIL'e düşmemeli"
        assert d.gorus_var is False
        assert d.kapsam_disi is False, "görüş yok, kapsam dışı DEĞİL"


def test_gorus_yok_none_donmuyor_nesne_donuyor():
    """`None` dönmek çağıranı 'if not durum' tuzağına düşürürdü."""
    with _Ortam([_p("AAA", "UYGUN", "2025-08-10 18:00:00")], _EVREN, _BEYAN):
        d = A.uygunluk_durumu("BEYANSIZ", date(2025, 9, 1))
    assert isinstance(d, A.Durum) and d.sebep


def test_bilinmeyen_ticker_hata_firlatiyor():
    """'Evrende yok' ile 'kaydı yok' ayrı (kural 7)."""
    with _Ortam([_p("AAA", "UYGUN", "2025-08-10 18:00:00")], _EVREN, _BEYAN):
        try:
            A.uygunluk_durumu("YOKBOYLE")
        except A.BilinmeyenTicker:
            return
    raise AssertionError("bilinmeyen ticker sessizce GORUS_YOK döndü")


# ===========================================================================
# hisse_karti
# ===========================================================================


_BEKLENEN_ALANLAR = {"ticker", "unvan", "pazar", "sektor", "muafiyet",
                     "beyan_durumu", "tarih", "durum", "endeksler",
                     "xktum_gecmisi", "karar_gecmisi", "olaylar",
                     "duzeltmeler", "uyarilar"}


def test_hisse_karti_alanlari():
    with _Ortam([_p("AAA", "UYGUN", "2025-08-10 18:00:00"),
                 _p("AAA", "UYGUN_DEGIL", "2026-03-04 18:00:00",
                    yil="2025", periyot="Yıllık", kodlar="G5_GELIR", bid="2")],
                _EVREN, _BEYAN,
                endeks=[{"ticker": "AAA", "endeks_adi": "BIST KATILIM TUM",
                         "olcum_tarihi": "2026-08-08"}]):
        k = A.hisse_karti("AAA", date(2026, 6, 1))
    assert set(k) == _BEKLENEN_ALANLAR, set(k) ^ _BEKLENEN_ALANLAR
    assert k["unvan"] == "AAA A.Ş."
    assert k["durum"].karar == "UYGUN_DEGIL"
    assert "BIST KATILIM TUM" in k["endeksler"]
    assert len(k["karar_gecmisi"]) == 2
    assert [o.olay_tipi for o in k["olaylar"]] == ["UYGUNLUK_KAYBI"]


def test_hisse_karti_bilinmeyen_ticker():
    with _Ortam([_p("AAA", "UYGUN", "2025-08-10 18:00:00")], _EVREN, _BEYAN):
        try:
            A.hisse_karti("YOKBOYLE")
        except A.BilinmeyenTicker as e:
            assert "evrende yok" in str(e)
            return
    raise AssertionError("bilinmeyen ticker için hata fırlatılmadı")


def test_karar_gecmisi_gecersiz_kayitlari_da_tasiyor():
    """Düzeltmeyle geçersiz kılınan satır SİLİNMEZ, işaretlenir."""
    with _Ortam([_p("AAA", "UYGUN", "2025-08-10 18:00:00", gecerli="HAYIR"),
                 _p("AAA", "UYGUN_DEGIL", "2025-09-05 18:00:00", bid="2",
                    duzeltme="DUZENLENEN")], _EVREN, _BEYAN):
        g = A.karar_gecmisi("AAA")
    assert len(g) == 2
    assert [r["gecerli_kayit"] for r in g] == [False, True]


def test_uyarilar_karantina_ve_gorus_yok_gorunur():
    with _Ortam([_p("AAA", "UYGUN", "2025-08-10 18:00:00", self_check="KALDI")],
                _EVREN, _BEYAN):
        k = A.hisse_karti("AAA", date(2025, 9, 1))
        assert any("KARANTİNA" in u for u in k["uyarilar"]), k["uyarilar"]
        k2 = A.hisse_karti("BEYANSIZ", date(2025, 9, 1))
        assert any("GÖRÜŞ YOK" in u for u in k2["uyarilar"]), k2["uyarilar"]


# ===========================================================================
# PORTAL — sunucu ayağa kaldırılmadan
# ===========================================================================


def test_portal_kart_html_uretiyor():
    with _Ortam([_p("AAA", "UYGUN", "2025-08-10 18:00:00"),
                 _p("AAA", "UYGUN_DEGIL", "2026-03-04 18:00:00", bid="2",
                    yil="2025", periyot="Yıllık", kodlar="G5_GELIR")],
                _EVREN, _BEYAN):
        h = P.kart_html(A.hisse_karti("AAA", date(2026, 6, 1)))
    for imza in ("AAA A.Ş.", "UYGUN_DEGIL", "G5_GELIR", "Karar geçmişi",
                 "Olaylar", "Düzeltmeler"):
        assert imza in h, imza
    assert 'class="karar degil"' in h, "UYGUN_DEGIL kırmızı sınıfı almadı"


def test_portal_gecersiz_satir_soluk_isaretleniyor():
    with _Ortam([_p("AAA", "UYGUN", "2025-08-10 18:00:00", gecerli="HAYIR"),
                 _p("AAA", "UYGUN", "2025-09-05 18:00:00", bid="2",
                    duzeltme="DUZENLENEN")], _EVREN, _BEYAN):
        h = P.kart_html(A.hisse_karti("AAA", date(2025, 10, 1)))
    assert 'class="gecersiz"' in h
    assert "geçersiz kılındı" in h and "✔ geçerli" in h


def test_portal_bilinmeyen_ticker_bos_sayfa_donmuyor():
    with _Ortam([_p("AAA", "UYGUN", "2025-08-10 18:00:00")], _EVREN, _BEYAN):
        h = P.sayfa_html("YOKBOYLE")
    assert "evrende yok" in h
    assert "<form" in h, "arama kutusu kayboldu"


def test_portal_bakim_bolumu_butce_ve_onay_tasiyor():
    h = P.sayfa_html(None)
    assert 'class="bakim"' in h, "bakım bölümü görsel olarak ayrılmamış"
    for imza in ("Bildirimleri tara", "Formları indir", "son koşu",
                 "bütçe", "Emin misiniz"):
        assert imza in h, imza
    # Bütçe kod içinden büyütülmez: CLI varsayılanıyla aynı sabit.
    assert "--butce" in str(P.BAKIM["bildirimler"]["komut"])
    assert P.BAKIM["bildirimler"]["komut"][-1] == "800"
    assert P.BAKIM["indir"]["komut"][-1] == "2600"


def test_portal_yalniz_yerel_adrese_bagli():
    assert P.ADRES == "127.0.0.1"


def test_portal_cdn_ve_cerceve_kullanmiyor():
    h = P.sayfa_html(None)
    assert "http://" not in h.replace("http://127.0.0.1", "")
    assert "https://" not in h
    assert h.count("<style>") == 1


def test_portal_html_kacisi_yapiyor():
    kotu = [{"ticker": "XSS", "unvan": "<script>alert(1)</script>",
             "pazar": "ANA PAZAR", "sektor": "İMALAT",
             "mali_sektor_muaf": "HAYIR"}]
    with _Ortam([_p("XSS", "UYGUN", "2025-08-10 18:00:00")], kotu,
                [{"ticker": "XSS", "durum": "BEYAN_VAR"}]):
        h = P.kart_html(A.hisse_karti("XSS", date(2025, 9, 1)))
    assert "<script>alert" not in h
    assert "&lt;script&gt;" in h


# ===========================================================================
# Gerçek veri kademesi
# ===========================================================================


def test_gercek_veriyle_kart_uretiliyor():
    if not (KOK / "veri" / "panel" / "panel.csv").exists():
        print("    ATLANDI: panel yok")
        return
    A.onbellegi_temizle()
    k = A.hisse_karti("THYAO")
    assert k["durum"].karar == "UYGUN_DEGIL"
    assert "G4_DOGRUDAN_AYKIRI" in k["durum"].red_kodlari
    assert len(k["karar_gecmisi"]) >= 3
    h = P.kart_html(k)
    assert "TÜRK HAVA YOLLARI" in h
    # MUAF ≠ ELENMİŞ gerçek vakada da doğru temsil ediliyor.
    d = A.uygunluk_durumu("ALBRK")
    assert d.kapsam_disi is True and d.uygun is None
    A.onbellegi_temizle()


if __name__ == "__main__":
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
