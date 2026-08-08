"""20 gerçek KAP bildirimi üzerinde regresyon — Faz 1.3'ün kalıcı kapısı.

**Bu, projedeki en güçlü test katmanı.** CLAUDE.md "Test katmanları"
ayrımında: sentetik HTML duman testidir, bu ise **kanıttır** — fixture'lar
KAP'ın kendi yayımladığı 20 formdan üretildi (`arac/pilot_20.py`).

İki kademe çalışır:

  1. **Fixture kademesi (her zaman).** Ayrıştırılmış JSON'dan üç oran
     yeniden hesaplanır ve formun kendi özet alanlarıyla karşılaştırılır;
     karar motoru yeniden koşulur. Arşiv (`veri/ham/`, git dışı) olmadan da
     çalışır — taze klonda da anlamlı.
  2. **Arşiv kademesi (arşiv varsa).** Ham HTML yeniden ayrıştırılıp
     fixture ile karşılaştırılır. Ayrıştırıcıdaki bir gerileme ancak burada
     yakalanır; arşiv yoksa test atlanır ve bunu SÖYLER (sessizce geçmez).

Örneklemin 7'sinde self-check bilinçli olarak KALDI: sebebi parser değil,
**formun kendi 4E TOPLAM satırının kendi kalemleriyle tutmaması**
(PILOT_20_RAPORU.md §3). Bu kayıtlar `beklenen.self_check == "KALDI"`
olarak dondurulmuştur — yani "bozuk" değil, "kaynağında tutarsız" diye
işaretlenmiştir. TOLERANS'ı gevşetmek bu bilgiyi yok ederdi.
"""
import json
import pathlib
import sys
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from katilim.ayristirici import ayristir  # noqa: E402
from katilim.karar import degerlendir  # noqa: E402
from katilim.model import KafifBildirim  # noqa: E402
from katilim.oranlar import TOLERANS, self_check  # noqa: E402

KOK = pathlib.Path(__file__).resolve().parents[1]
FIXTURE_DIZINI = KOK / "tests" / "fixtures" / "pilot"
HAM = KOK / "veri" / "ham"

FIXTURELAR = sorted(FIXTURE_DIZINI.glob("*.json"))


def _yukle(yol):
    return json.loads(yol.read_text(encoding="utf-8"))


def test_yirmi_fixture_var():
    assert len(FIXTURELAR) == 20, f"{len(FIXTURELAR)} fixture bulundu, 20 bekleniyordu"


def test_tek_sablon_imzasi():
    """Bu pencerede tek şablon revizyonu var (1.276/1.276 ölçüldü).

    İkinci bir imza çıkarsa bu bir BULGUDUR: şablon değişmiş demektir ve
    2.2 (şablon versiyonlama) devreye girer. Test kırılırsa imzayı silme,
    yeni imzayı belgeleyip karantina kuralını uygula.
    """
    imzalar = {_yukle(y)["beklenen"]["sablon_imzasi"] for y in FIXTURELAR}
    assert imzalar == {"4A|4B|4C|4D|4E|5F|5G|5H|6I|6J|OZET|S1|S2|S3"}, imzalar


def test_oranlar_fixtureden_yeniden_hesaplaniyor():
    """Kalemlerden hesaplanan üç oran, dondurulmuş değerlerle aynı olmalı.

    Bu kademe `veri/ham/` olmadan da koşar: oran formüllerinin (oranlar.py)
    20 gerçek belgeye karşı regresyonu.
    """
    for yol in FIXTURELAR:
        f = _yukle(yol)
        b = KafifBildirim.from_dict(f["bildirim"])
        kontrol = self_check(b)
        for ad in ("gelir", "varlik", "borc"):
            beklenen = f["beklenen"]["oranlar"][ad]
            bulunan = str(getattr(kontrol.hesaplanan, ad))
            assert bulunan == beklenen, f"{yol.name} {ad}: {bulunan} != {beklenen}"


def test_self_check_durumu_dondurulmus():
    """Geçen geçmeye, kalan kalmaya devam etmeli.

    KALAN 7 kayıt teşhis edilmiştir (formun kendi TOPLAM satırı tutarsız).
    Bunların GEÇTİ'ye dönmesi, TOLERANS'ın gevşetildiği anlamına gelir.
    """
    for yol in FIXTURELAR:
        f = _yukle(yol)
        b = KafifBildirim.from_dict(f["bildirim"])
        durum = "GECTI" if self_check(b).gecti else "KALDI"
        assert durum == f["beklenen"]["self_check"], f"{yol.name}: {durum}"


