"""Evren (Faz 1.1) test paketi. Ağa çıkmaz.

Fixture uydurma değil: `bist_sirketler_parca.html` gerçek KAP gövdesinden
kesilmiş bir parça (bkz. `fixtures/olustur_evren_parca.py`). Yine de
CLAUDE.md'nin test katmanı ayrımı burada da geçerli — bu parça RSC yükünün
biçimini kanıtlar, KAP'ın onu hep bu biçimde üreteceğini kanıtlamaz.

En kritik test `test_eslesme_konuma_bagli_degil`: DOM satırlarının sırası
bozulduğunda sonuç değişmemeli. Değişiyorsa eşleme konuma kaymış demektir
ve bu, sessizce yanlış şirkete slug atayan sınıftan bir hatadır.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from bs4 import BeautifulSoup  # noqa: E402

from katilim.evren import (  # noqa: E402
    Sirket,
    dom_satirlari,
    evreni_ayristir,
    fark,
    mali_sektor_muaf_mi,
    oku,
    rsc_kayitlari,
    unvan_slug,
    yaz,
)

PARCA = pathlib.Path(__file__).parent / "fixtures" / "bist_sirketler_parca.html"


def _html() -> str:
    return PARCA.read_text(encoding="utf-8")


def _sirketler() -> list[Sirket]:
    return evreni_ayristir(_html())[0]


def _bul(ticker: str) -> Sirket:
    return next(s for s in _sirketler() if s.ticker == ticker)


# ===== RSC ayrıştırma =====================================================

def test_rsc_yuku_okunuyor():
    kayitlar = rsc_kayitlari(_html())
    assert len(kayitlar) == 5, len(kayitlar)
    thy = next(k for k in kayitlar if k["stockCode"] == "THYAO")
    assert thy["mkkMemberOid"] == "4028e4a140f2ed720140f376bebb01a7"
    assert thy["kapMemberTitle"] == "TÜRK HAVA YOLLARI A.O."
    assert thy["cityName"] == "İSTANBUL"


def test_rsc_kacisli_tirnak_geri_alinmazsa_okunmaz():
    """Yük bir script string'i içinde; kaçış geri alınmadan JSON değil."""
    ham = _html()
    assert '\\"mkkMemberOid\\"' in ham, "fixture kaçışsız, gerçek biçimi temsil etmiyor"


# ===== Ticker ile eşleme (konum değil) ====================================

def test_slug_ticker_uzerinden_eslesiyor():
    assert _bul("THYAO").kap_kfif_slug == "1107-turk-hava-yollari-a-o"


def test_denetci_linki_slug_sanilmiyor():
    """Satırda hem şirketin hem denetim kuruluşunun linki var.

    'İlk linki al' deseydik THYAO'ya PwC'nin slug'ı atanabilirdi.
    """
    for s in _sirketler():
        if s.kap_kfif_slug:
            assert "bagimsiz-denetim" not in s.kap_kfif_slug, s
            assert "pwc" not in s.kap_kfif_slug, s


def test_eslesme_konuma_bagli_degil():
    """DOM satır sırası bozulunca sonuç değişmemeli (CLAUDE.md kural 4)."""
    corba = BeautifulSoup(_html(), "html.parser")
    tablo = corba.find("table")
    satirlar = tablo.find_all("tr")[1:]
    for tr in reversed(satirlar):      # sırayı tersine çevir
        tablo.append(tr.extract())

    karisik, _ = evreni_ayristir(str(corba))
    duzgun = _sirketler()
    assert {s.ticker: s.kap_kfif_slug for s in karisik} == {
        s.ticker: s.kap_kfif_slug for s in duzgun
    }


def test_coklu_pay_kodu_ayri_satir_olur():
    """'ALBRK, ALK' tek tüzel kişi, iki pay kodu. Ticker birincil anahtar."""
    albrk, alk = _bul("ALBRK"), _bul("ALK")
    assert albrk.kap_member_uuid == alk.kap_member_uuid
    assert albrk.kap_kfif_slug == alk.kap_kfif_slug == "2414-albaraka-turk-katilim-bankasi-a-s"
    assert albrk.unvan == alk.unvan


def test_dom_hucresindeki_coklu_kod_bolunuyor():
    harita = dom_satirlari(_html())
    assert "ALBRK" in harita and "ALK" in harita


