"""Ön mutabakat testleri — ağa çıkmaz (Faz 4.0).

Test edilen asıl şey **dört sınıfın ayrılması**. Çelişkiyi doğrudan
"uyuşmazlık" saymak, modelleme boşluğunu hipotez hatası gibi gösterir;
bu modülün varlık sebebi o karışıklığı önlemek.

Özellikle **MUAF ≠ ELENMİŞ** (spec §0.4): muafiyet uygunsuzluk değil kapsam
dışılıktır ve endeks üyeliğini engellemez. `KAPSAM_DISI` bir kaydı
"elenmiş" saymak uyuşmazlık oranını sahte biçimde şişirir.
"""
import csv
import pathlib
import sys
import tempfile
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from katilim import mutabakat  # noqa: E402
from katilim.evren import Sirket  # noqa: E402

PANEL_BASLIK = [
    "ticker", "yil", "periyot", "form_donem_etiketi",
    "gelir_orani_kalem", "varlik_orani_kalem", "borc_orani_kalem",
    "gelir_orani_ozet", "varlik_orani_ozet", "borc_orani_ozet",
    "oran_ayrisiyor", "h5_ayirt_edici", "karar", "red_kodlari",
    "karar_kalem_bazli", "red_kodlari_kalem", "self_check", "karantina",
    "karantina_sebebi", "sablon_imzasi", "nitelik", "bildirim_id",
    "gonderim_ts", "is_duzeltme", "dosya",
]


def _dosyalar(d, panel_satirlari, endeks_satirlari, beyan_satirlari):
    d = pathlib.Path(d)
    with open(d / "panel.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=PANEL_BASLIK)
        w.writeheader()
        for r in panel_satirlari:
            w.writerow({k: r.get(k, "") for k in PANEL_BASLIK})
    with open(d / "endeks.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "endeks_adi", "olcum_tarihi"])
        w.writeheader()
        w.writerows(endeks_satirlari)
    with open(d / "beyan.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "unvan", "durum", "kafif_sayisi",
                                          "sorgu_durumu", "mali_sektor_muaf"])
        w.writeheader()
        w.writerows(beyan_satirlari)
    return d / "panel.csv", d / "endeks.csv", d / "beyan.csv"


def _panel(ticker, karar, ts="2026-03-04 18:57:54", kodlar=""):
    return {"ticker": ticker, "karar": karar, "red_kodlari": kodlar,
            "gonderim_ts": ts, "yil": "2025", "periyot": "Yıllık",
            "oran_ayrisiyor": "HAYIR", "h5_ayirt_edici": "HAYIR",
            "is_duzeltme": "HAYIR", "bildirim_id": "1"}


def _xktum(ticker):
    return {"ticker": ticker, "endeks_adi": "BIST KATILIM TUM",
            "olcum_tarihi": "2026-08-08"}


# Endeks dosyası hiç satırsız olmamalı: satırsız dosya "kimse XKTUM'da
# değil" demek olur ve tüm panel uyuşmazlık görünür (mutabakat.py bunu
# hata sayıyor). XKTUM üyesi olmayan senaryolarda başka endeksten satır.
_BASKA_ENDEKS = {"ticker": "ZZZ", "endeks_adi": "BIST TUM",
                 "olcum_tarihi": "2026-08-08"}


# Senaryoda geçmeyen, yalnız dosyayı satırsız bırakmamak için kullanılan kayıt.
_BASKA_PANEL = {"ticker": "ZZZ", "karar": "UYGUN_DEGIL", "red_kodlari": "",
                "gonderim_ts": "2025-06-01 10:00:00", "yil": "2025",
                "periyot": "Yıllık", "oran_ayrisiyor": "HAYIR",
                "h5_ayirt_edici": "HAYIR", "is_duzeltme": "HAYIR",
                "bildirim_id": "99"}


def _beyan(ticker, durum):
    return {"ticker": ticker, "unvan": f"{ticker} A.Ş.", "durum": durum,
            "kafif_sayisi": "0", "sorgu_durumu": "", "mali_sektor_muaf": ""}


def _sirket(ticker, *, pazar="YILDIZ PAZAR", uuid="u1", muaf=False):
    return Sirket(ticker=ticker, unvan=f"{ticker} A.Ş.", kap_member_uuid=uuid,
                  kap_kfif_slug=None, pazar=pazar, mali_sektor_muaf=muaf)


def _kosla(d, sirketler, panel, endeks, beyan, bugun=date(2026, 8, 8)):
    # Panel de satırsız olmamalı (mutabakat.py hata sayıyor): senaryoda
    # "bu şirketin satırı yok" demek istiyoruz, "panel boş" değil.
    p, e, b = _dosyalar(d, panel + [_BASKA_PANEL], endeks + [_BASKA_ENDEKS], beyan)
    return mutabakat.karsilastir(sirketler, panel_csv=p, endeks_csv=e,
                                 beyan_csv=b, bugun=bugun)


# --- revizyon takvimi ------------------------------------------------------


def test_son_revizyon_takvimi():
    assert mutabakat.son_revizyon(date(2026, 8, 8)) == date(2026, 5, 1)
    assert mutabakat.son_revizyon(date(2026, 10, 5)) == date(2026, 10, 1)
    assert mutabakat.son_revizyon(date(2026, 3, 1)) == date(2025, 10, 1)


# --- dört sınıf ------------------------------------------------------------


def test_uyumlu_kayitlar():
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_sirket("AAA"), _sirket("BBB", uuid="u2")],
                   [_panel("AAA", "UYGUN", "2025-06-01 10:00:00"),
                    _panel("BBB", "UYGUN_DEGIL", "2025-06-01 10:00:00")],
                   [_xktum("AAA")], [])
    assert m.sinif_dagilimi() == {mutabakat.SINIF_UYUMLU: 2}