def test_tolerans_gevsetilmemis():
    """TOLERANS sabiti değiştirilirse bu test kırılır (CLAUDE.md kural 1)."""
    assert TOLERANS == Decimal("0.01"), f"TOLERANS {TOLERANS} olmuş"


def test_karar_motoru_dondurulmus():
    for yol in FIXTURELAR:
        f = _yukle(yol)
        b = KafifBildirim.from_dict(f["bildirim"])
        sonuc = degerlendir(b)
        assert sonuc.karar.value == f["beklenen"]["karar"], (
            f"{yol.name}: {sonuc.karar.value} != {f['beklenen']['karar']}"
        )
        assert list(sonuc.kodlar) == f["beklenen"]["red_kodlari"], yol.name


def test_beyanlar_eksiksiz():
    """13/13 beyan dolu olmalı. Eksik beyan `None` kalır ve karar BELİRSİZ
    olur (kural 2) — bu örneklemde hiç eksik yok, olursa bulgudur."""
    for yol in FIXTURELAR:
        f = _yukle(yol)
        b = KafifBildirim.from_dict(f["bildirim"])
        assert b.eksik_beyanlar() == [], f"{yol.name}: {b.eksik_beyanlar()}"
        assert f["beklenen"]["dolu_beyan"] == 13, yol.name


def test_ornek_zoru_kapsiyor():
    """Örneklem 'kolay olanı' değil zoru kapsamalı (plan 1.3 şartları)."""
    kayitlar = [_yukle(y) for y in FIXTURELAR]
    nitelikler = [k["beklenen"]["nitelik"] for k in kayitlar]
    donemler = {
        (k["bildirim"]["yil"], k["bildirim"]["periyot"]) for k in kayitlar
    }
    carpanlar = {k["bildirim"]["para_birimi_carpani"] for k in kayitlar}

    assert nitelikler.count("Konsolide Olmayan") >= 3, "en az 3 solo tablo gerekli"
    assert sum(1 for d in donemler if d[1] == "6 Aylık") >= 1
    assert len(donemler) >= 4, f"dönem çeşitliliği yetersiz: {donemler}"
    assert len(carpanlar) >= 2, f"tek para birimi çarpanı: {carpanlar}"
    assert sum(1 for k in kayitlar if k["bildirim"]["is_duzeltme"]) >= 1, \
        "en az 1 düzeltme bildirimi olmalı"
    assert sum(1 for k in kayitlar if k["beklenen"]["self_check"] == "KALDI") >= 1, \
        "teşhis edilmiş sapmalar örneklemde kalmalı"


def test_arsivden_yeniden_ayristirma():
    """Ham HTML -> fixture. Ayrıştırıcı gerilemesini YALNIZ bu yakalar.

    `veri/ham/` git dışı (239 MB). Yoksa test atlanır ama bunu duyurur —
    sessizce geçmek, kapının kapalı olduğunu gizlemek olurdu.
    """
    if not HAM.exists():
        print("    ATLANDI: veri/ham/ yok (arşiv git dışı) — fixture kademesi koştu")
        return
    bakilan = 0
    for yol in FIXTURELAR:
        f = _yukle(yol)
        html = HAM / f["_kaynak"]["dosya"]
        if not html.exists():
            continue
        b = ayristir(
            html.read_text(encoding="utf-8", errors="ignore"),
            bildirim_id=f["_kaynak"]["bildirim_id"],
            ticker=f["_kaynak"]["ticker"],
        )
        bek = f["beklenen"]
        assert b.sablon_imzasi == bek["sablon_imzasi"], yol.name
        assert b.finansal_tablo_niteligi == bek["nitelik"], yol.name
        assert len(b.kalemler) == bek["kalem_sayisi"], yol.name
        kontrol = self_check(b)
        for ad in ("gelir", "varlik", "borc"):
            assert str(getattr(kontrol.hesaplanan, ad)) == bek["oranlar"][ad], (
                f"{yol.name} {ad}"
            )
        assert ("GECTI" if kontrol.gecti else "KALDI") == bek["self_check"], yol.name
        assert degerlendir(b).karar.value == bek["karar"], yol.name
        bakilan += 1
    if bakilan == 0:
        print("    ATLANDI: arşivde fixture dosyaları bulunamadı")
    else:
        print(f"    ({bakilan}/20 ham HTML'den yeniden ayrıştırıldı)")


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
