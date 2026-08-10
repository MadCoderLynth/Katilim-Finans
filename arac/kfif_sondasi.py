"""XKTUM üyesi olup panelde hiç kaydı olmayan 8 isim için ikili sonda — 4.0.

**Bu üretim kodu değildir** ve `/tr/kfif/{id}-{slug}` rotasını **veri
kaynağı olarak kullanmaz.** O rota yasak (ROTA_KESFI_RAPORU §6): gönderim
zaman damgası yok ve 4A'nın son üç satırı render edilmiyor, yani ondan
üretilen her karar `BELIRSIZ` olur.

Burada sorulan tek şey **ikili**: bu tüzel kişinin KAP'ta bir KAFİF beyanı
var mı, yok mu? Üç okumayı ayırt etmek için (spec §0.4 kutusu):

  (a) keşif boşluğu — beyan var, biz kaçırdık  -> sayfa DOLU form döner
  (b) selef tüzel kişi — beyan başka uuid'de   -> sayfa "Bilgi Mevcut Değil"
  (c) kural boşluğu — hiç vermemişler          -> sayfa "Bilgi Mevcut Değil"

(a) çıkarsa 1.2'nin kapsamı yeniden değerlendirilir. (b) ile (c) bu sonda
ile ayrılmaz; onları unvan/slug kimliği kanıtı ayırıyor.

Bütçe: 8 istek, onaylandı. Çalıştırma:
    .venv/Scripts/python.exe arac/kfif_sondasi.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from katilim.cekici import BütçeAşıldı, HızSınırlayıcı, ÇekimHatası, Çekici  # noqa: E402
from katilim.evren import oku as evren_oku  # noqa: E402
from katilim.metin import normalize  # noqa: E402

KFIF_URL = "https://kap.org.tr/tr/kfif/{slug}"
CIKTI = KOK / "veri" / "onbellek" / "kfif_sonda_olcum.json"

HEDEFLER = ["AAGYO", "BETAE", "GENKM", "GOLDA", "LXGYO", "MCARD", "SOHOE", "SSAAT"]

# Sayfanın "beyan yok" cevabı. İçerik imzası; konum değil.
BOS_IMZA = "bilgi mevcut degil"
# Dolu formun imzası: KAFİF tablolarının ayırt edici etiketi.
DOLU_IMZALAR = ("alkollu icki", "katilim finansi ilkelerine uygun olmayan")


def olc(govde: str) -> dict:
    n = normalize(govde)
    dolu = [i for i in DOLU_IMZALAR if i in n]
    return {
        "bayt": len(govde),
        "bos_imza": BOS_IMZA in n,
        "dolu_imzalar": dolu,
        "sonuc": "DOLU_FORM" if dolu else ("BILGI_YOK" if BOS_IMZA in n else "BELIRSIZ"),
    }


def main() -> int:
    sirketler = {s.ticker: s for s in evren_oku()}
    cekici = Çekici(
        KOK / "veri" / "onbellek",
        sinirlayici=HızSınırlayıcı(min_aralik=4.0, jitter=1.0, oturum_butcesi=8),
    )

    sonuclar = []
    try:
        for t in HEDEFLER:
            s = sirketler.get(t)
            kayit = {"ticker": t, "unvan": getattr(s, "unvan", None),
                     "slug": getattr(s, "kap_kfif_slug", None)}
            if not s or not s.kap_kfif_slug:
                kayit["sonuc"] = "SLUG_YOK"
                sonuclar.append(kayit)
                continue
            url = KFIF_URL.format(slug=s.kap_kfif_slug)
            kayit["url"] = url
            try:
                kayit.update(olc(cekici.getir(url, onbellekle=False)))
            except ÇekimHatası as e:
                kayit["sonuc"] = "CEKIM_HATASI"
                kayit["hata"] = str(e)[:160]
            sonuclar.append(kayit)
            print(f"  {t:7s} {kayit['sonuc']:12s} {kayit.get('bayt', 0):>8,} B "
                  f"{kayit.get('dolu_imzalar', '')}", flush=True)
    except BütçeAşıldı as e:
        print(f"BÜTÇE AŞILDI: {e}", file=sys.stderr)

    CIKTI.write_text(json.dumps(sonuclar, ensure_ascii=False, indent=1), encoding="utf-8")
    dagilim: dict[str, int] = {}
    for k in sonuclar:
        dagilim[k["sonuc"]] = dagilim.get(k["sonuc"], 0) + 1
    print(f"\nSONUÇ: {dagilim}")
    print(f"istek: {cekici.istatistik}  ->  {CIKTI}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
