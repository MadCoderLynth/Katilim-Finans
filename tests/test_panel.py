"""Snapshot panel testleri — ağa çıkmaz (Faz 1.4b).

Test edilen şey 1.3'ten gelen iki kararın kodda doğru uygulanması:

  1. `karar` ÖZET oranından, `karar_kalem_bazli` kalem oranından üretilir;
     ikisinin ayrıştığı kayıtlar `h5_ayirt_edici` ile işaretlenir.
  2. Dönem anahtarı META VERİDEN gelir; formun kendi etiketi yalnız
     `form_donem_etiketi` olarak taşınır.

Ayrıca karantina disiplini: self-check kalan kayıt panelden SİLİNMEZ,
işaretlenir.
"""
import csv
import pathlib
import sys
import tempfile
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from katilim import panel  # noqa: E402
from katilim.evren import Sirket  # noqa: E402
from katilim.model import Kalem, KafifBildirim  # noqa: E402

BEYANLAR_TEMIZ = {
    "b1_1": False, "b1_2": False, "b2_1": False, "b2_2": False,
    "b3_1": False, "b3_2": False,
    "b4_1": False, "b4_2": False, "b4_3": False, "b4_4": False,
    "b4_5": False, "b4_6": False, "b4_7": False,
}


def _bildirim(*, gelir_pay=0, gelir_payda=1000, ozet=(0, 0, 0), beyanlar=None,
              yil=2025, periyot="6 Aylık", duzeltme=False):
    """Kalemlerden istenen oranı üreten sentetik bildirim.

    NOT: bu sentetik veridir — duman testi. Gerçek doğrulama
    `tests/test_pilot.py` (20 gerçek KAP belgesi).
    """
    b = KafifBildirim(
        bildirim_id=1, ticker="TEST", yil=yil, periyot=periyot,
        finansal_tablo_niteligi="Konsolide", is_duzeltme=duzeltme,
        gonderim_ts=datetime(2026, 3, 4, 18, 57, 54),
        sablon_imzasi="IMZA",
    )
    b.beyanlar = dict(beyanlar or BEYANLAR_TEMIZ)
    # DOKUZ tutar tablosunun hepsi olmalı: `self_check` eksik tabloyu da
    # kapılıyor (oranlar.py). Gerçek formda dokuzu da var.
    tutarlar = {
        "4B": 0, "4C": gelir_pay, "4D": 0, "4E": gelir_payda,
        "5F": 0, "5G": 0, "5H": 1000, "6I": 0, "6J": 0,
    }
    b.kalemler = [
        Kalem(tablo=t, kalem_no=1, kalem_adi="x", tutar_ham=Decimal(v))
        for t, v in tutarlar.items()
    ]
    b.ozet_gelir_orani = Decimal(str(ozet[0]))
    b.ozet_varlik_orani = Decimal(str(ozet[1]))
    b.ozet_borc_orani = Decimal(str(ozet[2]))
    return b


def _kayit(b, tickerlar=("TEST",), yil=2025, periyot="6 Aylık"):
    return panel.ArsivKayit(
        bildirim=b, bildirim_id=b.bildirim_id or 1, tickerlar=list(tickerlar),
        yil=yil, periyot=periyot, gonderim_ts=b.gonderim_ts, dosya="TEST.html",
    )


# --- H5: iki oran, iki karar ----------------------------------------------


def test_karar_ozet_alanindan_uretiliyor():
    """PNLSN vakasının sentetik hâli: kalem %4,67 (UYGUN), özet %5,30 (aşım).

    Varsayılan H5: `karar` ÖZET'ten gelir. Yanlış yönde seçmek, uygunsuz
    şirketi uygun göstermek olurdu (pahalı hata).
    """
    b = _bildirim(gelir_pay=467, gelir_payda=10000, ozet=(Decimal("5.30"), 0, 0))
    s = panel.satir_uret(_kayit(b), "TEST")
    assert s.gelir_orani_kalem == Decimal("4.67")
    assert s.gelir_orani_ozet == Decimal("5.30")
    assert s.karar == "TOLERANSTA", s.karar          # özet: %5-5,5 bandı
    assert s.karar_kalem_bazli == "UYGUN", s.karar_kalem_bazli
    assert s.oran_ayrisiyor is True
    assert s.h5_ayirt_edici is True


