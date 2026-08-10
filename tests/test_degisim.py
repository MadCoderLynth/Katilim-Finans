"""Değişim bazlı mutabakat testleri — ağa çıkmaz (Faz 4.2).

4.0 DURUMU karşılaştırıyordu; burada karşılaştırılan **DEĞİŞİM**. Örneklem
yalnız giriş/çıkış olayları: resmî liste değiştiğinde bizim de değişip
değişmediğimiz. Kararlı vakalar dışarıda, çünkü orada yarım çalışan bir
motor da uyuşur.

İki kademe (`test_pilot.py` disipliniyle):

1. **Fixture kademesi (her zaman):** sınıflandırma, yön, ön teşhis ve
   payda kuralları sentetik veriyle donduruluyor.
2. **Gerçek veri kademesi (referans + panel varsa):** 4.2 koşusunun
   ölçtüğü sayılar donduruluyor. Dosyalar yoksa test **atlandığını
   duyurur**, sessizce geçmez.
"""
import csv
import pathlib
import sys
import tempfile
import traceback
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from katilim import mutabakat as M  # noqa: E402

KOK = pathlib.Path(__file__).resolve().parents[1]
_DONEM_CSV = KOK / "veri" / "referans" / "xktum_donemler.csv"
_OLAY_CSV = KOK / "veri" / "referans" / "xktum_olaylar.csv"
_PANEL_CSV = KOK / "veri" / "panel" / "panel.csv"
_DUZELTME_CSV = KOK / "veri" / "panel" / "duzeltme_olaylari.csv"

# 4.2 koşusunun ölçtüğü sayılar. Değişirse bu bir BULGUDUR — sayı
# güncellenmeden önce sebebi araştırılır.
OLCULEN = {
    "2025-10": {"olay": 52, "eslesti": 49, "gorus_yok": 3, "uyusmazlik": 0},
    "2026-05": {"olay": 46, "eslesti": 46, "gorus_yok": 0, "uyusmazlik": 0},
}

PANEL_BASLIK = ["ticker", "yil", "periyot", "gecerlilik_baslangic", "karar",
                "red_kodlari", "onceki_donem_tolerans", "self_check",
                "bildirim_id", "gecerli_kayit"]
DONEM_BASLIK = ["donem_baslangic", "donem_bitis", "duyuru_tarihi",
                "uye_sayisi", "giren_sayisi", "cikan_sayisi", "kaynak_dosya"]
OLAY_BASLIK = ["ticker", "donem_baslangic", "olay", "kaynak_dosya"]


def _kur(d, panel, olaylar, donemler=None):
    d = pathlib.Path(d)
    donemler = donemler or [
        {"donem_baslangic": "2025-05-01", "donem_bitis": "2025-09-30",
         "duyuru_tarihi": "2025-04-25", "uye_sayisi": "241",
         "giren_sayisi": "21", "cikan_sayisi": "36", "kaynak_dosya": "a.pdf"},
        {"donem_baslangic": "2025-10-01", "donem_bitis": "2026-04-30",
         "duyuru_tarihi": "2025-09-24", "uye_sayisi": "235",
         "giren_sayisi": "23", "cikan_sayisi": "29", "kaynak_dosya": "b.pdf"},
    ]
    for ad, basliklar, veri in (("panel.csv", PANEL_BASLIK, panel),
                                ("donem.csv", DONEM_BASLIK, donemler),
                                ("olay.csv", OLAY_BASLIK, olaylar)):
        with open(d / ad, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=basliklar)
            w.writeheader()
            for r in veri:
                w.writerow({k: r.get(k, "") for k in basliklar})
    return d / "panel.csv", d / "donem.csv", d / "olay.csv"


def _p(ticker, karar, ts, **kw):
    r = {"ticker": ticker, "karar": karar, "gecerlilik_baslangic": ts,
         "yil": "2025", "periyot": "6 Aylık", "red_kodlari": "",
         "self_check": "GEÇTİ", "onceki_donem_tolerans": "HAYIR",
         "bildirim_id": "1", "gecerli_kayit": "EVET"}
    r.update(kw)
    return r


