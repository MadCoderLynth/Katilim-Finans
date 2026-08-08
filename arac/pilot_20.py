"""Tek seferlik pilot örneklem seçimi ve tarama — Plan adımı 1.3.

**Bu üretim kodu değildir.** `katilim/` paketine girmez. Tek işi, 1.4a'nın
indirdiği arşivden 20/20 parser kapısının örneklemini **ölçüme göre** seçmek
ve kalıcı fixture'ları yazmak.

## Neden önce tam tarama

Örneklem şartları (solo tablo, küçük şirket, düzeltme bildirimi) ancak
ayrıştırdıktan sonra bilinebilir: "bu form solo mu" sorusunun cevabı dosya
adında yok. Ayrıştırma 0,06 sn/dosya olduğu için 1.276 formun tamamını
taramak ~80 saniye — örneklemi tahminle seçmek yerine ölçüyle seçiyoruz.

Yan kazanç: 20/20 kapısı fiilen **1.276/1.276** ölçümüne dönüşüyor. Kapı
yine 20 örnekle tanımlı (plan), ama arşivin tamamındaki self-check oranı
1.4b'ye devredilecek bir bulgu.

**Ağa çıkmaz.** Yalnız `veri/ham/` okur.

Çalıştırma:
    .venv/Scripts/python.exe arac/pilot_20.py --tara      # tam tarama
    .venv/Scripts/python.exe arac/pilot_20.py --sec       # 20'yi seç + fixture yaz
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from katilim.ayristirici import AyristirmaHatasi, ayristir  # noqa: E402
from katilim.karar import degerlendir  # noqa: E402
from katilim.metin import normalize  # noqa: E402
from katilim.oranlar import self_check  # noqa: E402

HAM = KOK / "veri" / "ham"
INDEKS = HAM / "arsiv_indeksi.csv"
TARAMA_JSON = KOK / "veri" / "onbellek" / "pilot_tarama.json"
FIXTURE_DIZINI = KOK / "tests" / "fixtures" / "pilot"

# Sektör sınıflaması unvandan türetiliyor — RESMÎ KAYNAK DEĞİL.
# `sirketler.csv`'nin `sektor` alanı boş (1.1b henüz koşulmadı), bu yüzden
# örneklem çeşitliliği için geçici bir vekil kullanılıyor. Rapor bunu
# "sektör doğrulandı" diye sunmamalı.
_SEKTOR_KALIPLARI = (
    ("GYO", ("gayrimenkul yatirim ortakligi",)),
    ("GSYO", ("girisim sermayesi yatirim ortakligi",)),
    ("HOLDING", ("holding",)),
    ("PERAKENDE", ("magazacilik", "market", "perakende", "magaza")),
    ("GIDA", ("gida", "sut", "et ", "tarim", "bira", "icecek")),
    ("ENERJI", ("enerji", "elektrik", "petrol", "dogalgaz", "gaz ")),
    ("INSAAT", ("insaat", "yapi", "cimento", "beton")),
    ("TEKSTIL", ("tekstil", "mensucat", "iplik", "konfeksiyon")),
    ("TEKNOLOJI", ("teknoloji", "bilisim", "yazilim", "elektronik")),
    ("SAGLIK", ("saglik", "ilac", "hastane", "medikal")),
    ("ULASTIRMA", ("havayollari", "hava yollari", "lojistik", "tasimacilik", "denizcilik")),
    ("TURIZM", ("turizm", "otel")),
)


def sektor_vekili(unvan: str) -> str:
    n = normalize(unvan)
    for etiket, kaliplar in _SEKTOR_KALIPLARI:
        if any(k in n for k in kaliplar):
            return etiket
    return "SANAYI_DIGER"


# --- Tarama ----------------------------------------------------------------


def arsiv_satirlari() -> list[dict]:
    with open(INDEKS, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def tek_form_olc(satir: dict, unvanlar: dict[str, str]) -> dict:
    """Bir arşiv dosyasını ayrıştırıp ölçüsünü çıkarır. Ağ yok."""
    yol = HAM / satir["dosya"]
    olcu = {
        "bildirim_id": int(satir["bildirim_id"]),
        "ticker": satir["ticker"],
        "tum_tickerlar": satir["tum_tickerlar"],
        "yil": satir["yil"],
        "periyot": satir["periyot"],
        "gonderim_ts": satir["gonderim_ts"],
        "dosya": satir["dosya"],
        "bayt": int(satir["bayt"] or 0),
        "pencere_disi": satir["pencere_disi"] == "EVET",
        "unvan": unvanlar.get(satir["ticker"], ""),
        "sektor_vekili": sektor_vekili(unvanlar.get(satir["ticker"], "")),
    }
    try:
        b = ayristir(
            yol.read_text(encoding="utf-8", errors="ignore"),
            bildirim_id=int(satir["bildirim_id"]),
            ticker=satir["ticker"],
        )
    except AyristirmaHatasi as e:
        olcu["ayristirma"] = "HATA"
        olcu["hata"] = f"{type(e).__name__}: {e}"[:200]
        return olcu
    except Exception as e:  # noqa: BLE001 — taramada her hata veridir
        olcu["ayristirma"] = "COKTU"
        olcu["hata"] = f"{type(e).__name__}: {e}"[:200]
        return olcu

    kontrol = self_check(b)
    karar = degerlendir(b)
    olcu.update(
        {
            "ayristirma": "OK",
            "nitelik": b.finansal_tablo_niteligi,
            "carpan": b.para_birimi_carpani,
            "imza": b.sablon_imzasi,
            "kalem_sayisi": len(b.kalemler),
            # Şablon her formda 55 satır basıyor (boş kalemler 0 olarak).
            # "Küçük şirket" ölçütü bu yüzden satır sayısıyla değil, DOLU
            # (sıfır olmayan) kalem sayısı ve toplam varlıkla ölçülüyor.
            "sifir_disi_kalem": sum(1 for k in b.kalemler if k.tutar_ham),
            "toplam_varlik": str(b.toplam("5H")),
            "dolu_beyan": sum(1 for v in b.beyanlar.values() if v is not None),
            "eksik_beyan": b.eksik_beyanlar(),
            "eksik_tablo": b.eksik_tablolar(),
            "is_duzeltme": b.is_duzeltme,
            "self_check": "GECTI" if kontrol.gecti else "KALDI",
            "sapmalar": {k: str(v) for k, v in kontrol.sapmalar.items()},
            "hesaplanan": {
                a: str(getattr(kontrol.hesaplanan, a)) for a in ("gelir", "varlik", "borc")
            },
            "ozet": {
                "gelir": str(b.ozet_gelir_orani) if b.ozet_gelir_orani is not None else None,
                "varlik": str(b.ozet_varlik_orani) if b.ozet_varlik_orani is not None else None,
                "borc": str(b.ozet_borc_orani) if b.ozet_borc_orani is not None else None,
            },
            "karar": karar.karar.value,
            "red_kodlari": list(karar.kodlar),
            "parser_donem": [b.yil, b.periyot],
        }
    )
    return olcu


def tara() -> list[dict]:
    from katilim import evren

    unvanlar = {s.ticker: s.unvan for s in evren.oku()}
    satirlar = arsiv_satirlari()
    t0 = time.monotonic()
    olculer = []
    for i, s in enumerate(satirlar, 1):
        olculer.append(tek_form_olc(s, unvanlar))
        if i % 200 == 0:
            print(f"  {i}/{len(satirlar)} ({time.monotonic()-t0:.0f} sn)", flush=True)
    TARAMA_JSON.parent.mkdir(parents=True, exist_ok=True)
    TARAMA_JSON.write_text(
        json.dumps(olculer, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"tarama yazıldı: {TARAMA_JSON} ({time.monotonic()-t0:.0f} sn)")
    return olculer


def tarama_oku() -> list[dict]:
    return json.loads(TARAMA_JSON.read_text(encoding="utf-8"))


# --- Örneklem seçimi -------------------------------------------------------
#
# Şartlar plan 1.3'ten. Seçim "kolay olanı" değil ZORU kapsamalı; bu yüzden
# her şart için aday havuzu ölçüden süzülüyor ve seçim deterministik.


def sec(olculer: list[dict], hedef: int = 20) -> tuple[list[dict], dict]:
    ok = [o for o in olculer if o["ayristirma"] == "OK"]
    secili: dict[int, dict] = {}
    gerekce: dict[int, list[str]] = {}

    def ekle(aday: dict, sebep: str) -> None:
        if aday["bildirim_id"] not in secili:
            secili[aday["bildirim_id"]] = aday
        gerekce.setdefault(aday["bildirim_id"], []).append(sebep)

    def sirala(liste, anahtar=None):
        return sorted(liste, key=anahtar or (lambda o: o["bildirim_id"]))

    # 1) En az 3 SOLO finansal tablo. KAP'ın yazımı "Konsolide Olmayan";
    #    "Solo" dizesi formda hiç geçmiyor (ölçüldü: 405 form böyle).
    solo = sirala([o for o in ok if (o.get("nitelik") or "") == "Konsolide Olmayan"])
    for o in solo[:3]:
        ekle(o, "solo (Konsolide Olmayan) tablo")

    # 2) En az 2 tanesi 2025/6 Aylık — pencerenin en eski ucu, şablon farkı
    #    çıkacaksa orada çıkar.
    eski = sirala(
        [o for o in ok if o["yil"] == "2025" and o["periyot"] == "6 Aylık"],
        lambda o: o["gonderim_ts"],
    )
    for o in eski[:2]:
        ekle(o, "2025/6 Aylık (pencerenin en eski ucu)")

    # 3) En az 2 küçük şirket. DİKKAT: şablon her formda 55 satır basıyor,
    #    yani "kalem sayısı az" ölçütü bu pencerede tanım gereği sağlanamaz
    #    (ölçüm: 1.276 formun 1.276'sında 55 kalem). Vekil ölçüt: en az
    #    DOLU kalemi olan ve toplam varlığı en küçük formlar.
    kucuk = sorted(ok, key=lambda o: (o["sifir_disi_kalem"], o["bildirim_id"]))
    for o in kucuk[:2]:
        ekle(o, f"küçük/az dolu kalem ({o['sifir_disi_kalem']}/55)")
    minik = sorted(ok, key=lambda o: (int(o["toplam_varlik"] or 0), o["bildirim_id"]))
    for o in minik[:1]:
        ekle(o, "en küçük toplam varlık")

    # 4) En az 1 düzeltme bildirimi (is_duzeltme tespiti hiç doğrulanmadı).
    duzeltme = sirala([o for o in ok if o["is_duzeltme"]])
    for o in duzeltme[:2]:
        ekle(o, "is_duzeltme=True")

    # 5) En az 3 farklı sektör. Vekil sınıflama; resmî kaynak değil.
    gorulen = {secili[b]["sektor_vekili"] for b in secili}
    for hedef_sektor in ("GYO", "PERAKENDE", "SANAYI_DIGER", "ENERJI", "GIDA", "HOLDING"):
        if hedef_sektor in gorulen:
            continue
        adaylar = sirala([o for o in ok if o["sektor_vekili"] == hedef_sektor])
        if adaylar:
            ekle(adaylar[0], f"sektör çeşitliliği ({hedef_sektor})")
            gorulen.add(hedef_sektor)

    # 5b) Dönem çeşitliliği. 3 Aylık / 9 Aylık / 2024 Yıllık formlar özel
    #     hesap dönemli şirketlerden geliyor (futbol kulüpleri 31 Mayıs'ta
    #     kapatıyor) ve şablon farkı çıkacaksa oralarda da çıkabilir.
    for etiket in ("3 Aylık", "9 Aylık"):
        adaylar = sirala([o for o in ok if o["periyot"] == etiket])
        if adaylar:
            ekle(adaylar[0], f"özel hesap dönemi ({etiket})")
    eski_yil = sirala([o for o in ok if o["yil"] == "2024"])
    if eski_yil:
        ekle(eski_yil[0], "2024/Yıllık (özel hesap dönemi, ağustos 2025'te verilmiş)")

    # 6) Self-check KALAN varsa hepsi örnekleme girer — kapının asıl konusu.
    for o in sirala([o for o in ok if o["self_check"] == "KALDI"])[:5]:
        ekle(o, "self-check KALDI (teşhis edilecek)")

    # 7) Eksik beyanı olan (BELİRSİZ karar üreten) varsa örnekleme girsin.
    for o in sirala([o for o in ok if o["eksik_beyan"]])[:2]:
        ekle(o, f"eksik beyan ({len(o['eksik_beyan'])})")

    # 8) Farklı şablon imzası görüldüyse her imzadan bir örnek.
    imzalar = {}
    for o in ok:
        imzalar.setdefault(o["imza"], []).append(o)
    for imza, grup in sorted(imzalar.items()):
        if not any(secili[b]["imza"] == imza for b in secili):
            ekle(sirala(grup)[0], f"şablon imzası {imza[:20]}…")

    # 9) Kalanı en büyük ve en küçük dosyalardan doldur (uç örnekler).
    ucler = sorted(ok, key=lambda o: o["bayt"])
    for o in list(reversed(ucler)) + ucler:
        if len(secili) >= hedef:
            break
        ekle(o, "uç örnek (dosya boyutu)")

    ozet = {
        "solo": sum(1 for b in secili if secili[b].get("nitelik") == "Konsolide Olmayan"),
        "konsolide": sum(1 for b in secili if secili[b].get("nitelik") == "Konsolide"),
        "2025_6_aylik": sum(
            1 for b in secili if secili[b]["yil"] == "2025" and secili[b]["periyot"] == "6 Aylık"
        ),
        "donemler": sorted({f"{secili[b]['yil']}/{secili[b]['periyot']}" for b in secili}),
        "duzeltme": sum(1 for b in secili if secili[b]["is_duzeltme"]),
        "sektor": sorted({secili[b]["sektor_vekili"] for b in secili}),
        "self_check_kaldi": sum(1 for b in secili if secili[b]["self_check"] == "KALDI"),
        "carpanlar": sorted({secili[b]["carpan"] for b in secili}),
    }
    secilenler = [dict(secili[b], gerekce=gerekce[b]) for b in sorted(secili)]
    return secilenler[:hedef], ozet


# --- Fixture yazımı --------------------------------------------------------


def fixture_yaz(secilenler: list[dict]) -> list[Path]:
    """Ayrıştırılmış JSON + beklenen üç oran, `tests/fixtures/pilot/` altına.

    Fixture, HTML'siz de anlamlı olmalı: `tests/test_pilot.py` arşiv yokken
    (taze klon) oranları ve kararı JSON'dan yeniden hesaplayabiliyor; arşiv
    varsa ayrıca HTML'i yeniden ayrıştırıp fixture ile karşılaştırıyor.
    """
    FIXTURE_DIZINI.mkdir(parents=True, exist_ok=True)
    yazilan = []
    for o in secilenler:
        yol = HAM / o["dosya"]
        b = ayristir(
            yol.read_text(encoding="utf-8", errors="ignore"),
            bildirim_id=o["bildirim_id"],
            ticker=o["ticker"],
        )
        kontrol = self_check(b)
        karar = degerlendir(b)
        icerik = {
            "_kaynak": {
                "dosya": o["dosya"],
                "bildirim_id": o["bildirim_id"],
                "ticker": o["ticker"],
                "unvan": o["unvan"],
                "sektor_vekili": o["sektor_vekili"],
                "gerekce": o["gerekce"],
                "pencere_disi": o["pencere_disi"],
            },
            "beklenen": {
                "sablon_imzasi": b.sablon_imzasi,
                "nitelik": b.finansal_tablo_niteligi,
                "kalem_sayisi": len(b.kalemler),
                "dolu_beyan": sum(1 for v in b.beyanlar.values() if v is not None),
                "self_check": "GECTI" if kontrol.gecti else "KALDI",
                "oranlar": {
                    a: str(getattr(kontrol.hesaplanan, a))
                    for a in ("gelir", "varlik", "borc")
                },
                "ozet_oranlar": {
                    "gelir": str(b.ozet_gelir_orani) if b.ozet_gelir_orani is not None else None,
                    "varlik": str(b.ozet_varlik_orani) if b.ozet_varlik_orani is not None else None,
                    "borc": str(b.ozet_borc_orani) if b.ozet_borc_orani is not None else None,
                },
                "karar": karar.karar.value,
                "red_kodlari": list(karar.kodlar),
            },
            "bildirim": b.to_dict(),
        }
        ad = f"{o['ticker']}_{o['yil']}_{normalize(o['periyot']).replace(' ', '_')}_{o['bildirim_id']}.json"
        (FIXTURE_DIZINI / ad).write_text(
            json.dumps(icerik, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        yazilan.append(FIXTURE_DIZINI / ad)
    return yazilan


def main() -> int:
    ap = argparse.ArgumentParser(description="Plan 1.3 — pilot örneklem")
    ap.add_argument("--tara", action="store_true", help="arşivin tamamını ayrıştır")
    ap.add_argument("--sec", action="store_true", help="20'yi seç ve fixture yaz")
    ap.add_argument("--hedef", type=int, default=20)
    args = ap.parse_args()

    olculer = tara() if args.tara else tarama_oku()

    dagilim: dict[str, int] = {}
    for o in olculer:
        dagilim[o["ayristirma"]] = dagilim.get(o["ayristirma"], 0) + 1
    sc: dict[str, int] = {}
    for o in olculer:
        if o["ayristirma"] == "OK":
            sc[o["self_check"]] = sc.get(o["self_check"], 0) + 1
    print(f"\nTARAMA: {len(olculer)} form · ayrıştırma {dagilim} · self-check {sc}")

    if args.sec:
        secilenler, ozet = sec(olculer, args.hedef)
        yazilan = fixture_yaz(secilenler)
        print(f"\nÖRNEKLEM: {len(secilenler)} form, {len(yazilan)} fixture")
        print(f"  şart karşılama: {ozet}")
        for o in secilenler:
            print(f"  {o['ticker']:8s} {o['yil']}/{o['periyot']:8s} "
                  f"{(o.get('nitelik') or '-'):10s} kalem={o['kalem_sayisi']:3d} "
                  f"{o['self_check']:6s} {o['karar']:14s} <- {'; '.join(o['gerekce'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
