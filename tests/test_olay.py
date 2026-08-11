"""Olay serisi testleri — ağa çıkmaz (Faz 5.1).

**Bu dosyanın ASIL konusu look-ahead denetimidir** (§ "LOOK-AHEAD"). Diğer
testler davranışı donduruyor; look-ahead testi modülün var olma sebebini
sınıyor: bir olay, yalnız o an yayımlanmış veriden üretilmiş olmalı.

İki kademe:

1. **Fixture kademesi (her zaman):** olay tipleri, karşı olay, kılpayı
   eşiği, olgunluk ve yürürlük türetimi sentetik veriyle donduruluyor.
2. **Gerçek veri kademesi (panel + referans varsa):** 5.1 koşusunun
   ölçtüğü sayılar ve gerçek DOGUB/PNLSN vakaları. Dosyalar yoksa test
   **atlandığını duyurur**, sessizce geçmez.
"""
import csv
import pathlib
import sys
import tempfile
import traceback
from datetime import date, datetime, timedelta
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from katilim import olay as O  # noqa: E402

KOK = pathlib.Path(__file__).resolve().parents[1]
_PANEL = KOK / "veri" / "panel" / "panel.csv"
_DONEM = KOK / "veri" / "referans" / "xktum_donemler.csv"

# 5.1 koşusunun ölçtüğü sayılar. Değişirse bu bir BULGUDUR.
OLCULEN = {"olay": 206, "pay_kodu": 137, "karsi_olay": 84}

PANEL_BASLIK = ["ticker", "yil", "periyot", "gecerlilik_baslangic", "karar",
                "red_kodlari", "gelir_orani", "varlik_orani", "borc_orani",
                "onceki_donem_tolerans", "sablon_versiyon", "self_check",
                "bildirim_id", "zincir_notu", "duzeltme_izi", "gecerli_kayit"]
DONEM_BASLIK = ["donem_baslangic", "donem_bitis", "duyuru_tarihi",
                "uye_sayisi", "giren_sayisi", "cikan_sayisi", "kaynak_dosya"]

# Gerçek takvim (4.1 ölçümü) — sentetik testlerde de bu kullanılıyor ki
# yürürlük türetimi uydurma bir takvime karşı doğrulanmasın.
TAKVIM = [
    ("2025-05-01", "2025-09-30", "2025-04-25"),
    ("2025-10-01", "2026-04-30", "2025-09-24"),
    ("2026-05-01", "2026-09-30", "2026-04-27"),
]


