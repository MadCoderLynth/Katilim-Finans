"""Tek seferlik tarihsel derinlik keşfi — Plan adımı 2.0.

**Bu üretim kodu değildir.** `katilim/` paketine girmez, API'si kararlı
değildir. Tek bir soruyu ölçer: KAP bildirim sorgusunun 1 yıllık penceresinin
ötesine geçen bir yol var mı?

Ölçüm turu ilkeleri (1.0'dan devralındı):
  - Bütçe düşük (30 istek). `BütçeAşıldı` yakalanır ama YÜKSELTİLMEZ.
  - Önbellek açık; ama sonda 0 bilinçli olarak `zorla` çeker (pencerenin
    bugün nerede durduğu soruluyor, dünkü kopya cevap değil).
  - Ölçüm JSON'a yazılır, rapor ondan yazılır.

Üç ölçüm aracı — 1.0'da kullanılmayan ve ayrımı asıl yapan şey:

  1. **Sunucunun kendi ilan ettiği pencere.** Sonuç sayfası gövdesinde
     "Başlangıç Tarihi: 05-08-2025 / Bitiş Tarihi: 05-08-2026" yazıyor.
     Bir parametre pencereyi oynattıysa sayfa bunu kendisi söyler; kayıt
     sayısına bakarak tahmin etmeye gerek yok.
  2. **Sunucunun kendi kayıt sayısı.** "98 bildirim bulundu." Bu sayı
     render edilen satır sayısından FARKLIYSA sayfalama var demektir —
     sayfalama sondasının asıl kanıtı bu.
  3. **RSC yükündeki yapılandırılmış kayıtlar.** `disclosureBasic` nesnesi
     `disclosureIndex` (= bildirim_id), `publishDate`, `disclosureClass`,
     `year`, `period` taşıyor. Checkbox `id`'si kazımaya gerek yok.

Değiştirilemez kural 7 burada koda giriyor: "0 kayıt" ile "sayfayı
okuyamadım" ayrı durumlar. Beklenen çıpaların (sunucu sayısı, satırlar,
boş-sonuç metni) hiçbiri yoksa `SayfaOkunamadi` fırlatılır.

Çalıştırma:
    .venv/Scripts/python.exe arac/derinlik_kesfi.py --asama 0   # pencere kaydı mı
    .venv/Scripts/python.exe arac/derinlik_kesfi.py --asama 1   # detaylı sorgulama formu
    .venv/Scripts/python.exe arac/derinlik_kesfi.py --asama 2   # parametre sondaları
    .venv/Scripts/python.exe arac/derinlik_kesfi.py --asama 3   # ozet / kfif rotaları
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from datetime import date, datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from bs4 import BeautifulSoup  # noqa: E402

from katilim.cekici import BütçeAşıldı, HızSınırlayıcı, ÇekimHatası, Çekici  # noqa: E402

ONBELLEK = KOK / "veri" / "onbellek"
ONBELLEK_ARSIV = ONBELLEK / "arsiv"
OLCUM_JSON = ONBELLEK / "derinlik_kesfi_olcum.json"

THY_UUID = "4028e4a140f2ed720140f376bebb01a7"
THY_SLUG = "1107-turk-hava-yollari-a-o"

SONUC_URL = f"https://kap.org.tr/tr/bildirim-sorgu-sonuc?member={THY_UUID}"
SORGU_URL = "https://kap.org.tr/tr/bildirim-sorgu"
OZET_URL = f"https://kap.org.tr/tr/sirket-bilgileri/ozet/{THY_SLUG}"
KFIF_URL = f"https://kap.org.tr/tr/kfif/{THY_SLUG}"

# 05.08.2026 ölçümünün tabanı (ROTA_KESFI_RAPORU §3). Sonda 0 bunu diskteki
# gövdeyi yeniden ayrıştırarak da doğruluyor; sabit yalnız rapor içindir.
TABAN = {"kayit": 98, "en_eski": "05.08.2025 19:15", "olcum_tarihi": "2026-08-05"}


class SayfaOkunamadi(RuntimeError):
    """Beklenen çıpaların hiçbiri yok. Bu 'sonuç yok' DEĞİLDİR (kural 7)."""


# --- Ayıklama --------------------------------------------------------------


def _json_nesnesi(metin: str, acilis: int) -> str:
    """`metin[acilis]` konumundaki '{' ile eşleşen '}' arasını döndürür.

    Alan sırasına dayanan regex yerine süslü parantez eşlemesi: KAP alan
    sırasını değiştirirse regex sessizce boş küme döndürürdü.
    """
    derinlik = 0
    dizede = False
    kacis = False
    for i in range(acilis, len(metin)):
        c = metin[i]
        if kacis:
            kacis = False
            continue
        if c == "\\":
            kacis = True
            continue
        if c == '"':
            dizede = not dizede
            continue
        if dizede:
            continue
        if c == "{":
            derinlik += 1
        elif c == "}":
            derinlik -= 1
            if derinlik == 0:
                return metin[acilis : i + 1]
    raise SayfaOkunamadi("JSON nesnesi kapanmadan gövde bitti")


def rsc_bildirimleri(html: str) -> list[dict]:
    """RSC yükündeki `disclosureBasic` kayıtları.

    Yük script string'i içinde, tırnaklar kaçışlı; önce kaçış geri alınır.
    """
    duz = html.replace('\\"', '"')
    kayitlar = []
    for m in re.finditer(r'"disclosureBasic":\s*\{', duz):
        acilis = duz.index("{", m.end() - 1)
        try:
            kayitlar.append(json.loads(_json_nesnesi(duz, acilis)))
        except (json.JSONDecodeError, SayfaOkunamadi):
            continue
    return kayitlar


def dom_bildirimleri(html: str) -> list[str]:
    """Satırdaki checkbox `id`'leri. RSC yükü kaybolursa geri düşülecek yol."""
    corba = BeautifulSoup(html, "html.parser")
    return [
        i["id"]
        for i in corba.find_all("input", {"name": "notification-checkbox"})
        if i.get("id")
    ]


