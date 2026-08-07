"""Bildirim geçmişi toplayıcısının testleri — ağa çıkmaz.

**Katman uyarısı (CLAUDE.md "Test katmanları").** Buradaki HTML sentetiktir:
parser mekaniğinin çalıştığını gösterir, gerçek KAP gövdesinin bu yapıda
olduğunu KANITLAMAZ. Gerçek doğrulama `python -m katilim.cli bildirimler`
koşumudur (BILDIRIM_GECMISI_RAPORU.md).

Sentetik gövde, 2.0 turunda ölçülen gerçek RSC kaydının alan adlarını ve
kaçış biçimini birebir taklit ediyor — uydurulmuş değil, kopyalanmış.
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from katilim import bildirim  # noqa: E402
from katilim.evren import Sirket  # noqa: E402

_SOZLUK = (
    '<script>self.__next_f.push([1,"{\\"noDataShow\\":\\"Bildirim bulunamadı.\\"}"])'
    "</script>"
)


def _kayit(bid, baslik, tarih, yil=2025, donem="Yıllık", sinif="DG", kod="THYAO"):
    yil_s = "null" if yil is None else str(yil)
    return (
        '{\\"disclosureBasic\\":{\\"publishDate\\":\\"' + tarih + '\\",'
        '\\"disclosureIndex\\":' + str(bid) + ',\\"stockCode\\":\\"' + kod + '\\",'
        '\\"companyTitle\\":\\"X A.Ş.\\",\\"title\\":\\"' + baslik + '\\",'
        '\\"disclosureClass\\":\\"' + sinif + '\\",\\"isChanged\\":null,'
        '\\"year\\":' + yil_s + ',\\"period\\":4,\\"donem\\":\\"' + donem + '\\",'
        '\\"fundCode\\":null}}'
    )


def _sayfa(kayitlar=(), sayi=None, satirlar="", tablo=True):
    sayac = (
        f'<div class="w-full text-right font-bold pr-3">{sayi} bildirim bulundu.</div>'
        if sayi is not None
        else ""
    )
    govde = f'<table><tr><th>#</th></tr>{satirlar}</table>' if tablo else ""
    return (
        f'<html><body>{_SOZLUK}'
        f'<script>self.__next_f.push([1,"[{",".join(kayitlar)}]"])</script>'
        f"{sayac}{govde}</body></html>"
    )


def _satir(bid):
    return f'<tr><td><input name="notification-checkbox" id="{bid}"></td></tr>'


# --- kural 7: üç durum -----------------------------------------------------


def test_dolu_sayfa_kafif_ayikliyor():
    html = _sayfa(
        kayitlar=[
            _kayit(1566002, "Katılım Finansı İlkeleri Bilgi Formu ", "04.03.2026 18:57:54"),
            _kayit(1600000, "Özel Durum Açıklaması (Genel)", "05.03.2026 09:00:00", sinif="ODA"),
        ],
        sayi=2,
        satirlar=_satir(1566002) + _satir(1600000),
    )
    s = bildirim.ayikla(html)
    assert s.sinif == "DOLU"
    assert len(s.bildirimler) == 2
    assert [b.bildirim_id for b in s.kafifler] == [1566002]
    k = s.kafifler[0]
    assert k.yil == 2025 and k.periyot == "Yıllık"
    assert k.gonderim_ts.isoformat() == "2026-03-04T18:57:54"
    assert s.eksik_ayiklama is False


def test_bos_sonuc_hata_degil():
    html = _sayfa(sayi=0, satirlar="<tr><td>Bildirim bulunamadı.</td></tr>")
    s = bildirim.ayikla(html)
    assert s.sinif == "BOS" and s.kafifler == []


def test_okunamayan_sayfa_hata_firlatir():
    try:
        bildirim.ayikla("<html><body><div id='root'></div></body></html>")
    except bildirim.SayfaOkunamadi:
        return
    raise AssertionError("çıpasız sayfada SayfaOkunamadi bekleniyordu")


def test_sozlukteki_bos_metin_dolu_sayfayi_bos_gostermez():
    """'Bildirim bulunamadı.' i18n sözlüğünde HER sayfada geçiyor."""
    html = _sayfa(
        kayitlar=[_kayit(1, "Katılım Finansı İlkeleri Bilgi Formu ", "01.01.2026 10:00:00")],
        sayi=1,
        satirlar=_satir(1),
    )
    assert "Bildirim bulunamadı" in html
    assert bildirim.ayikla(html).sinif == "DOLU"


def test_eksik_ayiklama_isaretleniyor():
    """Sunucu 5 dedi, 1 ayıklandıysa sessiz kayıp var demektir."""
    html = _sayfa(
        kayitlar=[_kayit(1, "Katılım Finansı İlkeleri Bilgi Formu ", "01.01.2026 10:00:00")],
        sayi=5,
        satirlar=_satir(1),
    )
    assert bildirim.ayikla(html).eksik_ayiklama is True


# --- içerik imzası ---------------------------------------------------------


def test_kafif_konusu_icerik_imzasiyla_taniniyor():
    assert bildirim.kafif_mi("Katılım Finansı İlkeleri Bilgi Formu ")
    assert bildirim.kafif_mi("KATILIM FİNANSI İLKELERİ BİLGİ FORMU")
    assert bildirim.kafif_mi("Katılım  Finansı   İlkeleri Bilgi Formu")
    assert not bildirim.kafif_mi("Özel Durum Açıklaması (Genel)")
    assert not bildirim.kafif_mi(None)


def test_donem_cizgi_ise_none_kalir():
    """'-' dönem bilgisi yok demek; sayısal period'dan etiket TÜRETİLMEZ."""
    html = _sayfa(
        kayitlar=[_kayit(9, "Katılım Finansı İlkeleri Bilgi Formu ", "01.01.2026 10:00:00",
                         yil=None, donem="-")],
        sayi=1,
        satirlar=_satir(9),
    )
    b = bildirim.ayikla(html).kafifler[0]
    assert b.periyot is None and b.yil is None


