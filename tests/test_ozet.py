"""Özet sayfası ayıklama testleri — ağa çıkmaz (Faz 1.1b).

Sentetik gövde, gerçek sayfanın yapısını taklit ediyor: değerler RSC
yükündeki çip bağlantılarının href'inde ve **base64 kodlu**. Kalıp
2026-08-08'de THYAO/ACSEL/ASELS sayfalarında ölçüldü.

Gerçek doğrulama `python -m katilim.cli ozet` koşusudur (OZET_RAPORU.md).
"""
import base64
import csv
import json
import pathlib
import sys
import tempfile
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from katilim import ozet  # noqa: E402
from katilim.evren import Sirket  # noqa: E402
from katilim.metin import normalize  # noqa: E402


def _b64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def _cip(yol: str, deger: str) -> str:
    return f'{{\\"href\\":\\"/tr/{yol}={_b64(deger)}\\"}}'


def _sayfa(pazar=None, sektorler=(), endeksler=(), etiket=True):
    """Gerçek sayfanın kabı: JS dize literaline gömülü RSC yükü."""
    parcalar = []
    if etiket:
        parcalar += [f'\\"{e}\\"' for e in ozet.ETIKETLER]
    if pazar:
        parcalar.append(_cip("Pazarlar?market", pazar))
    parcalar += [_cip("Sektorler?sector", s) for s in sektorler]
    parcalar += [_cip("Endeksler?indice", e) for e in endeksler]
    ic = "[" + ",".join(parcalar) + "]"
    return f'<html><body><script>self.__next_f.push([1,{json.dumps(ic)}])</script></body></html>'


# --- ayıklama --------------------------------------------------------------


def test_uc_alan_ayikliyor():
    html = _sayfa(
        pazar="YILDIZ PAZAR",
        sektorler=["İMALAT", "KİMYA İLAÇ PETROL LASTİK VE PLASTİK ÜRÜNLER"],
        endeksler=["BIST KATILIM 30", "BIST TÜM"],
    )
    b = ozet.ozet_ayristir(html)
    assert b.pazar == "YILDIZ PAZAR"
    assert b.sektorler == ["İMALAT", "KİMYA İLAÇ PETROL LASTİK VE PLASTİK ÜRÜNLER"]
    assert b.sektor == "İMALAT / KİMYA İLAÇ PETROL LASTİK VE PLASTİK ÜRÜNLER"
    assert b.endeksler == ["BIST KATILIM 30", "BIST TÜM"]
    assert b.eksik_alanlar == []


def test_turkce_karakter_base64ten_bozulmadan_geliyor():
    """'İ', 'Ü', 'Ş' UTF-8 üzerinden gidiyor; latin-1 çözülürse bozulur."""
    b = ozet.ozet_ayristir(_sayfa(sektorler=["ULAŞTIRMA VE DEPOLAMA"],
                                  endeksler=["BIST SÜRDÜRÜLEBİLİRLİK"]))
    assert b.sektorler == ["ULAŞTIRMA VE DEPOLAMA"]
    assert b.endeksler == ["BIST SÜRDÜRÜLEBİLİRLİK"]


def test_sektor_sirasi_korunuyor_tekrar_atiliyor():
    """Ana sektör önce, alt sektör sonra. `set()` bu bilgiyi yok ederdi."""
    b = ozet.ozet_ayristir(_sayfa(sektorler=["ULAŞTIRMA VE DEPOLAMA",
                                             "ULAŞTIRMA VE DEPOLAMA"]))
    assert b.sektorler == ["ULAŞTIRMA VE DEPOLAMA"], "tekrar tekilleşmeli"


def test_alani_olmayan_sayfada_none_kaliyor():
    """Alan yoksa `None` — boş dize DEĞİL. '' ile 'bilinmiyor' aynı şey değil."""
    b = ozet.ozet_ayristir(_sayfa(sektorler=["İMALAT"]))
    assert b.pazar is None, repr(b.pazar)
    assert b.endeksler == []
    assert b.sektor == "İMALAT"
    assert sorted(b.eksik_alanlar) == ["endeksler", "pazar"]


def test_hicbir_alani_olmayan_ama_etiketi_olan_sayfa_hata_degil():
    b = ozet.ozet_ayristir(_sayfa())
    assert b.pazar is None and b.sektor is None and b.endeksler == []