def ilan_edilen_pencere(html: str) -> tuple[str | None, str | None]:
    """Sunucunun sayfaya bastığı tarih aralığı ('05-08-2025', '05-08-2026').

    Asıl ölçüm aleti: bir parametre pencereyi oynattıysa sayfa söyler.
    """
    def bul(etiket: str) -> str | None:
        m = re.search(etiket + r".{0,120}?(\d{2}-\d{2}-\d{4})", html, re.S)
        return m.group(1) if m else None

    return bul("Başlangıç Tarihi"), bul("Bitiş Tarihi")


def sunucu_kayit_sayisi(html: str) -> int | None:
    """"98 bildirim bulundu." — sunucunun kendi saydığı toplam."""
    m = re.search(r"(\d+)\s*bildirim bulundu", html)
    return int(m.group(1)) if m else None


def bos_sonuc_mu(html: str) -> bool:
    """Boş sonuç metni TABLONUN İÇİNDE mi?

    Aynı metin i18n sözlüğünde de geçiyor; gövdede aramak her sayfayı
    'boş' gösterir. 1.0'da bu ayrım iki ölçüm hatasının kaynağıydı.
    """
    corba = BeautifulSoup(html, "html.parser")
    tablo = corba.find("table")
    if tablo and re.search(r"Bildirim bulunamadı|Sonuç Bulunamadı", tablo.get_text()):
        return True
    return False


def _ts(kayit: dict) -> datetime | None:
    try:
        return datetime.strptime(kayit["publishDate"], "%d.%m.%Y %H:%M:%S")
    except (KeyError, TypeError, ValueError):
        return None


