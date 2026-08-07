"""Derinlik keşfi ayıklayıcısının testleri — ağa çıkmaz.

**Katman uyarısı (CLAUDE.md "Test katmanları").** Buradaki HTML sentetiktir:
duman testidir, gerçek KAP gövdesinin bu yapıda olduğunu KANITLAMAZ. Gerçek
doğrulama, betiğin canlı sayfaya karşı koşturulmasıdır (DERINLIK_KESFI_RAPORU.md).

Test edilen asıl davranış **değiştirilemez kural 7**: "0 kayıt döndü" ile
"sayfayı ayrıştıramadım" ayrı durumlardır. 1.0 turundaki iki ölçüm hatası da
bu ayrımın kodda karşılığı olmamasından çıkmıştı.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "arac"))

from derinlik_kesfi import (  # noqa: E402
    SayfaOkunamadi,
    _json_nesnesi,
    bos_sonuc_mu,
    ilan_edilen_pencere,
    rsc_bildirimleri,
    sorgu_olc,
)

# KAP'ın RSC yükü bir script string'i içinde durur: tırnaklar kaçışlıdır.
_KAYIT = (
    '{\\"disclosureBasic\\":{\\"publishDate\\":\\"05.08.2026 08:01:05\\",'
    '\\"disclosureIndex\\":1643241,\\"stockCode\\":\\"THYAO\\",'
    '\\"title\\":\\"Katılım Finansı İlkeleri Bilgi Formu \\",'
    '\\"disclosureClass\\":\\"DG\\",\\"year\\":2026,\\"period\\":2,'
    '\\"fundCode\\":null}}'
)
_KAYIT_ESKI = (
    '{\\"disclosureBasic\\":{\\"publishDate\\":\\"05.08.2025 19:15:36\\",'
    '\\"disclosureIndex\\":1472624,\\"stockCode\\":\\"THYAO\\",'
    '\\"title\\":\\"Özel Durum Açıklaması (Genel)\\",'
    '\\"disclosureClass\\":\\"ODA\\",\\"year\\":null,\\"period\\":null,'
    '\\"fundCode\\":null}}'
)

# Boş-sonuç metni HER sayfada var: i18n sözlüğünde. Tuzak tam burada.
_SOZLUK = '<script>self.__next_f.push([1,"{\\"noDataShow\\":\\"Bildirim bulunamadı.\\"}"])</script>'


def _sayfa(kayitlar="", tablo_satirlari="", sayi=None, pencere=True):
    ust = ""
    if pencere:
        ust = (
            "<div><span><strong>Başlangıç Tarihi<!-- -->:</strong> <!-- -->05-08-2025 </span>"
            "<span><strong>Bitiş Tarihi<!-- -->:</strong> <!-- -->05-08-2026 </span></div>"
        )
    sayac = f'<div class="w-full text-right font-bold pr-3">{sayi} bildirim bulundu.</div>' if sayi is not None else ""
    return (
        f'<html><body>{_SOZLUK}<script>self.__next_f.push([1,"[{kayitlar}]"])</script>'
        f"{ust}{sayac}<table><tr><th>#</th><th>Tarih</th></tr>{tablo_satirlari}</table></body></html>"
    )


def _satir(bid):
    return f'<tr><td><input name="notification-checkbox" id="{bid}"></td><td>05.08.2026</td></tr>'


def test_dolu_sayfa_olculuyor():
    html = _sayfa(
        kayitlar=f"{_KAYIT},{_KAYIT_ESKI}",
        tablo_satirlari=_satir(1643241) + _satir(1472624),
        sayi=2,
    )
    o = sorgu_olc(html)
    assert o["sinif"] == "DOLU", o
    assert o["sunucu_sayisi"] == 2 and o["rsc_kayit"] == 2 and o["dom_kayit"] == 2
    assert o["en_eski"] == "05.08.2025 19:15:36", o["en_eski"]
    assert o["en_yeni"] == "05.08.2026 08:01:05", o["en_yeni"]
    assert o["kafif_idleri"] == ["1643241"], o["kafif_idleri"]
    assert o["siniflar"] == ["DG", "ODA"], o["siniflar"]


def test_bos_sonuc_hata_degildir():
    """Sunucu 'bulunamadı' bastıysa bu geçerli bir cevap: BOS, hata değil."""
    html = _sayfa(tablo_satirlari="<tr><td>Bildirim bulunamadı.</td></tr>", sayi=0)
    o = sorgu_olc(html)
    assert o["sinif"] == "BOS", o
    assert o["sunucu_sayisi"] == 0


def test_okunamayan_sayfa_hata_firlatir():
    """Kural 7: hiçbir çıpa yoksa sessizce boş liste DÖNÜLMEZ."""
    try:
        sorgu_olc("<html><body><div id='root'></div></body></html>")
    except SayfaOkunamadi:
        return
    raise AssertionError("çıpasız sayfada SayfaOkunamadi bekleniyordu")


def test_sozlukteki_bos_metin_dolu_sayfayi_bos_gostermez():
    """i18n sözlüğündeki 'Bildirim bulunamadı.' her sayfada var; tablo doluysa
    sayfa BOŞ değildir. 1.0'daki ölçüm hatasının tam olarak bu."""
    html = _sayfa(kayitlar=_KAYIT, tablo_satirlari=_satir(1643241), sayi=1)
    assert "Bildirim bulunamadı" in html
    assert bos_sonuc_mu(html) is False
    assert sorgu_olc(html)["sinif"] == "DOLU"


def test_ilan_edilen_pencere_okunuyor():
    bas, bit = ilan_edilen_pencere(_sayfa(sayi=0))
    assert (bas, bit) == ("05-08-2025", "05-08-2026"), (bas, bit)


def test_sunucu_render_farki_sayfalamayi_ele_verir():
    """Sunucu 98 diyor ama 1 kayıt render edildiyse sayfalama var demektir."""
    o = sorgu_olc(_sayfa(kayitlar=_KAYIT, tablo_satirlari=_satir(1643241), sayi=98))
    assert o["sunucu_render_farki"] == 97, o["sunucu_render_farki"]


def test_json_nesnesi_ic_ice_suslu_ve_kacisli_tirnak():
    """Alan sırasına dayanan regex yerine parantez eşlemesi: iç içe nesne ve
    dize içindeki '}' karakteri ayıklamayı bozmamalı."""
    metin = '{"a":{"b":"}"},"c":"\\"x\\"","d":1} KUYRUK'
    assert _json_nesnesi(metin, 0) == '{"a":{"b":"}"},"c":"\\"x\\"","d":1}'


def test_rsc_kaydi_alan_sirasindan_bagimsiz():
    ters = (
        '{\\"disclosureBasic\\":{\\"fundCode\\":null,\\"disclosureIndex\\":1,'
        '\\"publishDate\\":\\"01.01.2026 10:00:00\\"}}'
    )
    kayitlar = rsc_bildirimleri(_sayfa(kayitlar=ters, tablo_satirlari=_satir(1), sayi=1))
    assert len(kayitlar) == 1 and kayitlar[0]["disclosureIndex"] == 1, kayitlar


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