def test_oranlar_tutunca_ayrisma_bayraklari_kapali():
    b = _bildirim(gelir_pay=100, gelir_payda=10000, ozet=(1, 0, 0))
    s = panel.satir_uret(_kayit(b), "TEST")
    assert s.oran_ayrisiyor is False and s.h5_ayirt_edici is False
    assert s.karar == s.karar_kalem_bazli == "UYGUN"
    assert s.self_check == "GECTI" and s.karantina is False


def test_tanimsiz_oran_ayirt_edici_sayilmaz():
    """4E=0 vakası: kalem oranı None, form 0 basıyor.

    Ayrışma var (karantina) ama H5'i sınamaz — biri tanımsızken hangi
    oranın kullanıldığı sorusuna cevap veremez.
    """
    b = _bildirim(gelir_pay=0, gelir_payda=0, ozet=(0, 0, 0))
    s = panel.satir_uret(_kayit(b), "TEST")
    assert s.gelir_orani_kalem is None
    assert s.oran_ayrisiyor is True
    assert s.h5_ayirt_edici is False, "tanımsız oran H5'i ayırt etmez"
    assert s.karantina is True


# --- karantina -------------------------------------------------------------


def test_karantina_kaydi_silinmiyor_isaretleniyor():
    b = _bildirim(gelir_pay=1000, gelir_payda=10000, ozet=(Decimal("12.00"), 0, 0))
    satirlar = panel.snapshot_uret([_kayit(b)])
    assert len(satirlar) == 1, "karantina kaydı panelden düşürülmemeli"
    assert satirlar[0].karantina is True
    assert satirlar[0].self_check == "KALDI"
    assert "self-check" in satirlar[0].karantina_sebebi


# --- dönem anahtarı --------------------------------------------------------


def test_donem_anahtari_meta_veriden_form_etiketi_ayri():
    """Form 'Yıllık' dese de anahtar meta verinin dediğidir."""
    b = _bildirim(yil=2025, periyot="4. 3 Aylık Bildirim")
    s = panel.satir_uret(_kayit(b, yil=2025, periyot="Yıllık"), "TEST")
    assert (s.yil, s.periyot) == (2025, "Yıllık"), "anahtar meta veriden gelmeli"
    assert s.form_donem_etiketi == "2025/4. 3 Aylık Bildirim"


# --- ticker ekseni ---------------------------------------------------------


def test_coklu_kod_her_kod_icin_satir():
    """İndirme tekti; panel ekseni ticker olduğu için satır iki."""
    b = _bildirim()
    satirlar = panel.snapshot_uret([_kayit(b, tickerlar=("ALBRK", "ALK"))])
    assert [s.ticker for s in satirlar] == ["ALBRK", "ALK"]
    assert {s.bildirim_id for s in satirlar} == {1}


def test_muaf_ticker_kapsam_disi():
    b = _bildirim()
    satirlar = panel.snapshot_uret(
        [_kayit(b, tickerlar=("AKBNK",))], muafiyet={"AKBNK": True}
    )
    assert satirlar[0].karar == "KAPSAM_DISI"


def test_belirsiz_muafiyet_muaf_sayilmaz():
    """None = 'karar verilemedi'. Muaf saymak şirketi sessizce düşürürdü."""
    b = _bildirim()
    satirlar = panel.snapshot_uret(
        [_kayit(b, tickerlar=("KTLEV",))], muafiyet={"KTLEV": None}
    )
    assert satirlar[0].karar != "KAPSAM_DISI"


# --- eksik beyan -----------------------------------------------------------


def test_eksik_beyan_belirsiz_uretiyor():
    """Kural 2: okunamayan beyan None kalır ve karar BELİRSİZ olur."""
    beyanlar = dict(BEYANLAR_TEMIZ, b4_5=None)
    b = _bildirim(beyanlar=beyanlar)
    s = panel.satir_uret(_kayit(b), "TEST")
    assert s.karar == "BELIRSIZ" and s.karar_kalem_bazli == "BELIRSIZ"


