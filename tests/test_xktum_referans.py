"""XKTUM tarihsel referans (plan 4.1) testleri — ağa çıkmaz.

**İki kademe** (`test_pilot.py` ile aynı disiplin):

1. **Fixture kademesi (her zaman):** geriye yürüme mantığı, sütun çıpası,
   yapısal sözcük elemesi ve kural 7 davranışları sentetik veriyle
   donduruluyor. Taze klonda da koşar.
2. **PDF kademesi (arşiv varsa):** `veri/referans/ham/` altındaki 5 gerçek
   PDF yeniden ayrıştırılıp ölçülmüş sayılarla karşılaştırılıyor. Arşiv
   yoksa test **atlandığını duyurur**, sessizce geçmez.

Donduruluyor çünkü ikisi de gerçek hatalardan çıktı:
- Sayfa bazlı ayıklama, XKTUM listesi 2. sayfaya taştığında altındaki
  KATILIM 100 tablosunu XKTUM sanıyordu (sessiz kirlenme).
- `PAY` başlık sözcüğü çıpanın tam x0'ında durduğu ve `[A-Z]{3,6}`
  kalıbına uyduğu için her bölüme sahte bir "PAY" kodu ekleniyordu.
"""
import pathlib
import sys
import traceback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "arac"))

from xktum_referans import (  # noqa: E402
    HAM,
    PDFLER,
    DonemDegisimi,
    ReferansOkunamadi,
    _YAPISAL_SOZCUKLER,
    _endeks_bantlari,
    _sutun_capalari,
    ayristir,
    guncel_xktum,
    kur,
)

KOK = pathlib.Path(__file__).resolve().parents[1]

# 4.1 koşusunda ölçülen sayılar. Değişirse bu bir BULGUDUR — sayı
# güncellenmeden önce sebebi araştırılır (PDF revize mi edildi?).
OLCULEN = {
    "2024-07-01": (37, 21),
    "2024-12-01": (31, 65),
    "2025-05-01": (21, 36),
    "2025-10-01": (23, 29),
    "2026-05-01": (27, 19),
}


def _sozcuk(metin, x0, top):
    return {"text": metin, "x0": x0, "x1": x0 + 6 * len(metin), "top": top}


# --- Bant ayrımı -----------------------------------------------------------


def test_bant_bir_sonraki_endeks_basliginda_biter():
    """XKTUM listesi bir sayfada bitmeyip altında KATILIM 100 tablosu
    varsa, bant ikincisini KAPSAMAMALI. Gerçek vaka: 01.12.2024 PDF'i."""
    satirlar = [
        (100, [_sozcuk("BIST", 57, 100), _sozcuk("KATILIM", 79, 100),
               _sozcuk("TÜM", 123, 100), _sozcuk("ENDEKSİ", 146, 100)]),
        (154, [_sozcuk("59", 304, 154), _sozcuk("SONME", 323, 154)]),
        (200, [_sozcuk("BIST", 57, 200), _sozcuk("KATILIM", 79, 200),
               _sozcuk("100", 123, 200), _sozcuk("ENDEKSİ", 138, 200)]),
        (250, [_sozcuk("1", 63, 250), _sozcuk("ALCTL", 258, 250)]),
    ]
    bantlar = _endeks_bantlari(satirlar)
    assert len(bantlar) == 2, bantlar
    ad, ust, alt = bantlar[0]
    assert ad == "bist katilim tum endeksi"
    assert ust == 100 and alt == 200, (ust, alt)
    icerik = [y for y, _ in satirlar if ust < y < alt]
    assert icerik == [154], icerik


def test_bant_baslik_kalibi_alt_endeksleri_de_taniyor():
    for ad in ("BIST KATILIM 30 ENDEKSİ", "BIST KATILIM SÜRDÜRÜLEBİLİRLİK ENDEKSİ"):
        ws = [_sozcuk(p, 50 + 30 * i, 10) for i, p in enumerate(ad.split())]
        assert _endeks_bantlari([(10, ws)]), ad


# --- Sütun çıpası ----------------------------------------------------------