def _o(ticker, olay, donem="2025-10-01"):
    return {"ticker": ticker, "donem_baslangic": donem, "olay": olay,
            "kaynak_dosya": "b.pdf"}


def _kosla(d, panel, olaylar, evren=None, donem="2025-10"):
    p, dc, oc = _kur(d, panel, olaylar)
    return M.karsilastir_degisim(
        panel_csv=p, donem=donem,
        evren_tickerlari=evren if evren is not None else {"AAA", "BBB", "CCC"},
        donem_csv=dc, olay_csv=oc,
    )


# --- Dört hücre ------------------------------------------------------------


def test_cikan_uygun_dersek_yanlis_pozitif():
    """En pahalı hata: BIST çıkardı, biz UYGUN diyoruz."""
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("AAA", "UYGUN", "2025-08-10 10:00:00")],
                   [_o("AAA", "CIKAN")])
    assert m.olaylar[0].sinif == M.SINIF_YANLIS_POZITIF
    assert m.yanlis_pozitifler and m.olaylar[0].uyusmazlik
    assert m.matris()[("UYGUN", "DISARIDA")] == 1


def test_giren_uygun_degil_dersek_yanlis_negatif():
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("AAA", "UYGUN_DEGIL", "2025-08-10 10:00:00")],
                   [_o("AAA", "GIREN")])
    assert m.olaylar[0].sinif == M.SINIF_YANLIS_NEGATIF
    assert not m.yanlis_pozitifler          # yanlış negatif ayrı tutuluyor
    assert m.olaylar[0].uyusmazlik


def test_dogru_iki_hucre_eslesti():
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("AAA", "UYGUN", "2025-08-10 10:00:00"),
                       _p("BBB", "UYGUN_DEGIL", "2025-08-10 10:00:00")],
                   [_o("AAA", "GIREN"), _o("BBB", "CIKAN")])
    assert [o.sinif for o in m.olaylar] == [M.SINIF_ESLESTI, M.SINIF_ESLESTI]
    assert m.uyusmazlik_orani()[0] == 0.0


def test_toleransta_uygun_sayiliyor():
    """TOLERANSTA hâlâ endekste kalmayı sağlayan bir karardır."""
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("AAA", "TOLERANSTA", "2025-08-10 10:00:00")],
                   [_o("AAA", "GIREN")])
    assert m.olaylar[0].sinif == M.SINIF_ESLESTI


# --- Kesim noktası ve look-ahead -------------------------------------------


def test_kesim_noktasindan_sonraki_kayit_gorulmez():
    """Duyurudan (24.09.2025) SONRA yayımlanan KAFİF o revizyonu etkileyemez.

    Bu look-ahead disiplininin mutabakat karşılığı: yürürlük tarihini
    kullansaydık 25–30 Eylül'de gelen beyan BIST'e atfedilirdi.
    """
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("AAA", "UYGUN_DEGIL", "2025-08-10 10:00:00"),
                       _p("AAA", "UYGUN", "2025-09-28 10:00:00")],
                   [_o("AAA", "CIKAN")])
    o = m.olaylar[0]
    assert o.simdiki_karar == "UYGUN_DEGIL", "kesimden sonraki kayıt sızdı"
    assert o.sinif == M.SINIF_ESLESTI


def test_gecersiz_kilinmis_kayit_kendi_penceresinde_gecerli():
    """Bugün geçersiz kılınmış bir kayıt, o günkü kesimde canlı etiketti.

    `gecerli_kayit` süzgeci uygulanmıyor ve bu bilinçli.
    """
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("AAA", "UYGUN_DEGIL", "2025-08-10 10:00:00",
                          gecerli_kayit="HAYIR"),
                       _p("AAA", "UYGUN", "2026-03-01 10:00:00")],
                   [_o("AAA", "CIKAN")])
    assert m.olaylar[0].simdiki_karar == "UYGUN_DEGIL"


# --- Yön (B kademesi) ------------------------------------------------------


def test_yon_ayni_yonde_degisim():
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("AAA", "UYGUN", "2025-04-01 10:00:00"),
                       _p("AAA", "UYGUN_DEGIL", "2025-08-10 10:00:00")],
                   [_o("AAA", "CIKAN")])
    assert m.olaylar[0].yon == M.YON_AYNI