# --- kalıcılık -------------------------------------------------------------


def test_csv_basliklari_ve_yazim():
    b = _bildirim(gelir_pay=467, gelir_payda=10000, ozet=(Decimal("5.30"), 0, 0),
                  duzeltme=True)
    satirlar = panel.snapshot_uret([_kayit(b)])
    with tempfile.TemporaryDirectory() as d:
        yol = panel.yaz(satirlar, pathlib.Path(d) / "snapshot.csv")
        with open(yol, newline="", encoding="utf-8-sig") as f:
            okunan = list(csv.DictReader(f))
    assert list(okunan[0]) == panel.BASLIKLAR
    r = okunan[0]
    assert r["gelir_orani_kalem"] == "4.67" and r["gelir_orani_ozet"] == "5.30"
    assert r["oran_ayrisiyor"] == "EVET" and r["h5_ayirt_edici"] == "EVET"
    assert r["karar"] == "TOLERANSTA" and r["karar_kalem_bazli"] == "UYGUN"
    assert r["is_duzeltme"] == "EVET"


def test_indeks_yoksa_hata_firlatiyor():
    """Kural 7: 'arşiv okunamadı' ile 'kayıt yok' ayrı durumlar."""
    with tempfile.TemporaryDirectory() as d:
        try:
            panel.ayristir_arsiv(d, indeks_csv=pathlib.Path(d) / "yok.csv")
        except panel.ArsivOkunamadi:
            return
    raise AssertionError("indeks yokken ArsivOkunamadi bekleniyordu")


def test_indekste_olup_diskte_olmayan_dosya_raporlaniyor():
    with tempfile.TemporaryDirectory() as d:
        dizin = pathlib.Path(d)
        ix = dizin / "arsiv_indeksi.csv"
        with open(ix, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["bildirim_id", "ticker", "tum_tickerlar", "yil", "periyot",
                        "gonderim_ts", "durum", "dosya", "bayt", "sha256",
                        "pencere_disi", "not"])
            w.writerow([1, "YOK", "YOK", 2025, "Yıllık", "2026-03-04 18:57:54",
                        "INDIRILDI", "yok.html", 100, "", "HAYIR", ""])
        kayitlar, rapor = panel.ayristir_arsiv(dizin, indeks_csv=ix)
    assert kayitlar == [] and rapor.dosyasi_yok == [1]


# ===== Faz 3.1 — tolerans zincirli tarihsel panel ==========================


def _zincir_kayit(bid, *, gelir_ozet=0, varlik_ozet=0, borc_ozet=0, ts=None,
                  ticker="TEST", yil=2025, periyot="6 Aylık", beyanlar=None):
    """Oranları ÖZET alanından gelen kayıt.

    Panel `karar` sütununu ÖZET'ten üretiyor (H5 varsayılanı), bu yüzden
    zincir testleri de özet alanını sürüyor.
    """
    b = _bildirim(ozet=(gelir_ozet, varlik_ozet, borc_ozet), beyanlar=beyanlar)
    b.bildirim_id = bid
    b.gonderim_ts = ts
    return panel.ArsivKayit(
        bildirim=b, bildirim_id=bid, tickerlar=[ticker], yil=yil,
        periyot=periyot, gonderim_ts=ts, dosya=f"{ticker}_{bid}.html",
    )