def test_pay_capasi_bolume_x_konumuna_gore_atanir():
    bant = [
        (119, [_sozcuk("ALINACAK", 61, 119), _sozcuk("PAYLAR", 112, 119),
               _sozcuk("ÇIKARILACAK", 301, 119), _sozcuk("PAYLAR", 369, 119)]),
        (131, [_sozcuk("NO", 61, 131), _sozcuk("PAY", 82, 131),
               _sozcuk("KODU", 102, 131), _sozcuk("NO", 301, 131),
               _sozcuk("PAY", 322, 131), _sozcuk("KODU", 342, 131)]),
    ]
    capalar = _sutun_capalari(bant)
    kod = sorted((x, b) for x, b, tur in capalar if tur == "KOD")
    assert kod == [(82, "GIREN"), (322, "CIKAN")], kod
    no = sorted((x, b) for x, b, tur in capalar if tur == "NO")
    assert no == [(61, "GIREN"), (301, "CIKAN")], no


def test_yedek_bolumu_taniniyor():
    bant = [(120, [_sozcuk("ALINACAK", 61, 120), _sozcuk("ÇIKARILACAK", 242, 120),
                   _sozcuk("YEDEK", 422, 120), _sozcuk("PAY", 434, 120)])]
    capalar = _sutun_capalari(bant)
    assert ("YEDEK" in [b for _x, b, _t in capalar]), capalar


def test_pay_sozcugu_yapisal_listede():
    """`PAY` çıpanın x0'ında durur ve pay kodu kalıbına uyar. Elenmezse
    her bölüme sahte bir kod girer (ölçüldü: 5 PDF'de 5 kez)."""
    assert "pay" in _YAPISAL_SOZCUKLER
    for s in ("kodu", "no", "bulten", "adi", "paylar"):
        assert s in _YAPISAL_SOZCUKLER, s


# --- Kural 7: boş sonuç ≠ okunamayan kaynak --------------------------------


def test_xktum_bandi_yoksa_hata_firlatir(tmp=None):
    """'Değişiklik yok' ile 'yapıyı okuyamadım' ayrı durumlar."""
    import io
    import types

    sahte_sayfa = types.SimpleNamespace(
        extract_words=lambda: [_sozcuk("BAMBASKA", 10, 10)],
        extract_text=lambda: "BAMBASKA",
    )

    class SahtePdf:
        pages = [sahte_sayfa]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    import xktum_referans as xr

    gercek = sys.modules.get("pdfplumber")
    sahte = types.ModuleType("pdfplumber")
    sahte.open = lambda _p: SahtePdf()
    sys.modules["pdfplumber"] = sahte
    try:
        try:
            xr.ayristir(pathlib.Path("yok.pdf"), "2026-05-01", "2026-09-30")
        except ReferansOkunamadi:
            pass
        else:
            raise AssertionError("XKTUM bandı yokken hata fırlatılmadı")
    finally:
        if gercek is not None:
            sys.modules["pdfplumber"] = gercek
        else:
            sys.modules.pop("pdfplumber", None)
    _ = io


def test_guncel_xktum_bos_dosyada_hata_firlatir(tmp_yol=None):
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        y = pathlib.Path(d) / "endeks.csv"
        y.write_text("ticker,endeks_adi,olcum_tarihi\nAAA,BIST 100,2026-08-08\n",
                     encoding="utf-8")
        try:
            guncel_xktum(y)
        except ReferansOkunamadi:
            return
        raise AssertionError("XKTUM satırı yokken hata fırlatılmadı")


# --- Geriye yürüme ---------------------------------------------------------


def _degisim(bas, bit, giren, cikan, dosya):
    return DonemDegisimi(donem_baslangic=bas, donem_bitis=bit, kaynak_dosya=dosya,
                         giren=list(giren), cikan=list(cikan))


def test_geriye_yurume_giren_cikan_ters_uygulanir():
    """Bir dönemde X girdiyse ONDAN ÖNCE listede yoktu; çıktıysa vardı."""
    d = [
        _degisim("2025-10-01", "2026-04-30", ["YENI1"], ["ESKI1"], "p1.pdf"),
        _degisim("2026-05-01", "2026-09-30", ["YENI2"], ["ESKI2"], "p2.pdf"),
    ]
    evren = {"YENI1", "YENI2", "ESKI1", "ESKI2", "SABIT"}
    satirlar, tanilar = kur(d, {"YENI2", "YENI1", "SABIT"}, "2026-08-08", evren)
    uyeler = {(r["donem_baslangic"], r["ticker"])
              for r in satirlar if r["endekste_mi"] == "EVET"}
    assert ("2026-05-01", "YENI2") in uyeler
    # YENI2 bu dönemde girdi -> önceki dönemde YOKTU
    assert ("2025-10-01", "YENI2") not in uyeler
    # ESKI2 bu dönemde çıktı -> önceki dönemde VARDI
    assert ("2025-10-01", "ESKI2") in uyeler
    assert not tanilar["tutarsizlik"], tanilar["tutarsizlik"]


