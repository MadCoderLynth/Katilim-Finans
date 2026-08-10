"""XKTUM tarihsel bileşen listesi — Plan adımı 4.1.

**Tek seferlik betik.** `katilim/` paketine girmez.

## Kaynak ve yöntem

Borsa İstanbul "BIST Katılım Endeksleri Dönemsel Değişiklikleri" PDF'leri
**tam bileşen listesi vermiyor** — yalnız o dönemde endekse GİREN ve
ÇIKAN payları listeliyor. Tarihsel bileşen listesi bu yüzden iki parçadan
kuruluyor:

    bugünkü tam liste  (veri/evren/endeks_uyeligi.csv, KAP'tan, 243 kod)
  + değişim PDF'leri   (geriye doğru ters uygulanır)
  = her dönem için bileşen listesi

Geriye yürüme mantığı: bir dönemde X **girdiyse**, o dönemden ÖNCE
listede yoktu; **çıktıysa**, önce vardı. Yani en güncel listeden başlayıp
değişimleri ters çevirerek geçmiş dönemler kuruluyor.

## Ağ disiplini

PDF'ler ikili; `katilim.cekici.Çekici` metin döndürdüğü için burada
kullanılmıyor (gövdeyi bozardı). Aynı `HızSınırlayıcı` yine de
uygulanıyor ve indirilen dosya `veri/referans/ham/` altına **bir kez**
yazılıyor; ikinci koşu diskten okur.

Çalıştırma:
    .venv/Scripts/python.exe arac/xktum_referans.py --indir
    .venv/Scripts/python.exe arac/xktum_referans.py --ayristir
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from katilim.cekici import HızSınırlayıcı  # noqa: E402
from katilim.metin import normalize  # noqa: E402

REFERANS = KOK / "veri" / "referans"
HAM = REFERANS / "ham"
BILESEN_CSV = REFERANS / "xktum_bilesenler.csv"
OLCUM_JSON = REFERANS / "ayristirma_olcumu.json"

# 4.1 keşfinde bulunan dönem PDF'leri. URL'ler TAHMİN EDİLMEDİ; arama
# sonuçlarından ve duyuru sayfasından toplandı. Dosya adı kalıbı tutarsız
# (bazısı tarihli, bazısı "-1" ekli) — bu yüzden liste elle sabitlendi.
PDFLER = [
    ("2024-07-01", "2024-11-30",
     "https://www.borsaistanbul.com/files/bist-katilim-endeksleri-donemsel-degisiklikleri.pdf"),
    ("2024-12-01", "2025-04-30",
     "https://www.borsaistanbul.com/files/bist-katilim-endeksleri-01-12-2024-30-04-2025-donemi-degisiklikleri.pdf"),
    ("2025-05-01", "2025-09-30",
     "https://borsaistanbul.com/files/bist-katilim-endeksleri-01052025-30092025-donemi-degisiklikleri.pdf"),
    ("2025-10-01", "2026-04-30",
     "https://www.borsaistanbul.com/files/bist-katilim-endeksleri-donemsel-degisiklikleri-1.pdf"),
    ("2026-05-01", "2026-09-30",
     "https://www.borsaistanbul.com/files/bist-katilim-endeksleri-donemsel-degisiklikleri-01052026%E2%80%9330092026.pdf"),
]

class ReferansOkunamadi(RuntimeError):
    """PDF yapısı beklenenden farklı. 'Değişiklik yok' DEĞİLDİR (kural 7)."""


# --- İndirme ---------------------------------------------------------------


def indir(butce: int = 10) -> list[dict]:
    """PDF'leri `veri/referans/ham/` altına indirir. İdempotan: dosya varsa
    ağa çıkılmaz (kural 6: ham kaynak saklanır)."""
    import requests

    HAM.mkdir(parents=True, exist_ok=True)
    sinirlayici = HızSınırlayıcı(min_aralik=3.0, jitter=1.0, oturum_butcesi=butce)
    sonuc = []
    for bas, bit, url in PDFLER:
        ad = f"katilim_endeksleri_{bas.replace('-','')}_{bit.replace('-','')}.pdf"
        yol = HAM / ad
        kayit = {"donem_baslangic": bas, "donem_bitis": bit, "url": url, "dosya": ad}
        if yol.exists():
            kayit["durum"] = "ZATEN_VARDI"
            kayit["bayt"] = yol.stat().st_size
        else:
            sinirlayici.bekle()
            y = requests.get(url, timeout=60, headers={
                "User-Agent": "katilim-motor/0.1 (arastirma amacli)"})
            kayit["http"] = y.status_code
            if y.status_code == 200 and y.content[:4] == b"%PDF":
                yol.write_bytes(y.content)
                kayit["durum"] = "INDIRILDI"
                kayit["bayt"] = len(y.content)
            else:
                # 200 dönen ama PDF olmayan gövde sessizce kabul edilmez.
                kayit["durum"] = "HATA"
                kayit["not"] = f"ilk baytlar: {y.content[:16]!r}"
        print(f"  {bas}..{bit}  {kayit['durum']:12s} {kayit.get('bayt', 0):>9,} B  {ad}")
        sonuc.append(kayit)
    return sonuc


# --- Ayrıştırma ------------------------------------------------------------


@dataclass
class DonemDegisimi:
    donem_baslangic: str
    donem_bitis: str
    kaynak_dosya: str
    giren: list[str] = field(default_factory=list)
    cikan: list[str] = field(default_factory=list)
    yedek: list[str] = field(default_factory=list)   # endekse GİRMİŞ değil
    sira_no: dict = field(default_factory=dict)      # PDF'in kendi NO sütunu
    self_check: str = ""                             # NO sütunuyla mutabakat
    basliktaki_donem: str = ""
    duyuru_tarihi: str = ""
    uyarilar: list[str] = field(default_factory=list)


_TICKER_RE = re.compile(r"\b[A-Z]{3,6}\b")
# PDF başlığındaki dönem: "01/05/2025-30/09/2025" veya "01.05.2026-30.09.2026"
_BASLIK_DONEM_RE = re.compile(
    r"(\d{2})[./](\d{2})[./](\d{4})\s*[-–]\s*(\d{2})[./](\d{2})[./](\d{4})"
)


# --- Bant bazlı ayıklama ---------------------------------------------------
#
# Neden sayfa değil BANT: 01.12.2024 PDF'inde XKTUM listesi 2. sayfaya
# taşıyor ve o sayfanın ALTINDA "BIST KATILIM 100 ENDEKSİ" tablosu var.
# Sayfa imzasıyla çalışan ilk sürüm ikisini birden XKTUM sanıyordu —
# hatayı `yedek` sayacı yakaladı (XKTUM'da yedek pay listesi olmaz,
# alt endekslerde olur). Sessiz kirlenme örneği.

# Bir endeks bölümünün başlığı: "BIST KATILIM TÜM ENDEKSİ" gibi.
_ENDEKS_BASLIGI_RE = re.compile(r"^bist katilim .{1,30} endeksi$")
_XKTUM_BASLIGI = "bist katilim tum endeksi"

# Bölüm başlıkları — PDF'in kendi sözcükleri ("dahil edilecek" DEĞİL).
_BOLUM_IMZALARI = {
    "alinacak": "GIREN",
    "cikarilacak": "CIKAN",
    "yedek": "YEDEK",  # alt endekslerde var; XKTUM'da OLMAMALI
}

# Pay kodu sütununun çıpası: "PAY KODU" başlığındaki `PAY` sözcüğü.
# Ölçüldü: veri satırındaki pay kodunun x0'ı bu sözcüğün x0'ına oturuyor
# (5 PDF'in hepsinde; ör. PAY@82 -> AKYHO@82, PAY@323 -> SONME@323).
_SUTUN_TOLERANS = 3.0

# Başlığın kendi sözcükleri pay kodu görünümünde olabilir — `PAY` tam da
# çıpanın x0'ında duruyor ve `[A-Z]{3,6}` kalıbına uyuyor. Elenmezse her
# bölüme sahte bir "PAY" kodu ekleniyor (ölçüldü: 5 PDF'de 5 kez).
_YAPISAL_SOZCUKLER = {
    "pay", "kodu", "no", "bulten", "adi", "paylar",
    "alinacak", "cikarilacak", "yedek", "bist", "katilim", "tum", "endeksi",
}


def _satirlar(sayfa) -> list[tuple[float, list[dict]]]:
    """Sözcükleri satırlara gruplar; (y, soldan sağa sözcükler)."""
    kova: dict[int, list[dict]] = {}
    for w in sayfa.extract_words():
        kova.setdefault(round(w["top"]), []).append(w)
    return [(y, sorted(kova[y], key=lambda a: a["x0"])) for y in sorted(kova)]


def _endeks_bantlari(satirlar) -> list[tuple[str, float, float]]:
    """(endeks_adi, bant_ust_y, bant_alt_y) — başlıktan sonraki başlığa."""
    basliklar = []
    for y, ws in satirlar:
        ad = normalize(" ".join(w["text"] for w in ws))
        if _ENDEKS_BASLIGI_RE.match(ad):
            basliklar.append((ad, y))
    bantlar = []
    for i, (ad, y) in enumerate(basliklar):
        alt = basliklar[i + 1][1] if i + 1 < len(basliklar) else float("inf")
        bantlar.append((ad, y, alt))
    return bantlar


def _sutun_capalari(bant_satirlari) -> list[tuple[float, str]]:
    """Bantta (pay_kodu_sutunu_x0, bölüm) çiftleri.

    İki kademe, ikisi de içerikten:
      1. `ALINACAK/ÇIKARILACAK/YEDEK` sözcükleri bölümlerin x sınırlarını verir.
      2. `PAY` başlık sözcükleri pay kodu sütununun x0'ını verir.
    Her `PAY` çıpası, x'ini kapsayan bölüme atanır.
    """
    bolum_baslari: list[tuple[float, str]] = []
    pay_capalari: list[float] = []
    no_capalari: list[float] = []
    for _y, ws in bant_satirlari:
        for w in ws:
            n = normalize(w["text"])
            if n in _BOLUM_IMZALARI:
                bolum_baslari.append((w["x0"], _BOLUM_IMZALARI[n]))
            elif n == "pay":
                pay_capalari.append(w["x0"])
            elif n == "no":
                no_capalari.append(w["x0"])
    bolum_baslari.sort()

    def _bolumle(x: float) -> str | None:
        bolum = None
        for bx, ad in bolum_baslari:
            if bx <= x:
                bolum = ad
            else:
                break
        return bolum

    capalar = [(x, _bolumle(x), "KOD") for x in sorted(set(pay_capalari))]
    capalar += [(x, _bolumle(x), "NO") for x in sorted(set(no_capalari))]
    return [(x, b, tur) for x, b, tur in capalar if b]


def ayristir(yol: Path, bas: str, bit: str) -> DonemDegisimi:
    """Bir dönem PDF'inden XKTUM giren/çıkan pay kodlarını çıkarır.

    Yalnız **BIST KATILIM TÜM** bandı okunuyor: alt endeksler (30/50/100)
    likidite ve fiili dolaşım şartlarına da bağlı; uygunluk kararımızın
    karşılığı XKTUM.
    """
    import pdfplumber

    d = DonemDegisimi(donem_baslangic=bas, donem_bitis=bit, kaynak_dosya=yol.name)
    bant_sayisi = 0
    with pdfplumber.open(yol) as pdf:
        tam_metin = chr(10).join((s.extract_text() or "") for s in pdf.pages)
        for sayfa in pdf.pages:
            satirlar = _satirlar(sayfa)
            for ad, ust, alt in _endeks_bantlari(satirlar):
                if ad != _XKTUM_BASLIGI:
                    continue
                bant_sayisi += 1
                bant = [(y, ws) for y, ws in satirlar if ust < y < alt]
                capalar = _sutun_capalari(bant)
                if not capalar:
                    d.uyarilar.append(f"{yol.name}: XKTUM bandında sütun çıpası yok")
                    continue
                for _y, ws in bant:
                    for w in ws:
                        metin_w = w["text"].strip()
                        for x, bolum, tur in capalar:
                            if abs(w["x0"] - x) > _SUTUN_TOLERANS:
                                continue
                            if tur == "NO":
                                if metin_w.isdigit():
                                    d.sira_no.setdefault(bolum, []).append(int(metin_w))
                                break
                            kod = metin_w.upper()
                            if not _TICKER_RE.fullmatch(kod):
                                break
                            if normalize(kod) in _YAPISAL_SOZCUKLER:
                                break
                            hedef = {"GIREN": d.giren, "CIKAN": d.cikan,
                                     "YEDEK": d.yedek}[bolum]
                            if kod not in hedef:
                                hedef.append(kod)
                            break

    m = _BASLIK_DONEM_RE.search(tam_metin)
    if m:
        d.basliktaki_donem = (
            f"{m.group(1)}.{m.group(2)}.{m.group(3)}-{m.group(4)}.{m.group(5)}.{m.group(6)}"
        )
        bekleniyor = datetime.strptime(bas, "%Y-%m-%d").strftime("%d.%m.%Y")
        if not d.basliktaki_donem.startswith(bekleniyor):
            d.uyarilar.append(
                f"başlıktaki dönem ({d.basliktaki_donem}) beklenenle ({bekleniyor}) tutmuyor"
            )
    else:
        d.uyarilar.append("PDF başlığında dönem bulunamadı")

    # Kural 7: "değişiklik yok" ile "yapıyı okuyamadım" ayrı şeyler.
    if bant_sayisi == 0:
        raise ReferansOkunamadi(
            f"{yol.name}: 'BIST KATILIM TÜM ENDEKSİ' bandı bulunamadı — "
            "PDF yapısı değişmiş olabilir. Bu 'değişiklik yok' anlamına GELMEZ."
        )
    if d.yedek:
        # XKTUM'da yedek pay listesi yok. Çıktıysa bant bir alt endekse taşmış.
        raise ReferansOkunamadi(
            f"{yol.name}: XKTUM bandında YEDEK PAYLAR çıktı ({len(d.yedek)} kod) — "
            "bant bir alt endeksin tablosuna taşmış olmalı."
        )
    if not d.giren and not d.cikan:
        d.uyarilar.append("XKTUM bandı bulundu ama giren/çıkan çıkarılamadı")

    # SELF-CHECK: PDF kendi satırlarını 1..N diye numaralıyor. Ayıkladığımız
    # kod sayısı bu N ile tutmalı. Tutmuyorsa ya sütun kaydı ya satır düştü.
    # (KAFİF self-check'iyle aynı disiplin: kaynağın kendi aritmetiğini kapıla.)
    sapmalar = []
    for bolum, liste in (("GIREN", d.giren), ("CIKAN", d.cikan)):
        nolar = d.sira_no.get(bolum, [])
        if not nolar:
            sapmalar.append(f"{bolum}: NO sütunu okunamadı")
        elif max(nolar) != len(liste):
            sapmalar.append(f"{bolum}: PDF {max(nolar)} satır diyor, {len(liste)} kod ayıklandı")
    d.self_check = "GEÇTİ" if not sapmalar else "KALDI: " + "; ".join(sapmalar)
    return d


# --- Bileşen listesinin geriye kurulması ------------------------------------


# Duyuru tarihi = PDF'in oluşturulma zamanı. Bağımsız doğrulandı: 01.05.2026
# dönemi için borsaistanbul.com duyuru sayfası da 27.04.2026 diyor.
# ÖNEMLİ: gerçek veri kesim noktası yürürlük tarihi değil DUYURU tarihidir —
# duyurudan sonra yayımlanan KAFİF o revizyonu etkileyemez.
def duyuru_tarihi(yol: Path) -> str | None:
    import pdfplumber

    with pdfplumber.open(yol) as pdf:
        ham = (pdf.metadata or {}).get("CreationDate") or ""
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", ham)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def guncel_xktum(yol: Path) -> tuple[set[str], str]:
    """KAP'ın bugünkü XKTUM listesi — geriye yürümenin çıpası."""
    uyeler, tarihler = set(), set()
    with open(yol, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["endeks_adi"].strip() == "BIST KATILIM TUM":
                uyeler.add(r["ticker"].strip())
                tarihler.add(r["olcum_tarihi"].strip())
    if not uyeler:
        # Kural 7: boş küme "endekste kimse yok" demek değil, okuyamadım demek.
        raise ReferansOkunamadi(
            f"{yol.name}: 'BIST KATILIM TUM' satırı bulunamadı"
        )
    return uyeler, sorted(tarihler)[-1]


BILESEN_BASLIKLARI = [
    "ticker", "donem_baslangic", "donem_bitis", "endekste_mi", "kaynak_dosya",
]

# 4.2 iki yardımcı tablo daha istiyor. Sebep: `katilim/` paketi PDF'lere
# (ve `pdfplumber`'a) bağlanmamalı; mutabakat bu CSV'lerden okur.
DONEM_BASLIKLARI = [
    "donem_baslangic", "donem_bitis", "duyuru_tarihi", "uye_sayisi",
    "giren_sayisi", "cikan_sayisi", "kaynak_dosya",
]
OLAY_BASLIKLARI = ["ticker", "donem_baslangic", "olay", "kaynak_dosya"]
DONEM_CSV = REFERANS / "xktum_donemler.csv"
OLAY_CSV = REFERANS / "xktum_olaylar.csv"


def donem_ve_olay_tablolari(degisimler, tanilar) -> tuple[list[dict], list[dict]]:
    """Dönem sınırları (+DUYURU tarihi) ve giriş/çıkış olayları.

    Olaylar **PDF'in kendi listelerinden** geliyor, bileşen kümelerinin
    farkından değil: fark almak, geriye yürümede tutmayan üç kodu
    (EFORC/DAGHL/PEHOL) sessizce yutardı.
    """
    uye = {t["baslangic"]: t["uye"] for t in tanilar["donemler"]}
    donemler, olaylar = [], []
    for d in degisimler:
        donemler.append({
            "donem_baslangic": d.donem_baslangic,
            "donem_bitis": d.donem_bitis,
            "duyuru_tarihi": d.duyuru_tarihi,
            "uye_sayisi": uye.get(d.donem_baslangic, ""),
            "giren_sayisi": len(d.giren),
            "cikan_sayisi": len(d.cikan),
            "kaynak_dosya": d.kaynak_dosya,
        })
        for t in d.giren:
            olaylar.append({"ticker": t, "donem_baslangic": d.donem_baslangic,
                            "olay": "GIREN", "kaynak_dosya": d.kaynak_dosya})
        for t in d.cikan:
            olaylar.append({"ticker": t, "donem_baslangic": d.donem_baslangic,
                            "olay": "CIKAN", "kaynak_dosya": d.kaynak_dosya})
    return donemler, olaylar


def kur(degisimler: list[DonemDegisimi], uyeler: set[str], olcum: str,
        evren: set[str]) -> tuple[list[dict], dict]:
    """Bugünden geriye yürüyerek her dönemin bileşen listesini kurar.

    Bir dönemde X **girdiyse** o dönemden önce listede yoktu; **çıktıysa**
    vardı. Yani `önceki = (şimdiki − giren) ∪ çıkan`.
    """
    satirlar: list[dict] = []
    tanilar = {"donemler": [], "tutarsizlik": []}

    # En güncel dönem: çıpa KAP'ın kendi listesi, PDF değil.
    son = degisimler[-1]
    kaynak = f"endeks_uyeligi.csv (KAP, {olcum})"
    donem_uyeleri = [(son.donem_baslangic, son.donem_bitis, set(uyeler), kaynak)]

    simdiki = set(uyeler)
    for d in reversed(degisimler):
        # Tutarlılık: bu dönemde giren üye olmalı, çıkan olmamalı.
        eksik = sorted(set(d.giren) - simdiki)
        fazla = sorted(set(d.cikan) & simdiki)
        if eksik or fazla:
            tanilar["tutarsizlik"].append({
                "donem": d.donem_baslangic,
                "giren_ama_uye_degil": eksik,
                "cikan_ama_hala_uye": fazla,
                # Evrende olmayan kod = borsadan çıkmış/birleşmiş şirket.
                # Olağanüstü çıkarmalar dönemsel PDF'lerde görünmez.
                "evrende_olmayan": sorted(set(eksik + fazla) - evren),
            })
        onceki = (simdiki - set(d.giren)) | set(d.cikan)
        # Bu dönemin kendi PDF'i, KENDİNDEN ÖNCEKİ dönemin listesini üretir.
        i = degisimler.index(d)
        if i > 0:
            oncekinin = degisimler[i - 1]
            donem_uyeleri.append(
                (oncekinin.donem_baslangic, oncekinin.donem_bitis, onceki,
                 d.kaynak_dosya)
            )
        simdiki = onceki

    donem_uyeleri.sort(key=lambda t: t[0])
    for bas, bit, uye, kaynak in donem_uyeleri:
        tanilar["donemler"].append({"baslangic": bas, "bitis": bit,
                                    "uye": len(uye), "kaynak": kaynak})
        for t in sorted(uye):
            satirlar.append({"ticker": t, "donem_baslangic": bas,
                             "donem_bitis": bit, "endekste_mi": "EVET",
                             "kaynak_dosya": kaynak})
        # HAYIR satırları yalnız bugünkü evren için yazılıyor. Borsadan
        # çıkmış kodlar için "hayır" diyemeyiz — o kod hakkında görüşümüz yok.
        for t in sorted(evren - uye):
            satirlar.append({"ticker": t, "donem_baslangic": bas,
                             "donem_bitis": bit, "endekste_mi": "HAYIR",
                             "kaynak_dosya": kaynak})
    return satirlar, tanilar


def main() -> int:
    ap = argparse.ArgumentParser(description="Plan 4.1 — XKTUM tarihsel referans")
    ap.add_argument("--indir", action="store_true")
    ap.add_argument("--ayristir", action="store_true")
    ap.add_argument("--kur", action="store_true")
    ap.add_argument("--butce", type=int, default=10)
    args = ap.parse_args()

    if args.indir:
        print("PDF indirme:")
        kayitlar = indir(args.butce)
        (REFERANS / "indirme.json").write_text(
            json.dumps(kayitlar, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    if args.ayristir:
        print("\nPDF ayrıştırma:")
        degisimler = []
        for bas, bit, _ in PDFLER:
            ad = f"katilim_endeksleri_{bas.replace('-','')}_{bit.replace('-','')}.pdf"
            yol = HAM / ad
            if not yol.exists():
                print(f"  {bas}..{bit}  DOSYA YOK: {ad}")
                continue
            try:
                d = ayristir(yol, bas, bit)
            except ReferansOkunamadi as e:
                print(f"  {bas}..{bit}  OKUNAMADI: {e}")
                continue
            degisimler.append(d)
            print(f"  {bas}..{bit}  giren={len(d.giren):3d} çıkan={len(d.cikan):3d} "
                  f"self-check={d.self_check.split(':')[0]:6s} "
                  f"başlık={d.basliktaki_donem or '?'}"
                  + (f"  UYARI: {'; '.join(d.uyarilar)}" if d.uyarilar else ""))
        OLCUM_JSON.parent.mkdir(parents=True, exist_ok=True)
        OLCUM_JSON.write_text(
            json.dumps([d.__dict__ for d in degisimler], ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        print(f"\nölçüm yazıldı: {OLCUM_JSON}")

    if args.kur:
        print("\nBileşen listesi kuruluyor:")
        ham = json.loads(OLCUM_JSON.read_text(encoding="utf-8"))
        degisimler = [DonemDegisimi(**k) for k in ham]
        for d in degisimler:
            d.duyuru_tarihi = duyuru_tarihi(HAM / d.kaynak_dosya) or ""
        uyeler, olcum = guncel_xktum(KOK / "veri" / "evren" / "endeks_uyeligi.csv")
        evren = set()
        with open(KOK / "veri" / "evren" / "sirketler.csv", encoding="utf-8-sig",
                  newline="") as f:
            for r in csv.DictReader(f):
                evren.add(r["ticker"].strip())
        print(f"  çıpa: KAP XKTUM {len(uyeler)} kod ({olcum}) · evren {len(evren)} kod")
        satirlar, tanilar = kur(degisimler, uyeler, olcum, evren)
        BILESEN_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(BILESEN_CSV, "w", encoding="utf-8", newline="") as f:
            y = csv.DictWriter(f, fieldnames=BILESEN_BASLIKLARI)
            y.writeheader()
            y.writerows(satirlar)
        for t in tanilar["donemler"]:
            dd = next((x for x in degisimler
                       if x.donem_baslangic == t["baslangic"]), None)
            print(f"  {t['baslangic']}..{t['bitis']}  üye={t['uye']:3d}  "
                  f"duyuru={dd.duyuru_tarihi if dd else '?':10s}  "
                  f"kaynak={t['kaynak'][:46]}")
        for t in tanilar["tutarsizlik"]:
            print(f"  ! {t['donem']}  giren-ama-üye-değil={t['giren_ama_uye_degil']}"
                  f"  evrende-olmayan={t['evrende_olmayan']}")
        (REFERANS / "kurulum_tanilari.json").write_text(
            json.dumps(tanilar, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n  {len(satirlar):,} satır -> {BILESEN_CSV}")

        donemler, olaylar = donem_ve_olay_tablolari(degisimler, tanilar)
        for yol, basliklar, veri in ((DONEM_CSV, DONEM_BASLIKLARI, donemler),
                                     (OLAY_CSV, OLAY_BASLIKLARI, olaylar)):
            with open(yol, "w", encoding="utf-8", newline="") as f:
                y = csv.DictWriter(f, fieldnames=basliklar)
                y.writeheader()
                y.writerows(veri)
            print(f"  {len(veri):,} satır -> {yol.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