def test_unvan_slug_turkce_harfleri_dogru_ceviriyor():
    assert unvan_slug("TÜRK HAVA YOLLARI A.O.") == "turk-hava-yollari-a-o"
    # noktasız 'ı' tuzağı: sadece NFKD ile 'katilim' değil 'kat lim' çıkardı
    assert unvan_slug("ALBARAKA TÜRK KATILIM BANKASI A.Ş.") == (
        "albaraka-turk-katilim-bankasi-a-s"
    )


# ===== Eşleşmeyen kayıt ===================================================

def test_eslesmeyen_kayit_dusurulmuyor():
    """AGHOL'ün DOM satırı fixture'da yok; kayıt yine de listede olmalı."""
    aghol = _bul("AGHOL")
    assert aghol.kap_kfif_slug is None
    assert aghol.kap_member_uuid, "uuid kaybolmamalı"


def test_eslesmeyen_kayit_raporlaniyor():
    _, rapor = evreni_ayristir(_html())
    assert rapor.slug_bulunamayan == ["AGHOL"], rapor.slug_bulunamayan
    assert rapor.rsc_kayit == 5
    assert rapor.eslesen == 5          # THYAO, ALBRK, ALK, ISYAT, AKYHO
    assert rapor.coklu_kod == ["ALBRK+ALK"]


# ===== Muafiyet sınıflaması ===============================================

def test_muafiyet_banka():
    assert mali_sektor_muaf_mi("ALBARAKA TÜRK KATILIM BANKASI A.Ş.") is True
    # 'banka' kalıbı bunları kaçırıyordu: normalize -> 'akbank', 'sekerbank'
    assert mali_sektor_muaf_mi("AKBANK T.A.Ş.") is True
    assert mali_sektor_muaf_mi("ŞEKERBANK T.A.Ş.") is True
    assert mali_sektor_muaf_mi("ANADOLUBANK A.Ş.") is True
    assert mali_sektor_muaf_mi("BURGAN BANK A.Ş.") is True


def test_banka_adi_tasiyan_spv_muaf_sayilmiyor():
    """'AKTİF BANK SUKUK VARLIK KİRALAMA' bir sukuk aracı, banka değil.

    'bank' kalıbına takılıp muaf sayılırsa şirket panelden sessizce düşer.
    Belirsiz kalıpları bu yüzden muaf kalıplarından önce bakılıyor.
    """
    assert mali_sektor_muaf_mi("AKTİF BANK SUKUK VARLIK KİRALAMA A.Ş.") is None


def test_muafiyet_diger_finans_kurumlari():
    for unvan in (
        "ANADOLU HAYAT EMEKLİLİK A.Ş.",
        "ŞEKER FİNANSAL KİRALAMA A.Ş.",
        "LİDER FAKTORİNG A.Ş.",
        "AKSİGORTA A.Ş.",
        "A1 CAPITAL YATIRIM MENKUL DEĞERLER A.Ş.",
    ):
        assert mali_sektor_muaf_mi(unvan) is True, unvan


def test_muafiyet_holding_muaf_degil():
    """Spec §0.4: Holding ve GSYO KAFİF dolduruyor."""
    assert mali_sektor_muaf_mi("AG ANADOLU GRUBU HOLDİNG A.Ş.") is False


def test_holding_istisnasi_muafiyet_kalibini_yener():
    """'AKDENİZ YATIRIM HOLDİNG' hem 'yatirim' hem 'holding' geçiriyor."""
    assert _bul("AKYHO").mali_sektor_muaf is False


def test_gayrimenkul_yatirim_ortakligi_muaf_degil():
    """'gayrimenkul' içinde 'menkul' geçiyor — kalıp tuzağı."""
    assert mali_sektor_muaf_mi("İŞ GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.") is False
    assert mali_sektor_muaf_mi("RHEA GİRİŞİM SERMAYESİ YATIRIM ORTAKLIĞI A.Ş.") is False


def test_mkyo_belirsiz_kalibini_yener():
    """MKYO Spec §0.4 muafiyet listesinde açıkça var; tekil ve çoğul yazım."""
    assert mali_sektor_muaf_mi("ATLAS MENKUL KIYMETLER YATIRIM ORTAKLIĞI A.Ş.") is True
    assert mali_sektor_muaf_mi("X MENKUL KIYMET YATIRIM ORTAKLIĞI A.Ş.") is True