def test_dort_donemlik_zincir_temiz_tolerans_temiz_tolerans():
    """temiz -> toleransta -> temiz -> toleransta.

    Kritik nokta üçüncü dönem: temize dönmek tolerans durumunu SIFIRLAR,
    yani dördüncü dönemdeki aşım yeniden TOLERANSTA olur, eleme olmaz.
    """
    # DÖRT AYRI DÖNEM — aynı dönemin düzeltmesi zinciri ilerletmez (2.3).
    kayitlar = [
        _zincir_kayit(1, gelir_ozet=Decimal("1.0"), ts=datetime(2025, 8, 13),
                      yil=2025, periyot="6 Aylık"),
        _zincir_kayit(2, gelir_ozet=Decimal("5.2"), ts=datetime(2026, 3, 11),
                      yil=2025, periyot="Yıllık"),
        _zincir_kayit(3, gelir_ozet=Decimal("2.0"), ts=datetime(2026, 8, 5),
                      yil=2026, periyot="6 Aylık"),
        _zincir_kayit(4, gelir_ozet=Decimal("5.3"), ts=datetime(2027, 3, 9),
                      yil=2026, periyot="Yıllık"),
    ]
    satirlar = panel.panel_uret(kayitlar, [_sirket_kaydi("TEST")])
    assert [s.karar for s in satirlar] == [
        "UYGUN", "TOLERANSTA", "UYGUN", "TOLERANSTA",
    ], [s.karar for s in satirlar]
    assert [s.onceki_donem_tolerans for s in satirlar] == [
        False, False, True, False,
    ]


def test_toleranstan_sonra_farkli_kriterde_asim_eler():
    """H4: tolerans ŞİRKET bazında taşınır, kriter bazında değil.

    Gelirden toleransa düşen şirket, sonraki dönem BORÇTA aşarsa elenir.
    """
    kayitlar = [
        _zincir_kayit(1, gelir_ozet=Decimal("5.2"), ts=datetime(2025, 8, 13),
                      yil=2025, periyot="6 Aylık"),
        _zincir_kayit(2, borc_ozet=Decimal("34.0"), ts=datetime(2026, 3, 11),
                      yil=2025, periyot="Yıllık"),
    ]
    satirlar = panel.panel_uret(kayitlar, [_sirket_kaydi("TEST")])
    assert [s.karar for s in satirlar] == ["TOLERANSTA", "UYGUN_DEGIL"]
    assert satirlar[1].red_kodlari == ["G7_BORC"], satirlar[1].red_kodlari


def test_belirsiz_tolerans_durumunu_sifirlamaz():
    """Kural 2'nin zincirdeki karşılığı: veri eksikliği 'temize çıkma' değil."""
    eksik = dict(BEYANLAR_TEMIZ, b4_5=None)
    kayitlar = [
        _zincir_kayit(1, gelir_ozet=Decimal("5.2"), ts=datetime(2025, 8, 13),
                      yil=2025, periyot="6 Aylık"),
        _zincir_kayit(2, ts=datetime(2026, 3, 11), beyanlar=eksik,
                      yil=2025, periyot="Yıllık"),
        _zincir_kayit(3, gelir_ozet=Decimal("5.1"), ts=datetime(2026, 8, 5),
                      yil=2026, periyot="6 Aylık"),
    ]
    satirlar = panel.panel_uret(kayitlar, [_sirket_kaydi("TEST")])
    assert [s.karar for s in satirlar] == ["TOLERANSTA", "BELIRSIZ", "UYGUN_DEGIL"]
    assert satirlar[2].onceki_donem_tolerans is True, "BELIRSIZ durumu sıfırlamamalı"


def test_kronoloji_gonderim_ts_ile_donem_etiketiyle_degil():
    """Karışık dönem etiketleri; sıra zaman damgasından gelmeli."""
    kayitlar = [
        _zincir_kayit(2, gelir_ozet=Decimal("5.2"), ts=datetime(2026, 3, 11),
                      yil=2025, periyot="Yıllık"),
        _zincir_kayit(1, gelir_ozet=Decimal("1.0"), ts=datetime(2025, 8, 13),
                      yil=2024, periyot="Yıllık"),
        _zincir_kayit(3, gelir_ozet=Decimal("5.1"), ts=datetime(2026, 5, 6),
                      yil=2026, periyot="3 Aylık"),
    ]
    satirlar = panel.panel_uret(kayitlar, [_sirket_kaydi("TEST")])
    assert [s.bildirim_id for s in satirlar] == [1, 2, 3]
    # 1 temiz -> 2 TOLERANSTA -> 3 aşım + önceki toleranslı -> UYGUN_DEGIL
    assert [s.karar for s in satirlar] == ["UYGUN", "TOLERANSTA", "UYGUN_DEGIL"]