def sorgu_olc(html: str) -> dict:
    """Bir sorgu sonucu gövdesinin tam ölçüsü. Kural 7'yi kodda uygular."""
    kayitlar = rsc_bildirimleri(html)
    dom = dom_bildirimleri(html)
    sunucu = sunucu_kayit_sayisi(html)
    bos = bos_sonuc_mu(html)

    if not kayitlar and not dom and sunucu is None and not bos:
        raise SayfaOkunamadi(
            "Ne kayıt, ne sunucu sayısı, ne boş-sonuç metni bulundu — "
            "sayfa okunamadı. Bu 'sonuç yok' anlamına GELMEZ."
        )

    zamanlar = sorted(t for t in (_ts(k) for k in kayitlar) if t)
    bas, bit = ilan_edilen_pencere(html)
    olcu = {
        "sinif": "BOS" if (sunucu == 0 or (bos and not kayitlar)) else "DOLU",
        "sunucu_sayisi": sunucu,
        "rsc_kayit": len(kayitlar),
        "dom_kayit": len(dom),
        "ilan_pencere_bas": bas,
        "ilan_pencere_bit": bit,
        "en_eski": zamanlar[0].strftime("%d.%m.%Y %H:%M:%S") if zamanlar else None,
        "en_yeni": zamanlar[-1].strftime("%d.%m.%Y %H:%M:%S") if zamanlar else None,
        "idler": sorted(str(k.get("disclosureIndex")) for k in kayitlar),
        "kafif_idleri": sorted(
            str(k.get("disclosureIndex"))
            for k in kayitlar
            if "Katılım Finansı İlkeleri" in (k.get("title") or "")
        ),
        "siniflar": sorted({k.get("disclosureClass") for k in kayitlar if k.get("disclosureClass")}),
    }
    # Sayfalama kanıtı: sunucu 98 diyor ama 50 satır bastıysa sayfalama var.
    olcu["sunucu_render_farki"] = (
        None if sunucu is None else sunucu - len(kayitlar)
    )
    olcu["ilk_sira_en_yeni_mi"] = (
        None
        if len(kayitlar) < 2
        else (_ts(kayitlar[0]) or datetime.min) >= (_ts(kayitlar[-1]) or datetime.min)
    )
    return olcu


# --- Çekim -----------------------------------------------------------------


def _onbellek_yolu(url: str) -> Path:
    return ONBELLEK / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}.html"


def onbellegi_arsivle(url: str) -> Path | None:
    """`zorla` çekmeden önce diskteki kopyayı tarihiyle saklar.

    `veri/onbellek/` bir önbellek değil, telafisi olmayan arşiv (CLAUDE.md
    "Nerede kaldık"). Üzerine yazmak, 05.08.2026'da pencerede olan ama bugün
    olmayan bildirimlerin kaydını yok eder — sondanın ölçtüğü şeyi silmek olur.
    """
    p = _onbellek_yolu(url)
    if not p.exists():
        return None
    ONBELLEK_ARSIV.mkdir(parents=True, exist_ok=True)
    hedef = ONBELLEK_ARSIV / f"{p.stem}_{date.fromtimestamp(p.stat().st_mtime):%Y%m%d}.html"
    if not hedef.exists():
        shutil.copy2(p, hedef)
    return hedef


def getir_fabrikasi(gunluk: list[dict]):
    import requests

    def getir(url: str, basliklar: dict):
        t0 = time.monotonic()
        y = requests.get(url, headers=basliklar, timeout=30)
        gunluk.append(
            {
                "istenen_url": url,
                "son_url": y.url,
                "durum": y.status_code,
                "sure_sn": round(time.monotonic() - t0, 2),
                "bayt": len(y.content),
            }
        )
        return y.status_code, y.text, dict(y.headers)

    return getir