def test_evrende_olmayan_kod_icin_hayir_yazilmaz():
    """Borsadan çıkmış kod hakkında görüşümüz yok; 'hayır' demek uydurmak
    olurdu. EVET satırı kalır (kanıtı var), HAYIR satırı yazılmaz."""
    d = [
        _degisim("2025-10-01", "2026-04-30", [], [], "p1.pdf"),
        _degisim("2026-05-01", "2026-09-30", [], ["SILINMIS"], "p2.pdf"),
    ]
    satirlar, _ = kur(d, {"SABIT"}, "2026-08-08", {"SABIT"})
    silinmis = [r for r in satirlar if r["ticker"] == "SILINMIS"]
    assert [r["endekste_mi"] for r in silinmis] == ["EVET"], silinmis
    assert silinmis[0]["donem_baslangic"] == "2025-10-01"


def test_tutarsizlik_sessizce_yutulmuyor():
    """Girdiği söylenen kod üye değilse RAPORLANIR (gerçek vaka: EFORC,
    DAGHL, PEHOL — üçü de borsadan çıkmış)."""
    d = [
        _degisim("2025-10-01", "2026-04-30", [], [], "p1.pdf"),
        _degisim("2026-05-01", "2026-09-30", ["HAYALET"], [], "p2.pdf"),
    ]
    _, tanilar = kur(d, {"SABIT"}, "2026-08-08", {"SABIT"})
    assert tanilar["tutarsizlik"], "tutarsızlık raporlanmadı"
    t = tanilar["tutarsizlik"][0]
    assert t["giren_ama_uye_degil"] == ["HAYALET"]
    assert t["evrende_olmayan"] == ["HAYALET"]


def test_en_guncel_donem_capasi_kap_listesi():
    """Son dönemin üyeliği PDF'ten değil KAP'ın kendi listesinden gelir."""
    d = [
        _degisim("2025-10-01", "2026-04-30", [], [], "p1.pdf"),
        _degisim("2026-05-01", "2026-09-30", [], [], "p2.pdf"),
    ]
    satirlar, _ = kur(d, {"SABIT"}, "2026-08-08", {"SABIT"})
    son = [r for r in satirlar if r["donem_baslangic"] == "2026-05-01"]
    assert son[0]["kaynak_dosya"].startswith("endeks_uyeligi.csv"), son[0]


# --- PDF kademesi (arşiv varsa) --------------------------------------------


def test_gercek_pdfler_olculen_sayilari_veriyor():
    eksik = [b for b, _t, _u in PDFLER
             if not (HAM / f"katilim_endeksleri_{b.replace('-','')}_"
                     f"{_t.replace('-','')}.pdf").exists()]
    if eksik:
        print(f"    ATLANDI: {len(eksik)} PDF arşivde yok "
              f"(`--indir` ile alınır) — ayrıştırıcı gerilemesi SINANMADI")
        return
    for bas, bit, _url in PDFLER:
        yol = HAM / f"katilim_endeksleri_{bas.replace('-','')}_{bit.replace('-','')}.pdf"
        d = ayristir(yol, bas, bit)
        assert (len(d.giren), len(d.cikan)) == OLCULEN[bas], (bas, len(d.giren),
                                                              len(d.cikan))
        assert d.self_check == "GEÇTİ", (bas, d.self_check)
        assert not d.yedek, (bas, d.yedek)
        assert d.basliktaki_donem.startswith(
            f"{bas[8:10]}.{bas[5:7]}.{bas[0:4]}"), (bas, d.basliktaki_donem)


def test_pdf_kendi_numarasi_ile_mutabakat_zorunlu():
    """Self-check gevşetilemez: PDF'in NO sütunu N diyorsa N kod ayıklanmalı."""
    kaynak = (KOK / "arac" / "xktum_referans.py").read_text(encoding="utf-8")
    assert "max(nolar) != len(liste)" in kaynak, "NO sütunu self-check'i kaldırılmış"
    assert 'd.self_check = "GEÇTİ" if not sapmalar' in kaynak


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