def test_cipsiz_ve_etiketsiz_sayfa_hata_firlatir():
    """Kural 7: 'alan boş' ile 'sayfa okunamadı' ayrı durumlar."""
    try:
        ozet.ozet_ayristir("<html><body><div id='root'></div></body></html>")
    except ozet.OzetOkunamadi:
        return
    raise AssertionError("çıpasız sayfada OzetOkunamadi bekleniyordu")


def test_cozulemeyen_base64_sayiliyor():
    html = _sayfa(sektorler=["İMALAT"]).replace(
        f"Sektorler?sector={_b64('İMALAT')}", "Sektorler?sector=!!!gecersiz"
    )
    b = ozet.ozet_ayristir(html)
    assert b.sektorler == [] and b.pazar is None


# --- toplama ---------------------------------------------------------------


class SahteCekici:
    def __init__(self, harita):
        self.harita = harita
        self.istekler = []
        self.istatistik = {"onbellek": 0, "ag": 0, "yeniden_deneme": 0, "negatif": 0}

    def getir(self, url, *, zorla=False, onbellekle=True):
        self.istekler.append(url)
        if url not in self.harita:
            from katilim.cekici import ÇekimHatası

            raise ÇekimHatası(f"HTTP 404: {url}")
        return self.harita[url]


def _sirket(ticker, slug, unvan=None, muaf=False):
    return Sirket(ticker=ticker, unvan=unvan or f"{ticker} A.Ş.",
                  kap_member_uuid="u", kap_kfif_slug=slug, mali_sektor_muaf=muaf)


def test_coklu_kodlu_sirket_tek_istek_iki_kayit():
    """795 pay kodu / 746 tüzel kişi: sayfa paylaşılıyor, istek tekrarlanmıyor."""
    slug = "123-albaraka"
    url = ozet.OZET_URL_KALIBI.format(slug=slug)
    c = SahteCekici({url: _sayfa(pazar="ANA PAZAR", sektorler=["BANKACILIK"],
                                 endeksler=["BIST TÜM"])})
    t = ozet.ozetleri_topla([_sirket("ALBRK", slug), _sirket("ALK", slug)], c)
    assert len(c.istekler) == 1, "aynı slug iki kez çekilmemeli"
    assert t.pazarlar == {"ALBRK": "ANA PAZAR", "ALK": "ANA PAZAR"}
    assert t.endeksler["ALK"] == ["BIST TÜM"]


def test_slug_yoksa_sessizce_gecilmiyor():
    c = SahteCekici({})
    t = ozet.ozetleri_topla([_sirket("XYZ", None)], c)
    assert c.istekler == []
    assert t.durumlar[0].durum == ozet.DURUM_SLUG_YOK
    assert t.uyarilar


def test_cekim_hatasi_kaydediliyor():
    c = SahteCekici({})
    t = ozet.ozetleri_topla([_sirket("XYZ", "9-xyz")], c)
    assert t.durumlar[0].durum == ozet.DURUM_CEKIM_HATASI


def test_evrene_basma_none_birakiyor():
    slug = "9-xyz"
    url = ozet.OZET_URL_KALIBI.format(slug=slug)
    c = SahteCekici({url: _sayfa(sektorler=["İMALAT"])})
    sirketler = [_sirket("XYZ", slug)]
    t = ozet.ozetleri_topla(sirketler, c)
    ozet.evrene_bas(sirketler, t)
    assert sirketler[0].sektor == "İMALAT"
    assert sirketler[0].pazar is None, "bulunmayan alan boş dize olmamalı"


# --- endeks üyeliği --------------------------------------------------------


def test_endeks_csv_olcum_tarihi_zorunlu():
    t = ozet.Toplama(endeksler={"ASELS": ["BIST KATILIM 30", "BIST 100"]})
    with tempfile.TemporaryDirectory() as d:
        yol = ozet.endeks_uyeligi_yaz(t, pathlib.Path(d) / "e.csv",
                                      olcum_tarihi=date(2026, 8, 8))
        with open(yol, newline="", encoding="utf-8-sig") as f:
            satirlar = list(csv.DictReader(f))
    assert list(satirlar[0]) == ["ticker", "endeks_adi", "olcum_tarihi"]
    assert {s["olcum_tarihi"] for s in satirlar} == {"2026-08-08"}
    assert len(satirlar) == 2