def test_yon_olculemez_veri_yoksa_eslesmeme_sayilmaz():
    """Önceki kesimde kaydımız yoksa yön ÖLÇÜLEMEZ — 'eşleşmedi' değil.

    Eksik veriyi hipotez hatası gibi göstermek kural 2'nin ihlali olurdu.
    """
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("AAA", "UYGUN_DEGIL", "2025-08-10 10:00:00")],
                   [_o("AAA", "CIKAN")])
    o = m.olaylar[0]
    assert o.yon == M.YON_OLCULEMEZ
    assert o.sinif == M.SINIF_ESLESTI       # A kademesi yine de tuttu
    assert not o.uyusmazlik


def test_yon_degisim_yok_erken_karar():
    """Kararımız sınırın iki yanında aynıysa: biz BIST'ten erken davrandık."""
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("AAA", "UYGUN", "2025-04-01 10:00:00"),
                       _p("AAA", "UYGUN", "2025-08-10 10:00:00")],
                   [_o("AAA", "GIREN")])
    assert m.olaylar[0].yon == M.YON_DEGISIM_YOK


# --- Kapsam, olağanüstü çıkarma, payda -------------------------------------


def test_olagenustu_cikarma_uyusmazlik_sayilmiyor():
    """Bugünkü evrende olmayan kodun çıkışı kotasyon iptali olabilir.

    4.1 sınırı: olağanüstü çıkarmalar dönemsel PDF'lerde görünmüyor.
    Uyuşmazlık saymadan ÖNCE ayrı sınıflanıyor.
    """
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("SILINMIS", "UYGUN", "2025-08-10 10:00:00")],
                   [_o("SILINMIS", "CIKAN")], evren={"AAA"})
    o = m.olaylar[0]
    assert o.sinif == M.SINIF_OLAGANUSTU
    assert not o.uyusmazlik
    assert m.uyusmazlik_orani()[2] == 0, "olağanüstü çıkarma paydaya girdi"


def test_kapsam_karari_gorus_yok():
    for karar in ("BEYAN_YOK", "KAPSAM_DISI", "BELIRSIZ", "AYIRT_EDILEMEDI"):
        with tempfile.TemporaryDirectory() as d:
            m = _kosla(d, [_p("AAA", karar, "2025-08-10 10:00:00")],
                       [_o("AAA", "GIREN")])
        assert m.olaylar[0].sinif == M.SINIF_GORUS_YOK, karar


def test_panelde_kayit_yoksa_gorus_yok():
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("BBB", "UYGUN", "2025-08-10 10:00:00")],
                   [_o("AAA", "GIREN")])
    assert m.olaylar[0].sinif == M.SINIF_GORUS_YOK
    assert m.olaylar[0].simdiki_karar is None


def test_payda_yalniz_gorusu_olan_olaylar():
    """`GORUS_YOK` paydaya girerse oran sahte biçimde DÜŞER (4.0 dersi)."""
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("AAA", "UYGUN", "2025-08-10 10:00:00"),
                       _p("BBB", "BEYAN_YOK", "2025-08-10 10:00:00")],
                   [_o("AAA", "CIKAN"), _o("BBB", "CIKAN")])
    oran, k, n = m.uyusmazlik_orani()
    assert (k, n) == (1, 1) and oran == 1.0, (k, n, oran)


# --- Ön teşhis -------------------------------------------------------------


def test_teshis_self_check_kalirsa_parser_suphesi():
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("AAA", "UYGUN", "2025-08-10 10:00:00",
                          self_check="KALDI", red_kodlari="G5_GELIR")],
                   [_o("AAA", "CIKAN")])
    o = m.olaylar[0]
    assert "parser" in o.on_teshis, o.on_teshis
    assert o.hipotez == "—", "self-check kalmışken hipoteze atlanmamalı"