def cek(cekici: Çekici, url: str, sonuc: dict, *, zorla: bool = False) -> str | None:
    onceki = dict(cekici.istatistik)
    try:
        govde = cekici.getir(url, zorla=zorla)
    except BütçeAşıldı:
        raise
    except (ÇekimHatası, Exception) as e:  # noqa: BLE001 — keşifte her hata veridir
        sonuc["hata"] = f"{type(e).__name__}: {e}"
        return None
    sonuc["kaynak"] = (
        "onbellek" if cekici.istatistik["onbellek"] > onceki["onbellek"] else "ag"
    )
    return govde


def olc_ve_kaydet(cekici: Çekici, url: str, sonuc: dict, *, zorla: bool = False) -> dict:
    govde = cek(cekici, url, sonuc, zorla=zorla)
    if govde is None:
        return sonuc
    try:
        sonuc["olcu"] = sorgu_olc(govde)
    except SayfaOkunamadi as e:
        sonuc["olcu"] = None
        sonuc["hata"] = f"SayfaOkunamadi: {e}"
    return sonuc


# --- Sonda 0: pencere kayıyor mu -------------------------------------------


def sonda_0_kayma(cekici: Çekici) -> dict:
    """Tek istek, en yüksek bilgi değeri.

    Diskteki 05.08.2026 kopyası ÖNCE ayrıştırılır (taban), sonra aynı URL
    zorla yeniden çekilir. Karşılaştırma iki gövde arasında yapılır; rapora
    yazılmış sayılara güvenmeye gerek kalmaz.
    """
    s = {"sonda": "0 — pencere kayıyor mu", "url": SONUC_URL}

    eski_yol = _onbellek_yolu(SONUC_URL)
    if eski_yol.exists():
        s["disk_tarihi"] = f"{date.fromtimestamp(eski_yol.stat().st_mtime):%Y-%m-%d}"
        try:
            s["disk_olcu"] = sorgu_olc(
                eski_yol.read_text(encoding="utf-8", errors="ignore")
            )
        except SayfaOkunamadi as e:
            s["disk_olcu"] = None
            s["disk_hata"] = str(e)
        s["arsivlenen"] = str(onbellegi_arsivle(SONUC_URL))

    olc_ve_kaydet(cekici, SONUC_URL, s, zorla=True)
    s["bugun"] = date.today().isoformat()

    eski, yeni = s.get("disk_olcu"), s.get("olcu")
    if eski and yeni:
        eski_idler, yeni_idler = set(eski["idler"]), set(yeni["idler"])
        s["karsilastirma"] = {
            "en_eski_eski": eski["en_eski"],
            "en_eski_yeni": yeni["en_eski"],
            "pencere_basi_eski": eski["ilan_pencere_bas"],
            "pencere_basi_yeni": yeni["ilan_pencere_bas"],
            "dusen_kayit": sorted(eski_idler - yeni_idler),
            "eklenen_kayit": sorted(yeni_idler - eski_idler),
        }
        s["karar"] = (
            "KAYIYOR"
            if eski["ilan_pencere_bas"] != yeni["ilan_pencere_bas"]
            or (eski_idler - yeni_idler)
            else "SABIT"
        )
    return s


# --- Sonda 1: Detaylı Sorgulama formu --------------------------------------