# --- uuid ekseni -----------------------------------------------------------


class SahteCekici:
    """Ağ yerine sözlükten servis eder; hangi URL'in istendiğini sayar."""

    def __init__(self, harita):
        self.harita = harita
        self.istekler = []
        self.istatistik = {"onbellek": 0, "ag": 0, "yeniden_deneme": 0, "negatif": 0}

    def getir(self, url, *, zorla=False):
        self.istekler.append(url)
        if url not in self.harita:
            from katilim.cekici import ÇekimHatası

            raise ÇekimHatası(f"HTTP 404: {url}")
        return self.harita[url]


def _sirket(ticker, uuid, muaf=False):
    return Sirket(ticker=ticker, unvan=f"{ticker} A.Ş.", kap_member_uuid=uuid,
                  kap_kfif_slug=None, mali_sektor_muaf=muaf)


def test_coklu_kodlu_sirket_tek_kez_sorgulanir_iki_satir_uretir():
    uuid = "u1"
    html = _sayfa(
        kayitlar=[_kayit(500, "Katılım Finansı İlkeleri Bilgi Formu ",
                         "01.02.2026 10:00:00", kod="ALBRK, ALK")],
        sayi=1,
        satirlar=_satir(500),
    )
    cekici = SahteCekici({bildirim.SORGU_KALIBI.format(uuid=uuid): html})
    t = bildirim.gecmisi_topla([_sirket("ALBRK", uuid), _sirket("ALK", uuid)], cekici)

    assert len(cekici.istekler) == 1, "aynı uuid iki kez sorgulanmamalı"
    assert sorted(s["ticker"] for s in t.satirlar) == ["ALBRK", "ALK"]
    assert t.kafif_kimlikleri == {500}, "benzersiz form sayısı 1 olmalı"
    assert t.uyarilar == []