def test_teshis_kapi_hipoteze_esleniyor():
    for kod, hip in (("G4_DOGRUDAN_AYKIRI", "H1"), ("G2_IMTIYAZ", "H2"),
                     ("G5_GELIR", "H3"), ("G6_VARLIK", "H3"),
                     ("G7_BORC", "H3"), ("G1_ESAS_SOZLESME", "—")):
        with tempfile.TemporaryDirectory() as d:
            m = _kosla(d, [_p("AAA", "UYGUN_DEGIL", "2025-08-10 10:00:00",
                              red_kodlari=kod)], [_o("AAA", "CIKAN")])
        assert m.olaylar[0].hipotez == hip, (kod, m.olaylar[0].hipotez)


def test_teshis_tolerans_zinciri_h4():
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("AAA", "UYGUN_DEGIL", "2025-08-10 10:00:00",
                          red_kodlari="G7_BORC",
                          onceki_donem_tolerans="EVET")],
                   [_o("AAA", "CIKAN")])
    assert m.olaylar[0].hipotez == "H4", m.olaylar[0].on_teshis


def test_hipotez_ozeti_sinanmayani_gostermiyor():
    """Hiç olay karara bağlamayan hipotez tabloda GÖRÜNMEZ — sınanmamıştır."""
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_p("AAA", "UYGUN_DEGIL", "2025-08-10 10:00:00",
                          red_kodlari="G4_DOGRUDAN_AYKIRI")],
                   [_o("AAA", "CIKAN")])
    ozet = M.hipotez_ozeti(m)
    assert "H1" in ozet and ozet["H1"]["olay"] == 1
    assert "H2" not in ozet


# --- Kural 7 ---------------------------------------------------------------


def test_bilinmeyen_donem_hata_firlatiyor():
    with tempfile.TemporaryDirectory() as d:
        p, dc, oc = _kur(d, [_p("AAA", "UYGUN", "2025-08-10 10:00:00")],
                         [_o("AAA", "GIREN")])
        try:
            M.karsilastir_degisim(panel_csv=p, donem="2099-01",
                                  evren_tickerlari={"AAA"},
                                  donem_csv=dc, olay_csv=oc)
        except M.MutabakatGirdisiYok:
            return
    raise AssertionError("bilinmeyen dönem sessizce kabul edildi")


def test_olaysiz_donem_bos_sonuc_donmuyor():
    """'Hiç değişim yok' ile 'tabloyu okuyamadım' ayrı (kural 7)."""
    with tempfile.TemporaryDirectory() as d:
        p, dc, oc = _kur(d, [_p("AAA", "UYGUN", "2025-08-10 10:00:00")],
                         [_o("AAA", "GIREN", donem="2025-05-01")])
        try:
            M.karsilastir_degisim(panel_csv=p, donem="2025-10",
                                  evren_tickerlari={"AAA"},
                                  donem_csv=dc, olay_csv=oc)
        except M.MutabakatGirdisiYok:
            return
    raise AssertionError("olaysız dönem sessizce boş döndü")


# --- Düzeltme izi ----------------------------------------------------------


def test_duzeltme_yonu_tek_evet_eleyicidir():
    """G1-G4 'herhangi biri EVET' mantığı: tek `-> True` eleyicidir."""
    assert M._duzeltme_yonu("b1_1: False -> True") == "ELEYEN"
    assert M._duzeltme_yonu("b4_3: True -> False") == "TEMIZLEYEN"
    assert M._duzeltme_yonu("b1_1: True -> False; b1_2: False -> True") == "ELEYEN"