def test_zincir_boslugu_isaretleniyor_durum_tasiniyor():
    """Boşluk sonrası satır işaretlenir; GEÇİCİ davranış durumu TAŞIMAK.

    Spec bu durumu tanımlamıyor — karar kullanıcıya bırakıldı.
    """
    kayitlar = [
        _zincir_kayit(1, gelir_ozet=Decimal("5.2"), ts=datetime(2025, 8, 13),
                      yil=2025, periyot="6 Aylık"),
        # 1 yıldan uzun sessizlik: ARADA BİR DÖNEM ATLANMIŞ
        _zincir_kayit(2, gelir_ozet=Decimal("5.1"), ts=datetime(2026, 9, 20),
                      yil=2026, periyot="6 Aylık"),
    ]
    satirlar = panel.panel_uret(kayitlar, [_sirket_kaydi("TEST")])
    assert satirlar[0].zincir_notu == panel.ZINCIR_TEMIZ
    assert satirlar[1].zincir_notu == panel.ZINCIR_BOSLUGU
    # Geçici davranış: durum taşınıyor, yani aşım eleme üretiyor
    assert satirlar[1].karar == "UYGUN_DEGIL"
    assert satirlar[1].onceki_donem_tolerans is True


def test_bosluk_esigi_altindaki_aralik_isaretlenmez():
    """Normal yarıyıl kadansı (ölçülen medyan 185 gün) boşluk değildir."""
    kayitlar = [
        _zincir_kayit(1, ts=datetime(2025, 8, 13), yil=2025, periyot="6 Aylık"),
        _zincir_kayit(2, ts=datetime(2026, 3, 11), yil=2025, periyot="Yıllık"),
    ]
    satirlar = panel.panel_uret(kayitlar, [_sirket_kaydi("TEST")])
    assert all(s.zincir_notu == panel.ZINCIR_TEMIZ for s in satirlar)


def test_panel_karari_ozet_alanindan_uretiliyor():
    """H5 varsayılanı zincirde de geçerli: kalemler DEĞİL, özet alanı.

    Aksi halde tarihsel panel ile snapshot, tolerans zinciriyle ilgisi
    olmayan bir sebeple ayrışırdı.
    """
    # kalemler %4,67 (UYGUN) üretir; özet %5,30 (TOLERANSTA)
    b = _bildirim(gelir_pay=467, gelir_payda=10000, ozet=(Decimal("5.30"), 0, 0))
    b.bildirim_id = 7
    b.gonderim_ts = datetime(2025, 8, 13)
    k = panel.ArsivKayit(bildirim=b, bildirim_id=7, tickerlar=["TEST"], yil=2025,
                         periyot="6 Aylık", gonderim_ts=b.gonderim_ts, dosya="x.html")
    satirlar = panel.panel_uret([k], [_sirket_kaydi("TEST")])
    assert satirlar[0].karar == "TOLERANSTA", "özet alanı kullanılmalı"
    assert satirlar[0].gelir_orani == Decimal("5.30")


def test_muaf_sirket_kapsam_disi_zincirde_de():
    kayitlar = [_zincir_kayit(1, ts=datetime(2025, 8, 13), ticker="AKBNK")]
    satirlar = panel.panel_uret(kayitlar, [_sirket_kaydi("AKBNK", muaf=True)])
    assert satirlar[0].karar == "KAPSAM_DISI"


def test_panel_csv_semasi_spec_15():
    kayitlar = [_zincir_kayit(1, gelir_ozet=Decimal("5.2"), ts=datetime(2025, 8, 13))]
    satirlar = panel.panel_uret(kayitlar, [_sirket_kaydi("TEST")])
    with tempfile.TemporaryDirectory() as d:
        yol = panel.panel_yaz(satirlar, pathlib.Path(d) / "panel.csv")
        with open(yol, newline="", encoding="utf-8-sig") as f:
            okunan = list(csv.DictReader(f))
    assert list(okunan[0]) == panel.KARAR_BASLIKLARI
    r = okunan[0]
    assert r["karar"] == "TOLERANSTA"
    assert r["gecerlilik_baslangic"] == "2025-08-13 00:00:00"
    assert r["red_kodlari"] == "G5_GELIR_TOLERANS"
    assert r["onceki_donem_tolerans"] == "HAYIR"