def sonda_1_form(cekici: Çekici) -> dict:
    """Formun kendi söylediği alan adlarını oku; parametre TAHMİN ETME.

    1.0'da üç tarih parametresi tahmin edilmişti ve üçü de yok sayıldı.
    """
    s = {"sonda": "1 — Detaylı Sorgulama formu", "url": SORGU_URL}
    govde = cek(cekici, SORGU_URL, s)
    if govde is None:
        return s

    corba = BeautifulSoup(govde, "html.parser")
    s["form_sayisi"] = len(corba.find_all("form"))
    s["formlar"] = [
        {"action": f.get("action"), "method": f.get("method")}
        for f in corba.find_all("form")
    ]
    s["alanlar"] = [
        {
            "etiket": e.name,
            "name": e.get("name"),
            "id": e.get("id"),
            "type": e.get("type"),
            "placeholder": e.get("placeholder"),
            "opsiyonlar": [o.get("value") for o in e.find_all("option")][:20]
            if e.name == "select"
            else None,
        }
        for e in corba.find_all(["input", "select", "textarea"])
    ][:80]

    duz = govde.replace('\\"', '"')
    # Sorgunun gerçek parametre adları: RSC yükündeki JSON anahtarları.
    anahtarlar = sorted(set(re.findall(r'"([a-zA-Z][a-zA-Z0-9_]{2,40})":', duz)))
    ilgi = re.compile(
        r"date|page|index|offset|size|sort|order|dir|count|limit|from|start|end"
        r"|year|period|term|query|search|filter|disclos|subject|member|type",
        re.I,
    )
    s["ilgili_json_anahtarlari"] = [a for a in anahtarlar if ilgi.search(a)]
    s["api_izleri"] = sorted(
        set(re.findall(r'"(/[a-zA-Z0-9_\-/]*(?:api|service|query)[a-zA-Z0-9_\-/]*)"', duz))
    )
    # Sonuç sayfasına giden hazır bir bağlantı varsa parametre adları oradadır.
    s["sonuc_baglantilari"] = sorted(
        set(re.findall(r'"(/[a-z]{2}/bildirim-sorgu-sonuc[^"]*)"', duz))
    )[:20]
    s["tarih_metinleri"] = sorted(set(re.findall(r"\d{2}[.-]\d{2}[.-]\d{4}", govde)))[:20]
    return s


# --- Sonda 2/3: parametre sondaları ----------------------------------------


def parametre_sondasi(cekici: Çekici, denemeler: list[str], taban: dict) -> list[dict]:
    """Her parametre için: kayıt sayısı, ilan edilen pencere, en eski tarih.

    'Değişti mi' kararı üç ölçütle verilir; yalnız kayıt sayısına bakmak
    yanıltıcı (aynı sayı farklı pencereden de gelebilir).
    """
    sonuclar = []
    for ek in denemeler:
        s = {"parametre": ek, "url": SONUC_URL + ek}
        olc_ve_kaydet(cekici, s["url"], s)
        o = s.get("olcu")
        if o:
            s["pencere_degisti"] = o["ilan_pencere_bas"] != taban["ilan_pencere_bas"]
            s["kayit_degisti"] = o["sunucu_sayisi"] != taban["sunucu_sayisi"]
            s["idler_degisti"] = set(o["idler"]) != set(taban["idler"])
            s["yeni_id"] = sorted(set(o["idler"]) - set(taban["idler"]))
            s["sonuc"] = (
                "İŞLENDİ"
                if (s["pencere_degisti"] or s["kayit_degisti"] or s["idler_degisti"])
                else "yok sayıldı"
            )
        sonuclar.append(s)
    return sonuclar


# --- Sonda 4/5: alternatif rotalar -----------------------------------------


def sonda_4_ozet(cekici: Çekici) -> dict:
    """Şirket özet sayfası ayrı bir bildirim listesi sunuyor mu?"""
    s = {"sonda": "4 — şirket özet sayfası", "url": OZET_URL}
    govde = cek(cekici, OZET_URL, s)
    if govde is None:
        return s
    kayitlar = rsc_bildirimleri(govde)
    s["rsc_bildirim_kaydi"] = len(kayitlar)
    s["checkbox_satiri"] = len(dom_bildirimleri(govde))
    s["bildirim_linkleri"] = sorted(set(re.findall(r"/tr/Bildirim/(\d+)", govde)))[:20]
    s["sorgu_linkleri"] = sorted(
        set(re.findall(r'href="(/tr/[a-z\-]*bildirim[^"]*)"', govde))
    )[:20]
    s["sekme_basliklari"] = sorted(
        set(re.findall(r"Bildirim(?:ler)?(?:i)?\b[^<]{0,30}", govde))
    )[:15]
    s["tarih_izleri"] = sorted(set(re.findall(r"\d{2}\.\d{2}\.\d{4}", govde)))[:10]
    return s