def test_duzeltme_izi_simetrik_ve_sirali():
    """Eleyen düzeltme ÇIKIŞ, temizleyen GİRİŞ bekler; sıra şartı zorunlu."""
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        _, dc, oc = _kur(d, [_p("AAA", "UYGUN", "2025-08-10 10:00:00")], [
            _o("ASUZU", "CIKAN"), _o("TARKM", "GIREN"),
            _o("BORLS", "CIKAN"),
        ])
        y = d / "duz.csv"
        with open(y, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=[
                "ticker", "yil", "periyot", "degisen_beyanlar",
                "duzeltme_gonderim_ts", "karar_ceviren_beyan"])
            w.writeheader()
            w.writerows([
                # eleyen, çıkıştan ÖNCE -> eşleşir
                {"ticker": "ASUZU", "yil": "2025", "periyot": "6 Aylık",
                 "degisen_beyanlar": "b1_1: False -> True",
                 "duzeltme_gonderim_ts": "2025-09-02 18:47:48",
                 "karar_ceviren_beyan": "EVET"},
                # temizleyen, girişten ÖNCE -> eşleşir (simetrik yarı)
                {"ticker": "TARKM", "yil": "2025", "periyot": "6 Aylık",
                 "degisen_beyanlar": "b1_2: True -> False",
                 "duzeltme_gonderim_ts": "2025-09-01 10:00:00",
                 "karar_ceviren_beyan": "EVET"},
                # düzeltme çıkıştan SONRA -> sayılmaz (BORLS örüntüsü)
                {"ticker": "BORLS", "yil": "2025", "periyot": "Yıllık",
                 "degisen_beyanlar": "b1_1: False -> True",
                 "duzeltme_gonderim_ts": "2026-04-08 00:11:38",
                 "karar_ceviren_beyan": "EVET"},
                # kararı çevirmeyen -> hiç bakılmaz
                {"ticker": "ZZZ", "yil": "2025", "periyot": "Yıllık",
                 "degisen_beyanlar": "", "duzeltme_gonderim_ts":
                 "2025-09-01 10:00:00", "karar_ceviren_beyan": "HAYIR"},
            ])
        r = M.duzeltme_olay_eslemesi(y, olay_csv=oc, donem_csv=dc)
    assert r["karar_ceviren_duzeltme"] == 3
    assert r["eslesen"] == 2, r["eslesen_kayitlar"]
    assert r["ters_yon"] == 0
    assert r["olay_duzeltmeden_once"] == 1, r["sonradan_kayitlar"]
    assert {e["ticker"] for e in r["eslesen_kayitlar"]} == {"ASUZU", "TARKM"}


# --- Gerçek veri kademesi --------------------------------------------------


def _gercek_veri_var() -> bool:
    return all(y.exists() for y in
               (_DONEM_CSV, _OLAY_CSV, _PANEL_CSV, _DUZELTME_CSV))


def test_gercek_kosu_olculen_sayilari_veriyor():
    if not _gercek_veri_var():
        print("    ATLANDI: referans/panel dosyaları yok — "
              "4.2 ölçümü SINANMADI")
        return
    evren = set()
    with open(KOK / "veri" / "evren" / "sirketler.csv",
              encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            evren.add(r["ticker"].strip())
    for donem, bek in OLCULEN.items():
        m = M.karsilastir_degisim(
            panel_csv=_PANEL_CSV, donem=donem, evren_tickerlari=evren,
            donem_csv=_DONEM_CSV, olay_csv=_OLAY_CSV)
        d = m.sinif_dagilimi()
        assert len(m.olaylar) == bek["olay"], (donem, len(m.olaylar))
        assert d.get(M.SINIF_ESLESTI, 0) == bek["eslesti"], (donem, d)
        assert d.get(M.SINIF_GORUS_YOK, 0) == bek["gorus_yok"], (donem, d)
        assert len(m.uyusmazliklar) == bek["uyusmazlik"], (donem, d)
        assert not m.yanlis_pozitifler, (donem, m.yanlis_pozitifler)


def test_gercek_kosu_iz_eslesmesi():
    if not _gercek_veri_var():
        print("    ATLANDI: referans/panel dosyaları yok")
        return
    r = M.duzeltme_olay_eslemesi(_DUZELTME_CSV, olay_csv=_OLAY_CSV,
                                 donem_csv=_DONEM_CSV)
    assert r["karar_ceviren_duzeltme"] == 14, r["karar_ceviren_duzeltme"]
    assert r["eslesen"] == 8, r["eslesen"]
    assert r["ters_yon"] == 0, r["ters_yon_kayitlar"]
    esl = {e["ticker"] for e in r["eslesen_kayitlar"]}
    # 4.1'in gördüğü iz: ikisi de b1_1'i HAYIR->EVET düzeltip çıktı.
    assert {"ASUZU", "BEYAZ"} <= esl, esl
    # BORLS düzeltmesi çıkışından SONRA — sayılmamalı.
    assert "BORLS" not in esl


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