def _sirket_kaydi(ticker, muaf=False):
    return Sirket(ticker=ticker, unvan=f"{ticker} A.Ş.", kap_member_uuid="u",
                  kap_kfif_slug=None, mali_sektor_muaf=muaf)


# ===== Faz 2.3 — düzeltme çözümü ve DÖNEM bazlı zincir =====================
#
# Gerçek veriden sabitlenmiş regresyon vakaları. Değerler
# `veri/panel/panel.csv`'den alındı ama teste GÖMÜLÜ — arşiv olmadan da
# koşar (veri/ git dışı).


def _d(bid, gun, *, gelir, izi="", yil=2025, periyot="6 Aylık", ticker="X"):
    k = _zincir_kayit(bid, gelir_ozet=Decimal(str(gelir)), ts=gun,
                      ticker=ticker, yil=yil, periyot=periyot)
    k.duzeltme_izi = izi
    return k


def test_pnlsn_ayni_donem_uc_bildirim_zinciri_ilerletmez():
    """PNLSN 2025/6 Aylık: 3 bildirim, hiçbiri diğerinin 'önceki dönemi' değil.

    Eski kod (bildirim bazlı zincir) ilk kaydın TOLERANSTA'sını sonrakilere
    'önceki dönem' diye taşıyordu. Aynı dönemin düzeltmesi YENİ DÖNEM DEĞİL.
    """
    kayitlar = [
        _d(1475001, datetime(2025, 8, 8, 18, 10), gelir="5.30", izi="DUZELTILEN"),
        _d(1477986, datetime(2025, 8, 13, 21, 17), gelir="4.77", izi="DUZENLENEN"),
        _d(1486639, datetime(2025, 9, 4, 23, 18), gelir="4.75"),
    ]
    satirlar = panel.panel_uret(kayitlar, [_sirket_kaydi("X")])
    assert [s.karar for s in satirlar] == ["TOLERANSTA", "UYGUN", "UYGUN"]
    assert all(s.onceki_donem_tolerans is False for s in satirlar),         "aynı dönemin düzeltmesi 'önceki dönem' sayılmamalı"
    # spec §3.2: en geç kayıt geçerli, eskiler SİLİNMEZ
    assert [s.gecerli_kayit for s in satirlar] == [False, False, True]


def test_dcttr_duzeltme_artefakti_kapandi():
    """DCTTR: 2025/Yıllık'ın iki bildirimi de TOLERANSTA.

    Eski kodda ikinci bildirim birincisini 'önceki dönem' sanıp
    UYGUN_DEGIL üretiyordu — 3.1'in çevirdiği 5 satırın biri buydu ve
    4.0'da XKTUM üyesi bir şirkette SAHTE uyuşmazlık açıyordu.
    """
    kayitlar = [
        _d(1474028, datetime(2025, 8, 7, 18, 14), gelir="0.75"),
        _d(1570089, datetime(2026, 3, 10, 22, 28), gelir="4.97",
           izi="DUZELTILEN", periyot="Yıllık"),
        _d(1585103, datetime(2026, 4, 6, 18, 16), gelir="4.66",
           izi="DUZENLENEN", periyot="Yıllık"),
    ]
    satirlar = panel.panel_uret(kayitlar, [_sirket_kaydi("X")])
    kararlar = [s.karar for s in satirlar]
    assert kararlar == ["UYGUN", "UYGUN", "UYGUN"], kararlar
    assert all(s.onceki_donem_tolerans is False for s in satirlar)