def sonda_5_kfif(cekici: Çekici) -> dict:
    """kfif sayfası geçmiş bildirim KİMLİKLERİNE link veriyor mu?

    Sayfanın kendisi veri kaynağı olarak yasak (ROTA_KESFI_RAPORU §6);
    burada yalnız 'geçmiş dönem seçici var mı' sorusu var.
    """
    s = {"sonda": "5 — kfif dönem seçici", "url": KFIF_URL}
    govde = cek(cekici, KFIF_URL, s)
    if govde is None:
        return s
    s["bildirim_linkleri"] = sorted(set(re.findall(r"/tr/Bildirim/(\d+)", govde)))[:30]
    s["disclosure_index_izleri"] = sorted(
        set(re.findall(r'disclosureIndex\\?":\s*(\d+)', govde))
    )[:30]
    corba = BeautifulSoup(govde, "html.parser")
    s["select_alanlari"] = [
        {
            "name": e.get("name"),
            "id": e.get("id"),
            "opsiyonlar": [o.get_text(" ", strip=True) for o in e.find_all("option")][:20],
        }
        for e in corba.find_all("select")
    ]
    s["donem_metinleri"] = sorted(set(re.findall(r"20\d{2}\s*/\s*[^<\"]{0,12}", govde)))[:20]
    s["yil_izleri"] = sorted(set(re.findall(r'"year"\s*:\s*(\d{4})', govde.replace('\\"', '"'))))
    s["periyot_izleri"] = sorted(set(re.findall(r'"donem"\s*:\s*"([^"]{0,20})"', govde.replace('\\"', '"'))))
    return s


def sonda_6_alternatif_rota(cekici: Çekici, url: str, taban: dict | None) -> dict:
    """Sorgu sonucu şeklinde olan başka bir rotayı aynı ölçütlerle ölç.

    Sonda 4, özet sayfasında `/tr/sirket-bildirimleri/{id}-{slug}` bağlantısını
    buldu. Aynı bildirim listesini başka bir pencereyle sunuyor olabilir;
    ölçmeden bilinmez.
    """
    s = {"sonda": "6 — alternatif bildirim rotası", "url": url}
    olc_ve_kaydet(cekici, url, s)
    o = s.get("olcu")
    if o and taban:
        s["pencere_degisti"] = o["ilan_pencere_bas"] != taban["ilan_pencere_bas"]
        s["kayit_degisti"] = o["sunucu_sayisi"] != taban["sunucu_sayisi"]
        s["yeni_id"] = sorted(set(o["idler"]) - set(taban["idler"]))
        s["daha_eski_mi"] = bool(o["en_eski"] and taban["en_eski"] and o["en_eski"] < taban["en_eski"])
    return s


def sonda_7_js_ucu(cekici: Çekici, url: str) -> dict:
    """Sonda 1'in devamı: formun HTML `action`'ı yok, çünkü form React.

    Detaylı Sorgulama sayfası kendi yapılandırmasında iki taban adres
    açıklıyor: `clientBaseUrl` (kap.org.tr) ve `serverBaseUrl`
    (kapsitebackend.mkk.com.tr). Yani "form nereye gönderiyor" sorusunun
    cevabı bir JSON ucu; yolu sayfanın kendi JS parçalarında yazılı.

    Burada yol TAHMİN EDİLMİYOR, sayfanın kendi verdiği dizeler okunuyor.
    """
    s = {"sonda": "7 — JS parçasında sorgu ucu", "url": url}
    govde = cek(cekici, url, s)
    if govde is None:
        return s
    s["bayt"] = len(govde)
    yollar = set()
    for kalip in (
        r'"(/[a-zA-Z0-9_\-/{}\.]{4,90})"',
        r"`(/[a-zA-Z0-9_\-/${}\.]{4,90})`",
    ):
        for y in re.findall(kalip, govde):
            if re.search(r"disclosure|notification|bildirim|inquiry|search|query|member|api", y, re.I):
                yollar.add(y)
    s["aday_yollar"] = sorted(yollar)[:60]
    s["backend_izi"] = sorted(set(re.findall(r"https://[a-z0-9.\-]*mkk\.com\.tr[a-zA-Z0-9_\-/]*", govde)))[:10]
    return s