def test_muaf_endekste_uyusmazlik_degil():
    """MUAF ≠ ELENMİŞ: ALBRK katılım bankası, KAFİF vermiyor ama XKTUM'da."""
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_sirket("ALBRK", muaf=True)], [],
                   [_xktum("ALBRK")], [_beyan("ALBRK", "KAPSAM_DISI")])
    s = m.satirlar[0]
    assert s.sinif == mutabakat.SINIF_PANELDE_YOK, s.sinif
    assert m.gercek_uyusmazliklar == []


def test_kapsam_karari_gercek_uyusmazlik_sayilmaz():
    """Panelde satırı olan ama kararı BELIRSIZ olan kayıt kapsam sınıfına."""
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_sirket("CCC")],
                   [_panel("CCC", "BELIRSIZ", "2025-06-01 10:00:00")], [], [])
    assert m.satirlar[0].sinif == mutabakat.SINIF_KAPSAM


def test_pazar_on_sarti_yoksa_kapsam():
    """Biz UYGUN desek de nitelikli yatırımcı pazarındaki kod XKTUM'a giremez."""
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_sirket("DDD", pazar="YAKIN İZLEME PAZARI")],
                   [_panel("DDD", "UYGUN", "2025-06-01 10:00:00")], [], [])
    s = m.satirlar[0]
    assert s.sinif == mutabakat.SINIF_KAPSAM and "ön şartı" in s.sebep


def test_donem_uyumsuzlugu_otomatik_etiketleniyor():
    """KAFİF son revizyondan SONRA yayımlandıysa çelişki beklenen davranış."""
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_sirket("EEE")],
                   [_panel("EEE", "UYGUN_DEGIL", "2026-07-30 10:00:00")],
                   [_xktum("EEE")], [])
    s = m.satirlar[0]
    assert s.sinif == mutabakat.SINIF_DONEM, s.sinif
    assert "01.05.2026" in s.sebep


def test_kod_ayrismasi_h1_h4un_reddi_sayilmaz():
    """Aynı uuid'in bir kodu endekste, diğeri değil -> likidite kaynaklı."""
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_sirket("ALBRK", uuid="u9"), _sirket("ALK", uuid="u9")],
                   [_panel("ALBRK", "UYGUN", "2025-06-01 10:00:00"),
                    _panel("ALK", "UYGUN", "2025-06-01 10:00:00")],
                   [_xktum("ALBRK")], [])
    alk = [s for s in m.satirlar if s.ticker == "ALK"][0]
    assert alk.sinif == mutabakat.SINIF_KOD
    assert m.gercek_uyusmazliklar == []


def test_gercek_uyusmazlik_ve_yanlis_pozitif():
    """Üç açıklama da geçerli değilse GERÇEK; biz UYGUN + dışarıda = pahalı."""
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_sirket("FFF")],
                   [_panel("FFF", "UYGUN", "2025-06-01 10:00:00")], [], [])
    s = m.satirlar[0]
    assert s.sinif == mutabakat.SINIF_GERCEK
    assert s.yanlis_pozitif is True, "uygunsuzu uygun göstermek pahalı hata"


def test_panelde_yok_ayri_sinif():
    """XKTUM üyesi olup panelde kaydı olmayan isim matrise girmez."""
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(d, [_sirket("GGG")], [], [_xktum("GGG")],
                   [_beyan("GGG", "BEYAN_YOK")])
    assert m.satirlar[0].sinif == mutabakat.SINIF_PANELDE_YOK
    assert len(m.panelde_yok) == 1


# --- oran ------------------------------------------------------------------


def test_uyusmazlik_orani_paydasi_yalniz_karsilastirilabilir():
    """Kapsam / dönem / kod ayrışması paydaya girmez; girseydi oran sahte
    biçimde düşerdi."""
    with tempfile.TemporaryDirectory() as d:
        m = _kosla(
            d,
            [_sirket("A1"), _sirket("A2", uuid="u2"), _sirket("A3", uuid="u3"),
             _sirket("A4", pazar="GÖZALTI PAZARI", uuid="u4")],
            [_panel("A1", "UYGUN", "2025-06-01 10:00:00"),
             _panel("A2", "UYGUN", "2025-06-01 10:00:00"),
             _panel("A3", "UYGUN_DEGIL", "2025-06-01 10:00:00"),
             _panel("A4", "UYGUN", "2025-06-01 10:00:00")],
            [_xktum("A1")], [],
        )
    oran, gercek, n = m.uyusmazlik_orani()
    assert gercek == 1 and n == 3, (gercek, n)   # A4 kapsam dışı, paydada yok
    assert abs(oran - 1 / 3) < 1e-9


def test_girdi_yoksa_hata_firlatiyor():
    """Kural 7: 'girdi yok' ile 'uyuşmazlık yok' ayrı durumlar."""
    with tempfile.TemporaryDirectory() as d:
        try:
            mutabakat.xktum_uyeleri(pathlib.Path(d) / "yok.csv")
        except mutabakat.MutabakatGirdisiYok:
            return
    raise AssertionError("girdi yokken MutabakatGirdisiYok bekleniyordu")


def test_son_karar_gonderim_ts_ile_seciliyor():
    """Dönem etiketi kronoloji taşımıyor; en geç kayıt zaman damgasıyla."""
    with tempfile.TemporaryDirectory() as d:
        p, e, b = _dosyalar(
            d,
            [_panel("HHH", "UYGUN_DEGIL", "2025-08-11 10:00:00"),
             _panel("HHH", "UYGUN", "2026-03-04 10:00:00")],
            [], [],
        )
        son = mutabakat.son_kararlar(p)
    assert son["HHH"]["karar"] == "UYGUN"


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