def _kur(d, satirlar, takvim=None):
    d = pathlib.Path(d)
    with open(d / "panel.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=PANEL_BASLIK)
        w.writeheader()
        for r in satirlar:
            w.writerow({k: r.get(k, "") for k in PANEL_BASLIK})
    with open(d / "donem.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=DONEM_BASLIK)
        w.writeheader()
        for bas, bit, duy in (takvim or TAKVIM):
            w.writerow({"donem_baslangic": bas, "donem_bitis": bit,
                        "duyuru_tarihi": duy, "uye_sayisi": "240",
                        "giren_sayisi": "20", "cikan_sayisi": "20",
                        "kaynak_dosya": "x.pdf"})
    return d / "panel.csv", d / "donem.csv"


def _p(ticker, karar, ts, *, yil="2025", periyot="6 Aylık", kodlar="",
       duzeltme="", gelir="1.0", varlik="1.0", borc="1.0", bid="1"):
    return {"ticker": ticker, "karar": karar, "gecerlilik_baslangic": ts,
            "yil": yil, "periyot": periyot, "red_kodlari": kodlar,
            "duzeltme_izi": duzeltme, "gelir_orani": gelir,
            "varlik_orani": varlik, "borc_orani": borc, "bildirim_id": bid,
            "self_check": "GECTI", "gecerli_kayit": "EVET"}


def _uret(d, satirlar, **kw):
    p, dc = _kur(d, satirlar)
    return O.olaylari_uret(p, dc, **kw)


# ===========================================================================
# LOOK-AHEAD — bu dosyanın asıl konusu
# ===========================================================================


def test_look_ahead_girdi_zaman_damgalari_olaydan_once():
    """Her olayın KARAR alanlarını üreten girdiler olay anından ÖNCE olmalı.

    `girdi_ts` boş bırakılırsa denetim boşa döner; o yüzden doluluk da
    ayrıca sınanıyor.
    """
    if not _gercek_veri():
        print("    ATLANDI: panel/referans yok")
        return
    olaylar = O.olaylari_uret(_PANEL, _DONEM)
    assert olaylar, "olay üretilmedi"
    for o in olaylar:
        assert o.girdi_ts, f"{o.ticker} {o.olay_tipi}: girdi_ts BOŞ — denetim boşa döner"
        assert max(o.girdi_ts) <= o.olay_ts, (
            f"{o.ticker} {o.olay_tipi} {o.olay_ts}: girdi {max(o.girdi_ts)} "
            "olaydan SONRA"
        )


def test_look_ahead_nokta_zaman_yeniden_uretim():
    """★ ASIL DENETİM — `girdi_ts`'e GÜVENMEZ, yeniden üretir.

    Her olay için panel o olayın anına kadar kırpılır ve seri baştan
    üretilir. Olayın KARAR alanları birebir aynı çıkmalı: aynı çıkıyorsa
    o olay, üretildiği anda elimizde olan veriden türetilmiştir.

    Bu, `girdi_ts` alanının doğru doldurulduğuna dair bağımsız kanıttır —
    o alan yanlış olsa bile bu test hatayı yakalar.
    """
    if not _gercek_veri():
        print("    ATLANDI: panel/referans yok")
        return
    seri = O.panel_oku(_PANEL)
    takvim = O.takvim_oku(_DONEM)
    tam = O.olay_serisi(seri, takvim)

    KARAR_ALANLARI = ("ticker", "olay_tipi", "olay_ts", "endeks_yururluk_ts",
                      "onceki_karar", "yeni_karar", "red_kodlari",
                      "bildirim_id", "yil", "periyot", "karsi_olay",
                      "g1_teyitsiz", "kilpayi_kriterleri")

    def _imza(o):
        return tuple(getattr(o, a) for a in KARAR_ALANLARI)

    denetlenen = 0
    gercekten_kirpilan = 0
    for o in tam:
        kesik = O.olay_serisi(seri, takvim, kesim=o.olay_ts)
        esler = [k for k in kesik if k.olay_ts == o.olay_ts
                 and k.ticker == o.ticker and k.olay_tipi == o.olay_tipi]
        assert esler, (
            f"{o.ticker} {o.olay_tipi} {o.olay_ts}: olay anına kadarki veriyle "
            "YENİDEN ÜRETİLEMEDİ — geleceğe bakıyor"
        )
        assert len(esler) == 1, (
            f"{o.ticker} {o.olay_tipi} {o.olay_ts}: aynı imzayla {len(esler)} "
            "olay — eşleştirme belirsiz, denetim güvenilmez"
        )
        assert _imza(esler[0]) == _imza(o), (
            f"{o.ticker} {o.olay_tipi} {o.olay_ts}: nokta-zaman üretim farklı\n"
            f"  kesik: {_imza(esler[0])}\n  tam  : {_imza(o)}"
        )
        denetlenen += 1
        if any(r["_ts"] and r["_ts"] > o.olay_ts for r in seri[o.ticker]):
            gercekten_kirpilan += 1
    assert denetlenen == len(tam), (denetlenen, len(tam))

    # Denetimin sessizce boşa dönmediğinin kanıtı.
    #
    # Olayların bir kısmı **yapısal olarak kırpılamaz**: pay kodunun
    # serisindeki son olaydan sonra zaten kayıt yoktur, dolayısıyla
    # kırpma hiçbir şey düşürmez ve o olayda saklanacak gelecek de yoktur.
    # Ölçüldü (5.1 koşusu): 206 olayın 103'ü kırpılabilir, 103'ü serinin
    # sonunda — pay kodu başına olay dağılımı 1:83, 2:43, 3:8, 4:2, 5:1.
    #
    # Eşik ölçülen orana (%50) değil onun altına konuyor: panel derinleştikçe
    # oran değişecek, ama kırpmanın tamamen etkisizleşmesi bir arızadır.
    assert gercekten_kirpilan >= len(tam) // 4, (
        f"olayların yalnız {gercekten_kirpilan}/{len(tam)}'inde kırpma etkili — "
        "denetim büyük ölçüde boşa dönüyor"
    )


def test_look_ahead_takvim_de_kirpildiginda_yururluk_degismiyor():
    """★ Replay testinin KAPATMADIĞI açık: takvim kırpılmıyordu.

    `olay_serisi(kesim=...)` yalnız PANELİ kırpıyor. Takvim iki koşuda da
    aynı kaldığı için, `sonraki_yururluk`'un duyuru filtresi kaldırılsa
    replay testi bunu YAKALAYAMAZDI — iki koşu da aynı yanlış cevabı
    verirdi.

    Burada takvim de olay anına kadar kırpılıyor: yürürlük tarihi
    değişmiyorsa türetim gerçekten yalnız duyurusu geçmiş revizyonlara
    dayanıyor demektir.
    """
    if not _gercek_veri():
        print("    ATLANDI: panel/referans yok")
        return
    seri = O.panel_oku(_PANEL)
    takvim = O.takvim_oku(_DONEM)
    tam = O.olay_serisi(seri, takvim)

    kirpilan_takvim_sayisi = 0
    for o in tam:
        kirpik = O.RevizyonTakvimi(
            tuple(k for k in takvim.kayitlar if k[0] <= o.olay_ts.date())
        )
        if len(kirpik.kayitlar) < len(takvim.kayitlar):
            kirpilan_takvim_sayisi += 1
        kesik = O.olay_serisi(seri, kirpik, kesim=o.olay_ts)
        es = [k for k in kesik if k.olay_ts == o.olay_ts
              and k.ticker == o.ticker and k.olay_tipi == o.olay_tipi]
        assert es, f"{o.ticker} {o.olay_ts}: kırpık takvimle olay üretilemedi"
        assert es[0].endeks_yururluk_ts == o.endeks_yururluk_ts, (
            f"{o.ticker} {o.olay_ts}: yürürlük tarihi GELECEKTEKİ bir "
            f"duyuruya dayanıyor ({es[0].endeks_yururluk_ts} != "
            f"{o.endeks_yururluk_ts})"
        )
    assert kirpilan_takvim_sayisi > 0, (
        "hiçbir olayda takvim kırpılmadı — bu denetim boşa döndü"
    )


def test_look_ahead_olgunluk_alanlari_ileriye_donuk_ve_izole():
    """Olgunluk alanları BİLİNÇLİ olarak ileriye dönüktür — ve karar
    alanlarını etkilemez.

    `kesinlesme_ts` olay anına göre gelecektedir (sonraki dönemin yayını).
    Bunu saklamak look-ahead DEĞİLDİR: backtester `kesinlik(t)` çağırıp
    kendi saatiyle karşılaştırır. Ama karar alanlarına sızarsa öyle olur.
    """
    if not _gercek_veri():
        print("    ATLANDI: panel/referans yok")
        return
    seri = O.panel_oku(_PANEL)
    takvim = O.takvim_oku(_DONEM)
    olaylar = O.olay_serisi(seri, takvim)

    for o in olaylar:
        if o.kesinlesme_ts:
            assert o.kesinlesme_ts > o.olay_ts, (
                f"{o.ticker}: kesinlesme_ts olaydan önce/eşit — anlamsız"
            )
        assert o.olgunlasma_ts == o.olay_ts + timedelta(
            days=O.olgunlasma_penceresi(o.karsi_olay)
        )
        # Olgunluk alanları karar girdilerine karışmamış olmalı.
        assert o.kesinlesme_ts not in o.girdi_ts

    # Kesim uygulandığında karar alanları değişmiyor ama kesinlesme_ts
    # doğal olarak boşalıyor: ileriye dönük bilgi kesimden sonra yok.
    ornek = next(o for o in olaylar if o.kesinlesme_ts)
    kesik = O.olay_serisi(seri, takvim, kesim=ornek.olay_ts)
    es = next(k for k in kesik if k.bildirim_id == ornek.bildirim_id
              and k.olay_tipi == ornek.olay_tipi)
    assert es.kesinlesme_ts is None
    assert (es.olay_tipi, es.yeni_karar) == (ornek.olay_tipi, ornek.yeni_karar)


def test_look_ahead_kesinlik_zamana_gore_ilerliyor():
    """`kesinlik` etiketi saklanmıyor, `an`'a göre hesaplanıyor."""
    t = datetime(2025, 8, 18, 19, 0)
    o = O.Olay(ticker="AAA", olay_tipi=O.UYGUNLUK_KAYBI, olay_ts=t,
               endeks_yururluk_ts=date(2025, 10, 1), onceki_karar="UYGUN",
               yeni_karar="UYGUN_DEGIL", red_kodlari="", bildirim_id="1",
               yil="2025", periyot="6 Aylık", duzeltme_izi="",
               olgunlasma_ts=t + timedelta(days=O.DUZELTME_P95_GUN),
               kesinlesme_ts=datetime(2026, 3, 4, 18, 0))
    assert o.kesinlik(t) == O.KESINLIK_HAM
    assert o.kesinlik(t + timedelta(days=37)) == O.KESINLIK_HAM
    assert o.kesinlik(t + timedelta(days=38)) == O.KESINLIK_OLGUN
    assert o.kesinlik(datetime(2026, 3, 4, 18, 0)) == O.KESINLIK_KESIN


def test_zaman_damgasiz_kayit_olay_uretmiyor():
    """Olayın zamanı `gonderim_ts`'tir (spec §5.1); uydurulamaz."""
    with tempfile.TemporaryDirectory() as d:
        olaylar = _uret(d, [
            _p("AAA", "UYGUN", "2025-08-18 19:00:00"),
            _p("AAA", "UYGUN_DEGIL", "", yil="2025", periyot="Yıllık"),
        ])
    assert all(o.olay_ts is not None for o in olaylar)
    assert not [o for o in olaylar if o.yeni_karar == "UYGUN_DEGIL"]


# ===========================================================================
# Olay tipleri
# ===========================================================================


def test_dort_gecis_tipi():
    plan = [
        ("UYGUN", "UYGUN_DEGIL", O.UYGUNLUK_KAYBI),
        ("UYGUN_DEGIL", "UYGUN", O.UYGUNLUK_KAZANIMI),
        ("UYGUN", "TOLERANSTA", O.TOLERANSA_DUSUS),
        ("TOLERANSTA", "UYGUN", O.TOLERANSTAN_CIKIS),
        ("TOLERANSTA", "UYGUN_DEGIL", O.UYGUNLUK_KAYBI),
        ("UYGUN_DEGIL", "TOLERANSTA", O.UYGUNLUK_KAZANIMI),
    ]
    for onceki, yeni, bek in plan:
        assert O._gecis_tipi(onceki, yeni) == bek, (onceki, yeni)
    assert O._gecis_tipi("UYGUN", "UYGUN") is None
    # İkisi de olumsuz: uygunluk yönü değişmedi, olay yok.
    assert O._gecis_tipi("UYGUN_DEGIL", "BELIRSIZ") is None


def test_ilk_kayit_gecis_olayi_uretmiyor():
    """İlk gözlem bir DEĞİŞİM değildir; 539 sahte 'kazanım' üretmemeli."""
    with tempfile.TemporaryDirectory() as d:
        olaylar = _uret(d, [_p("AAA", "UYGUN", "2025-08-18 19:00:00")])
    assert [o.olay_tipi for o in olaylar] == []


def test_kilpayi_esigi_thy_vakasi():
    """THY 2025: gelir %4,92, limit %5 — kılpayı bu vaka için var."""
    with tempfile.TemporaryDirectory() as d:
        olaylar = _uret(d, [_p("THYAO", "UYGUN", "2025-08-18 19:00:00",
                               gelir="4.92")])
    assert [o.olay_tipi for o in olaylar] == [O.KILPAYI_UYARI]
    assert "gelir=4.92" in olaylar[0].kilpayi_kriterleri


def test_kilpayi_limiti_asan_orani_kapsamiyor():
    """Aşan oran zaten kendi kapısından olay üretiyor; kılpayı ÖNCESİDİR."""
    with tempfile.TemporaryDirectory() as d:
        olaylar = _uret(d, [_p("AAA", "UYGUN_DEGIL", "2025-08-18 19:00:00",
                               gelir="5.4")])
    assert not [o for o in olaylar if o.olay_tipi == O.KILPAYI_UYARI]


def test_kilpayi_bandi_uc_kriterde_de_calisiyor():
    with tempfile.TemporaryDirectory() as d:
        olaylar = _uret(d, [_p("AAA", "UYGUN", "2025-08-18 19:00:00",
                               gelir="4.6", varlik="32.7", borc="32.51")])
    assert len(olaylar) == 1
    k = olaylar[0].kilpayi_kriterleri
    assert "gelir=4.6" in k and "varlik=32.7" in k and "borc=32.51" in k


def test_kilpayi_tekrar_etmiyor():
    """Uyarı bir DURUM değil OLAY: açıkken her kayıtta yeniden üretilmez."""
    with tempfile.TemporaryDirectory() as d:
        olaylar = _uret(d, [
            _p("AAA", "UYGUN", "2025-08-18 19:00:00", gelir="4.9"),
            _p("AAA", "UYGUN", "2026-03-04 18:00:00", gelir="4.8",
               yil="2025", periyot="Yıllık"),
        ])
    assert [o.olay_tipi for o in olaylar] == [O.KILPAYI_UYARI]


def test_kilpayi_esigi_olculmus_sabitten():
    assert O.KILPAYI_ESIK == Decimal("0.5")


# ===========================================================================
# Düzeltme: İPTAL YOK, KARŞI OLAY
# ===========================================================================


def test_duzeltme_olayi_iptal_etmiyor_karsi_olay_uretiyor():
    """Eski olay YERİNDE KALIR; düzeltme kendi anıyla ters olay üretir.

    Bir olayı sonradan silmek look-ahead'a davetiyedir: o sinyal gerçekten
    yayımlanmış ve işlem yapılabilir durumdaydı.
    """
    with tempfile.TemporaryDirectory() as d:
        olaylar = _uret(d, [
            _p("AAA", "UYGUN", "2025-08-08 18:00:00", bid="1"),
            _p("AAA", "UYGUN_DEGIL", "2025-08-19 18:00:00", bid="2",
               yil="2025", periyot="Yıllık"),
            # AYNI dönemin düzeltmesi: kararı geri çeviriyor
            _p("AAA", "UYGUN", "2025-09-05 18:00:00", bid="3",
               yil="2025", periyot="Yıllık", duzeltme="DUZENLENEN"),
        ])
    tipler = [(o.olay_tipi, o.karsi_olay, o.bildirim_id) for o in olaylar]
    assert tipler == [
        (O.UYGUNLUK_KAYBI, False, "2"),
        (O.UYGUNLUK_KAZANIMI, True, "3"),
    ], tipler
    # İlk olay silinmedi ve zamanı değişmedi.
    assert olaylar[0].olay_ts == datetime(2025, 8, 19, 18, 0)


def test_karari_degistirmeyen_duzeltme_olay_uretmiyor():
    with tempfile.TemporaryDirectory() as d:
        olaylar = _uret(d, [
            _p("AAA", "UYGUN", "2025-08-08 18:00:00", bid="1"),
            _p("AAA", "UYGUN", "2025-09-05 18:00:00", bid="2",
               duzeltme="DUZENLENEN"),
        ])
    assert olaylar == []


def test_g1_teyitsiz_yalniz_duzeltilmemis_olumlu_kararda():
    """2.3: karar çeviren 14 düzeltmenin 9'u b1_1/b1_2, 7'si False->True.

    İlk bildirimin 'G1 temiz' demesi, düzeltilmişin aynı şeyi demesinden
    zayıf kanıttır.
    """
    with tempfile.TemporaryDirectory() as d:
        olaylar = _uret(d, [
            _p("AAA", "UYGUN_DEGIL", "2025-08-08 18:00:00", bid="1"),
            _p("AAA", "UYGUN", "2025-08-19 18:00:00", bid="2",
               yil="2025", periyot="Yıllık"),
            _p("AAA", "UYGUN_DEGIL", "2025-09-05 18:00:00", bid="3",
               yil="2025", periyot="Yıllık", duzeltme="DUZENLENEN"),
            _p("AAA", "UYGUN", "2025-09-20 18:00:00", bid="4",
               yil="2025", periyot="Yıllık", duzeltme="DUZENLENEN"),
        ])
    d_ = {o.bildirim_id: o.g1_teyitsiz for o in olaylar}
    assert d_["2"] is True, "düzeltilmemiş olumlu karar işaretlenmeli"
    assert d_["3"] is False, "olumsuz karar işaretlenmemeli"
    assert d_["4"] is False, "düzeltmeyle teyit edilmiş olumlu karar işaretlenmez"


# ===========================================================================
# Endeks yürürlük türetimi
# ===========================================================================


def test_yururluk_duyurusu_gecmis_revizyondan_tureniyor():
    t = O.takvim_oku_yardimci()
    # 18.08.2025: son duyuru 25.04.2025 (dönem 01.05-30.09) -> sonraki 01.10
    assert t.sonraki_yururluk(datetime(2025, 8, 18)) == date(2025, 10, 1)
    # 06.03.2026: son duyuru 24.09.2025 (dönem 01.10-30.04) -> sonraki 01.05
    assert t.sonraki_yururluk(datetime(2026, 3, 6)) == date(2026, 5, 1)


def test_yururluk_duyurudan_sonraki_kafif_bir_sonraki_revizyona_gidiyor():
    """28.09.2025'te yayımlanan form, 24.09'da DUYURULMUŞ 01.10 listesini
    etkileyemez — doğru cevap 01.05.2026.

    Yürürlük tarihine bakan naif bir kural burada 01.10.2025 derdi ve
    sahte bir öncüllük ölçerdi.
    """
    t = O.takvim_oku_yardimci()
    assert t.sonraki_yururluk(datetime(2025, 9, 28)) == date(2026, 5, 1)


def test_takvimden_once_yururluk_uydurulmuyor():
    t = O.takvim_oku_yardimci()
    assert t.sonraki_yururluk(datetime(2020, 1, 1)) is None


def test_duyurusuz_donem_hata_firlatiyor():
    """Kural 7: duyuru yoksa sessizce yürürlüğe düşülmez."""
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        with open(d / "donem.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=DONEM_BASLIK)
            w.writeheader()
            w.writerow({"donem_baslangic": "2026-05-01",
                        "donem_bitis": "2026-09-30", "duyuru_tarihi": "",
                        "uye_sayisi": "243", "giren_sayisi": "27",
                        "cikan_sayisi": "19", "kaynak_dosya": "x.pdf"})
        try:
            O.takvim_oku(d / "donem.csv")
        except O.OlayGirdisiYok:
            return
    raise AssertionError("duyurusuz dönem hata fırlatmadı")


def test_panel_satirsizsa_hata_firlatiyor():
    """'Olay yok' ile 'panel okunamadı' ayrı (kural 7)."""
    with tempfile.TemporaryDirectory() as d:
        p, _dc = _kur(d, [])
        try:
            O.panel_oku(p)
        except O.OlayGirdisiYok:
            return
    raise AssertionError("satırsız panel sessizce boş döndü")


# ===========================================================================
# Ölçülmüş eşikler
# ===========================================================================


def test_duzeltme_esikleri_olcumden_geliyor():
    """2.3 ölçümü (n=181): medyan 21 · p90 35 · p95 38 · max 55.

    Gevşetilirse olgunluk etiketi gerçeğinden erken 'güvenli' der.
    """
    assert O.DUZELTME_MEDYAN_GUN == 21
    assert O.DUZELTME_P95_GUN == 38
    assert O.DUZELTME_MAX_GUN == 55
    assert O.KARAR_CEVIREN_MAX_GUN == 31


# ===========================================================================
# Gerçek veri kademesi
# ===========================================================================


def _gercek_veri() -> bool:
    return _PANEL.exists() and _DONEM.exists()


def test_gercek_kosu_olculen_sayilar():
    if not _gercek_veri():
        print("    ATLANDI: panel/referans yok")
        return
    olaylar = O.olaylari_uret(_PANEL, _DONEM)
    o = O.ozet(olaylar, datetime(2026, 8, 11))
    for k, v in OLCULEN.items():
        assert o[k] == v, (k, o[k], v)


def test_gercek_dogub_pencere_olcumu():
    """DOGUB 2026/6 Aylık 30.07.2026 -> 01.10.2026 = 63 gün (görev metni)."""
    if not _gercek_veri():
        print("    ATLANDI: panel/referans yok")
        return
    olaylar = O.olaylari_uret(_PANEL, _DONEM)
    d = [o for o in olaylar if o.ticker == "DOGUB" and o.yil == "2026"]
    assert d, "DOGUB 2026 olayı yok"
    o = d[0]
    assert o.olay_ts.date() == date(2026, 7, 30), o.olay_ts
    assert o.endeks_yururluk_ts == date(2026, 10, 1), o.endeks_yururluk_ts
    assert (o.endeks_yururluk_ts - o.olay_ts.date()).days == 63


def test_gercek_karsi_olaylar_daha_gec_geliyor():
    """Karşı olaylar ilk bildirimlerden GEÇ gelir ama penceresi kapanmaz.

    5.1 ilk yazımında karşı olayın temiz penceresi −10 gün ölçülmüştü;
    o **yanlış eşiğin artefaktıydı** (ilk bildirimin 38 günü karşı olaya
    uygulanıyordu). Doğru eşikle (22 gün) pencere pozitife dönüyor.
    """
    if not _gercek_veri():
        print("    ATLANDI: panel/referans yok")
        return
    olaylar = O.olaylari_uret(_PANEL, _DONEM)
    ilk = sorted((o.endeks_yururluk_ts - o.olay_ts.date()).days
                 for o in olaylar if not o.karsi_olay and o.endeks_yururluk_ts)
    karsi = sorted((o.endeks_yururluk_ts - o.olay_ts.date()).days
                   for o in olaylar if o.karsi_olay and o.endeks_yururluk_ts)
    assert ilk and karsi
    assert ilk[len(ilk) // 2] > karsi[len(karsi) // 2], (
        "karşı olayların medyan öncüllüğü ilk bildirimlerden küçük olmalı"
    )
    # Doğru eşikle karşı olayda da temiz pencere kalıyor.
    temiz = karsi[len(karsi) // 2] - O.IKINCI_DUZELTME_P95_GUN
    assert temiz > 0, f"karşı olay temiz penceresi {temiz} gün"


def test_olgunlasma_esigi_olay_tipine_duyarli():
    """★ (a) — karşı olay AYRI bir dağılımdan eşik alır.

    38 gün ilk-bildirimden-ilk-düzeltmeye p95'i. Karşı olay zaten bir
    düzeltmedir; riski "ikinci düzeltme gelir mi" ve o dağılım ayrı:
    163 düzeltme grubunun 16'sında (%9,8) ikinci düzeltme var, ilk→ikinci
    gecikme medyan 4 · p95 22 · max 22.
    """
    assert O.olgunlasma_penceresi(False) == O.DUZELTME_P95_GUN == 38
    assert O.olgunlasma_penceresi(True) == O.IKINCI_DUZELTME_P95_GUN == 22
    assert O.IKINCI_DUZELTME_MEDYAN_GUN == 4
    assert O.IKINCI_DUZELTME_MAX_GUN == 22
    assert abs(O.IKINCI_DUZELTME_ORANI - 0.098) < 1e-9


def test_karsi_olay_daha_erken_olgunlasiyor():
    """Aynı anda yayımlanan iki olaydan karşı olan 16 gün önce olgunlaşır."""
    with tempfile.TemporaryDirectory() as d:
        olaylar = _uret(d, [
            _p("AAA", "UYGUN", "2025-08-08 18:00:00", bid="1"),
            _p("AAA", "UYGUN_DEGIL", "2025-08-19 18:00:00", bid="2",
               yil="2025", periyot="Yıllık"),
            _p("AAA", "UYGUN", "2025-09-05 18:00:00", bid="3",
               yil="2025", periyot="Yıllık", duzeltme="DUZENLENEN"),
        ])
    ilk = next(o for o in olaylar if not o.karsi_olay)
    karsi = next(o for o in olaylar if o.karsi_olay)
    assert (ilk.olgunlasma_ts - ilk.olay_ts).days == 38
    assert (karsi.olgunlasma_ts - karsi.olay_ts).days == 22


def test_gercek_ikinci_duzeltme_dagilimi_dondu():
    """Eşik ölçümden geliyor: panelden yeniden hesaplanıp doğrulanıyor.

    Sabit değişirse bu test kırılır ve sebebi araştırılır — eşiği
    'testi geçirmek için' güncellemek yasaktır (kural 1'in ruhu).
    """
    if not _gercek_veri():
        print("    ATLANDI: panel yok")
        return
    import collections
    gruplar = collections.defaultdict(list)
    with open(_PANEL, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["gecerlilik_baslangic"]:
                gruplar[(r["ticker"], r["yil"], r["periyot"])].append(
                    datetime.strptime(r["gecerlilik_baslangic"],
                                      "%Y-%m-%d %H:%M:%S"))
    for v in gruplar.values():
        v.sort()
    coklu = [v for v in gruplar.values() if len(v) > 1]
    ucuncu = [v for v in gruplar.values() if len(v) > 2]
    assert len(coklu) == 163, len(coklu)
    assert len(ucuncu) == 16, len(ucuncu)
    gecikme = sorted((v[2] - v[1]).days for v in ucuncu)
    assert max(gecikme) == O.IKINCI_DUZELTME_MAX_GUN
    assert gecikme[len(gecikme) // 2] == O.IKINCI_DUZELTME_MEDYAN_GUN


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