# --- Ana akış --------------------------------------------------------------


def olcum_oku() -> dict:
    if OLCUM_JSON.exists():
        return json.loads(OLCUM_JSON.read_text(encoding="utf-8"))
    return {}


def olcum_yaz(rapor: dict) -> None:
    OLCUM_JSON.write_text(
        json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Plan 2.0 — tarihsel derinlik keşfi")
    ap.add_argument("--asama", type=int, required=True, choices=[0, 1, 2, 3, 4, 5])
    ap.add_argument(
        "--url",
        action="append",
        default=None,
        help="Aşama 4 için ölçülecek alternatif rota (birden çok kez verilebilir).",
    )
    ap.add_argument(
        "--parametre",
        action="append",
        default=None,
        help="Aşama 2 için denenecek sorgu eki (birden çok kez verilebilir).",
    )
    ap.add_argument("--butce", type=int, default=30, help="oturum bütçesi (yükseltilmez)")
    args = ap.parse_args()

    sinirlayici = HızSınırlayıcı(min_aralik=2.0, jitter=1.0, oturum_butcesi=args.butce)
    gunluk: list[dict] = []
    cekici = Çekici(ONBELLEK, sinirlayici=sinirlayici, getir_fn=getir_fabrikasi(gunluk))

    rapor = olcum_oku()
    rapor.setdefault("asamalar", {})
    rapor["son_calistirma"] = datetime.now().isoformat(timespec="seconds")
    rapor["taban_1_0"] = TABAN

    try:
        if args.asama == 0:
            rapor["asamalar"]["0"] = sonda_0_kayma(cekici)
        elif args.asama == 1:
            rapor["asamalar"]["1"] = sonda_1_form(cekici)
        elif args.asama == 2:
            taban = (rapor.get("asamalar", {}).get("0") or {}).get("olcu")
            if not taban:
                print("Önce --asama 0 koşulmalı (taban ölçüm yok).")
                return 2
            denemeler = args.parametre or []
            if not denemeler:
                print("--parametre verilmedi; denenecek bir şey yok.")
                return 2
            rapor["asamalar"].setdefault("2", []).extend(
                parametre_sondasi(cekici, denemeler, taban)
            )
        elif args.asama == 3:
            rapor["asamalar"]["4"] = sonda_4_ozet(cekici)
            rapor["asamalar"]["5"] = sonda_5_kfif(cekici)
        elif args.asama == 4:
            taban = (rapor.get("asamalar", {}).get("0") or {}).get("olcu")
            for u in args.url or []:
                rapor["asamalar"].setdefault("6", []).append(
                    sonda_6_alternatif_rota(cekici, u, taban)
                )
        elif args.asama == 5:
            for u in args.url or []:
                rapor["asamalar"].setdefault("7", []).append(sonda_7_js_ucu(cekici, u))
    except BütçeAşıldı as e:
        rapor["kesildi"] = str(e)
        print(f"BÜTÇE AŞILDI: {e}")

    rapor["istatistik"] = dict(cekici.istatistik)
    rapor["sinirlayici_sayac"] = sinirlayici.kullanilan
    rapor.setdefault("http_gunlugu", []).extend(gunluk)
    olcum_yaz(rapor)

    cikti = rapor["asamalar"].get(str(args.asama)) or rapor["asamalar"]
    print(json.dumps(cikti, ensure_ascii=False, indent=2, default=str)[:9000])
    print(f"\n[istek: {sinirlayici.kullanilan}/{args.butce} · ölçüm: {OLCUM_JSON}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