# --- muafiyet yeniden değerlendirmesi --------------------------------------


def test_muafiyet_kesin_kalipla_kapaniyor():
    yeni, gerekce = ozet.muafiyet_yeniden_degerlendir(
        "X SİGORTA A.Ş.", "FİNANS VE SİGORTA FAALİYETLERİ / SİGORTA"
    )
    # `str.lower()` KULLANMA: 'İ'.lower() birleşen noktalı 'i̇' üretir ve
    # düz 'i' ile eşleşmez (CLAUDE.md kural 5). Karşılaştırma normalize ile.
    assert yeni is True and "sigorta" in normalize(gerekce)


def test_gyo_finans_sektorunde_gorunse_de_muaf_degil():
    """Spec §0.4: GYO ve holding muafiyet listesinde YOK."""
    yeni, _ = ozet.muafiyet_yeniden_degerlendir(
        "X GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.", "FİNANS VE SİGORTA FAALİYETLERİ"
    )
    assert yeni is False


def test_oturmayan_sektor_belirsiz_kaliyor():
    """Kapatılamıyorsa MUAF İŞARETLENMEZ; fazladan sorgulamak zararsız."""
    yeni, gerekce = ozet.muafiyet_yeniden_degerlendir(
        "X TASARRUF FİNANSMAN A.Ş.", "FİNANS VE SİGORTA FAALİYETLERİ"
    )
    assert yeni is None and "belirsiz" in normalize(gerekce)


def test_mkyo_cogul_yazimla_da_kapaniyor():
    """KAP çoğul yazıyor ('ORTAKLIKLARI'), spec §0.4 tekil ('ortaklığı').

    Tekil kalıp çoğulun içinde geçmez; kök kullanılmazsa 6 gerçek MKYO
    kapanmadan kalıyordu (ölçüldü: ETYAT, EUKYO, GRNYO, ISYAT, MTRYO, OYAYO).
    """
    yeni, _ = ozet.muafiyet_yeniden_degerlendir(
        "İŞ YATIRIM ORTAKLIĞI A.Ş.", "MALİ KURULUŞLAR / MENKUL KIYMET YATIRIM ORTAKLIKLARI"
    )
    assert yeni is True


def test_semsiye_mali_kuruluslar_tek_basina_kapatmiyor():
    yeni, _ = ozet.muafiyet_yeniden_degerlendir("X A.Ş.", "MALİ KURULUŞLAR")
    assert yeni is None


def test_yeniden_degerlendirme_yalniz_belirsize_dokunuyor():
    """Zaten True/False olan kayıt sektörle EZİLMEZ."""
    sirketler = [
        _sirket("AAA", "1-a", unvan="X MENKUL KIYMET A.Ş.", muaf=False),
        _sirket("BBB", "2-b", unvan="Y YATIRIM ORTAKLIĞI A.Ş."),
    ]
    sirketler[0].sektor = "MALİ KURULUŞLAR / MENKUL KIYMET YATIRIM ORTAKLIKLARI"
    sirketler[1].sektor = "MALİ KURULUŞLAR / MENKUL KIYMET YATIRIM ORTAKLIKLARI"
    sirketler[1].mali_sektor_muaf = None

    sonuc = ozet.belirsizleri_yeniden_degerlendir(sirketler)
    assert [s.ticker for s, *_ in sonuc] == ["BBB"], "yalnız None olan ele alınmalı"
    assert sirketler[0].mali_sektor_muaf is False, "mevcut karar ezilmemeli"
    assert sirketler[1].mali_sektor_muaf is True


def test_kapatilamayan_belirsiz_kaliyor_muaf_olmuyor():
    """Sukuk SPV'leri (varlık kiralama): sektör alanı boş, §0.4'te yok."""
    s = _sirket("ATAVK", "3-c", unvan="ATA VARLIK KİRALAMA A.Ş.")
    s.mali_sektor_muaf = None
    s.sektor = None
    sonuc = ozet.belirsizleri_yeniden_degerlendir([s])
    assert s.mali_sektor_muaf is None, "kapatılamayan MUAF işaretlenmemeli"
    assert sonuc[0][2] is None


def test_sektor_yoksa_belirsiz_kaliyor():
    yeni, gerekce = ozet.muafiyet_yeniden_degerlendir("X A.Ş.", None)
    assert yeni is None and "bos" in normalize(gerekce)


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