def test_muafiyet_belirsiz_none_kalir():
    """Sade 'Yatırım Ortaklığı' MKYO olabilir de olmayabilir de.

    Yanlış MUAF şirketi panelden sessizce düşürür; None yalnızca el ile
    bakılacak listeyi uzatır. Şüphe None'a gider.
    """
    assert _bul("ISYAT").mali_sektor_muaf is None
    # Sukuk ihraç aracı: §0.4'ün "varlık yönetim"i bundan farklı bir şey.
    assert mali_sektor_muaf_mi("ATA VARLIK KİRALAMA A.Ş.") is None


def test_tasarruf_finansman_muaf():
    """Spec §0.4'e 8 Ağu 2026'da eklendi; kod aynı commit'te takip etti.

    Gerekçe 4.0'ın bulgusu: KTLEV KAFİF vermiyor ama BIST KATILIM
    30/50/100/TÜM'ün hepsinde. Muafiyet uygunsuzluk değil KAPSAM
    DIŞILIKTIR ve endeks üyeliğini engellemez — "MUAF ≠ ELENMİŞ".
    """
    assert mali_sektor_muaf_mi("KATILIMEVİM TASARRUF FİNANSMAN A.Ş.") is True


def test_muafiyet_sanayi_sirketi():
    assert mali_sektor_muaf_mi("TÜRK HAVA YOLLARI A.O.") is False
    assert mali_sektor_muaf_mi("ASELSAN ELEKTRONİK SANAYİ VE TİCARET A.Ş.") is False


# ===== Kalıcılık ==========================================================

def test_csv_gidis_donus_ucuncu_durumu_koruyor():
    """EVET/HAYIR/boş üçlüsü bozulmadan dönmeli.

    None -> False'a düşerse muaf olmayan bir şirket muaf sayılmaz ama
    'el ile bakılacak' listesi sessizce boşalır.
    """
    with tempfile.TemporaryDirectory() as d:
        yol = pathlib.Path(d) / "sirketler.csv"
        yaz(_sirketler(), yol, arsivle=False)
        geri = {s.ticker: s for s in oku(yol)}
        assert geri["ISYAT"].mali_sektor_muaf is None
        assert geri["ALBRK"].mali_sektor_muaf is True
        assert geri["THYAO"].mali_sektor_muaf is False
        assert geri["AGHOL"].kap_kfif_slug is None
        assert geri["THYAO"].kap_kfif_slug == "1107-turk-hava-yollari-a-o"
        assert len(geri) == 6


def test_csv_bom_ile_yaziliyor():
    """utf-8-sig: Excel Türkçe karakterleri bozmasın."""
    with tempfile.TemporaryDirectory() as d:
        yol = pathlib.Path(d) / "sirketler.csv"
        yaz(_sirketler(), yol, arsivle=False)
        assert yol.read_bytes().startswith(b"\xef\xbb\xbf")


def test_arsiv_onceki_surumu_saklar():
    with tempfile.TemporaryDirectory() as d:
        yol = pathlib.Path(d) / "sirketler.csv"
        yaz(_sirketler()[:2], yol, arsivle=False)
        ilk = yol.read_bytes()
        time.sleep(0.01)
        arsiv = yaz(_sirketler(), yol)
        assert arsiv is not None and arsiv.exists(), "önceki sürüm arşivlenmedi"
        assert arsiv.read_bytes() == ilk
        assert yol.read_bytes() != ilk


def test_fark_evren_degisimini_yakaliyor():
    hepsi = _sirketler()
    eklenen, cikan = fark(hepsi[:-1], hepsi)
    assert eklenen == [hepsi[-1].ticker] and cikan == []
    eklenen, cikan = fark(hepsi, hepsi[:-1])
    assert eklenen == [] and cikan == [hepsi[-1].ticker]


# ===== Bağımsız koşucu ====================================================

def _kos() -> int:
    import traceback
    testler = [
        (ad, fn) for ad, fn in sorted(globals().items())
        if ad.startswith("test_") and callable(fn)
    ]
    basarisiz = []
    for ad, fn in testler:
        try:
            fn()
            print(f"  ok    {ad}")
        except Exception:
            basarisiz.append(ad)
            print(f"  HATA  {ad}")
            print("        " + traceback.format_exc().replace("\n", "\n        "))
    print(f"\n{len(testler) - len(basarisiz)}/{len(testler)} test geçti")
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(_kos())