def test_muaf_sirket_sorgulanmaz():
    cekici = SahteCekici({})
    t = bildirim.gecmisi_topla([_sirket("AKBNK", "u2", muaf=True)], cekici)
    assert cekici.istekler == []
    assert t.durumlar[0].durum == bildirim.DURUM_MUAF


def test_belirsiz_muafiyet_sorgulanir():
    """None = 'karar verilemedi'. Sorgulamamak şirketi sessizce düşürürdü."""
    uuid = "u3"
    cekici = SahteCekici({bildirim.SORGU_KALIBI.format(uuid=uuid): _sayfa(sayi=0,
                          satirlar="<tr><td>Bildirim bulunamadı.</td></tr>")})
    t = bildirim.gecmisi_topla([_sirket("KTLEV", uuid, muaf=None)], cekici)
    assert len(cekici.istekler) == 1
    assert t.durumlar[0].durum == bildirim.DURUM_BOS_SONUC


def test_okunamayan_sayfa_sirketi_sessizce_dusurmez():
    uuid = "u4"
    cekici = SahteCekici({bildirim.SORGU_KALIBI.format(uuid=uuid): "<html><body></body></html>"})
    t = bildirim.gecmisi_topla([_sirket("XYZ", uuid)], cekici)
    assert t.durumlar[0].durum == bildirim.DURUM_OKUNAMADI
    assert t.uyarilar, "okunamayan sayfa uyarı üretmeli"


def test_cekim_hatasi_kaydediliyor():
    cekici = SahteCekici({})           # her URL 404
    t = bildirim.gecmisi_topla([_sirket("YOK", "u5")], cekici)
    assert t.durumlar[0].durum == bildirim.DURUM_CEKIM_HATASI
    assert t.satirlar == []


def test_kod_uyusmazligi_uyari_uretir():
    """Bildirimin pay kodu evrendeki kodla kesişmiyorsa uuid eşlemesi bozuk."""
    uuid = "u6"
    html = _sayfa(
        kayitlar=[_kayit(700, "Katılım Finansı İlkeleri Bilgi Formu ",
                         "01.02.2026 10:00:00", kod="BASKA")],
        sayi=1,
        satirlar=_satir(700),
    )
    cekici = SahteCekici({bildirim.SORGU_KALIBI.format(uuid=uuid): html})
    t = bildirim.gecmisi_topla([_sirket("THYAO", uuid)], cekici)
    assert any("KOD UYUŞMAZLIĞI" in u for u in t.uyarilar), t.uyarilar


# --- kalıcılık -------------------------------------------------------------


def test_csv_gidis_donus():
    satirlar = [
        {"ticker": "THYAO", "bildirim_id": 1566002, "yil": 2025, "periyot": "Yıllık",
         "gonderim_ts": bildirim._ts("04.03.2026 18:57:54"),
         "konu": "Katılım Finansı İlkeleri Bilgi Formu", "indirildi_mi": False},
    ]
    with tempfile.TemporaryDirectory() as d:
        yol = pathlib.Path(d) / "g.csv"
        bildirim.yaz(satirlar, yol)
        geri = bildirim.oku(yol)
    assert geri == satirlar


def test_indirilmis_isareti_korunuyor():
    """1.2 yeniden koşunca 1.4'ün indirdiği formlar 'indirilmedi' olmamalı."""
    with tempfile.TemporaryDirectory() as d:
        yol = pathlib.Path(d) / "g.csv"
        temel = {"ticker": "THYAO", "bildirim_id": 1, "yil": 2025, "periyot": "Yıllık",
                 "gonderim_ts": None, "konu": "K", "indirildi_mi": True}
        bildirim.yaz([temel], yol)
        yeni = [dict(temel, indirildi_mi=False)]
        bildirim.yaz(bildirim.indirilenleri_koru(yeni, yol), yol)
        assert bildirim.oku(yol)[0]["indirildi_mi"] is True


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