def test_onceki_donem_durumu_nokta_zaman():
    """Look-ahead: P(n)'in gördüğü durum, P(n-1)'in O ANDA geçerli kaydından.

    P1 önce TOLERANSTA yayımlanıyor, P2 ondan sonra geliyor (aşımla) ve
    ELENMELİ. P1 daha sonra düzeltilip temizlenirse, P2'nin GEÇMİŞTEKİ
    etiketi değişmez — o kayıt kendi penceresinde canlıydı.
    """
    kayitlar = [
        _d(1, datetime(2025, 8, 10), gelir="5.20"),                    # P1 toleransta
        _d(2, datetime(2026, 3, 10), gelir="5.10", periyot="Yıllık"),  # P2 -> elenmeli
        _d(3, datetime(2026, 4, 10), gelir="1.00"),                    # P1 düzeltmesi: temiz
    ]
    satirlar = panel.panel_uret(kayitlar, [_sirket_kaydi("X")])
    d = {s.bildirim_id: s for s in satirlar}
    assert d[1].karar == "TOLERANSTA"
    assert d[2].karar == "UYGUN_DEGIL", "P2 kendi anında P1 toleranslıydı"
    assert d[2].onceki_donem_tolerans is True
    assert d[3].karar == "UYGUN"


def test_duzeltme_olayi_alanlari():
    """Olay: değişen oranlar + değişen beyanlar + HAYIR<->EVET bayrağı."""
    from katilim import toplayici

    k1 = _d(1, datetime(2025, 8, 8), gelir="5.30")
    k2 = _d(2, datetime(2025, 8, 13), gelir="4.77", izi="DUZENLENEN")
    k2.bildirim.beyanlar = dict(BEYANLAR_TEMIZ, b4_1=True)   # HAYIR -> EVET
    gecerli, olaylar = toplayici.duzeltmeleri_coz([k1, k2])

    assert len(gecerli) == 1 and gecerli[0].bildirim_id == 2, "en geç kazanır"
    assert len(olaylar) == 1
    o = olaylar[0]
    assert o.ilk_bildirim_id == 1 and o.duzeltme_bildirim_id == 2
    assert o.duzeltme_izi == "DUZENLENEN"
    assert o.degisen_oranlar["gelir"] == (Decimal("5.30"), Decimal("4.77"))
    assert o.degisen_beyanlar["b4_1"] == (False, True)
    assert o.karar_ceviren_beyan is True


def test_beyan_none_a_donerse_karar_ceviren_sayilmaz():
    """None <-> bool veri EKSİKLİĞİ; HAYIR<->EVET ile aynı şey değil."""
    from katilim import toplayici

    k1 = _d(1, datetime(2025, 8, 8), gelir="1.0")
    k2 = _d(2, datetime(2025, 8, 13), gelir="1.0")
    k2.bildirim.beyanlar = dict(BEYANLAR_TEMIZ, b4_1=None)
    _, olaylar = toplayici.duzeltmeleri_coz([k1, k2])
    assert olaylar[0].degisen_beyanlar["b4_1"] == (False, None)
    assert olaylar[0].karar_ceviren_beyan is False


def test_uc_bildirim_iki_olay_uretir():
    from katilim import toplayici

    kayitlar = [
        _d(1, datetime(2025, 8, 8), gelir="5.30"),
        _d(2, datetime(2025, 8, 13), gelir="4.77"),
        _d(3, datetime(2025, 9, 4), gelir="4.75"),
    ]
    gecerli, olaylar = toplayici.duzeltmeleri_coz(kayitlar)
    assert len(olaylar) == 2 and len(gecerli) == 1
    assert [o.kayit_sayisi for o in olaylar] == [3, 3]


def test_is_duzeltme_metin_aramasindan_gelmiyor():
    """2.3: parser artık sayfa metninde 'düzeltme' ARAMIYOR.

    Kaynak yapılandırılmış (`isChanged`); alan toplama katmanında set
    ediliyor. Parser'ın kendi başına True üretmemesi gerekiyor.
    """
    import inspect

    from katilim import ayristirici

    kod = inspect.getsource(ayristirici)
    assert 'is_duzeltme = "duzeltme"' not in kod, "metin araması geri gelmiş"


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
