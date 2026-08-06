"""Tek seferlik KAP rota keşfi — Plan adımı 1.0.

**Bu üretim kodu değildir.** `katilim/` paketine girmez, testi yoktur, API'si
kararlı değildir. Amacı tek bir soruyu ölçmek: Faz 1 toplama katmanı hangi
rotaların üstüne, hangi teknikle (requests / playwright) kurulabilir?

Ölçüm turu ilkeleri:
  - Bütçe düşük (50 istek). `BütçeAşıldı` yakalanır ama YÜKSELTİLMEZ;
    o ana kadar ölçülen neyse raporlanır.
  - Önbellek açık: betik yeniden çalıştırıldığında zaten çekilmiş URL için
    ağa çıkılmaz. Bu yüzden "kaç istek harcandı" sorusunun doğru cevabı
    süreç sayacı değil, önbellek indeksidir (bkz. `agdan_cekilen_toplam`).
  - Ölçüm sonuçları JSON olarak diske yazılır; rapor ondan yazılır.

Çalıştırma:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe arac/rota_kesfi.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from bs4 import BeautifulSoup  # noqa: E402

from katilim.ayristirici import AyristirmaHatasi, ayristir  # noqa: E402
from katilim.cekici import BütçeAşıldı, HızSınırlayıcı, ÇekimHatası, Çekici  # noqa: E402
from katilim.oranlar import self_check  # noqa: E402

ONBELLEK = KOK / "veri" / "onbellek"
OLCUM_JSON = ONBELLEK / "rota_kesfi_olcum.json"
YEREL_THY = KOK / "veri" / "ham" / "THYAO_2025_yillik.html"

ROTA_1 = "https://kap.org.tr/tr/bist-sirketler"
ROTA_3 = "https://kap.org.tr/tr/Bildirim/1566002"

# KAP kimlikleri tirelisiz 32 haneli hex (örn. 4028e4a140f2ed720140f376bebb01a7)
UUID_RE = re.compile(r"\b[0-9a-f]{32}\b")
# Şirket listesi sayfası verisini RSC (Next.js flight) yükü içinde gömülü
# taşıyor. Kaydın tamamı tek satırda, alanları sabit sırada.
KAYIT_RE = re.compile(r"\{\"mkkMemberOid\":.*?\"kapMemberType\":\"[^\"]*\"\}")


# --- Ölçüm yardımcıları ----------------------------------------------------


def govde_olc(html: str) -> dict:
    """Bir HTML gövdesinin 'dolu mu, iskelet mi' ölçüsü.

    Ayırt edici sinyal: görünür metin / toplam bayt oranı. JS iskeletinde
    gövde büyüktür ama görünür metin birkaç yüz karakterdir.
    """
    corba = BeautifulSoup(html, "html.parser")
    olcu = {
        "uzunluk": len(html),
        "tablo_sayisi": len(corba.find_all("table")),
        "tr_sayisi": len(corba.find_all("tr")),
        "script_sayisi": len(corba.find_all("script")),
        "a_sayisi": len(corba.find_all("a")),
        "next_data_var": "__NEXT_DATA__" in html,
        "nuxt_var": "__NUXT__" in html or "window.__" in html,
    }
    for e in corba(["script", "style", "noscript"]):
        e.decompose()
    metin = corba.get_text(" ", strip=True)
    olcu["gorunur_metin"] = len(metin)
    olcu["metin_orani"] = round(len(metin) / max(1, len(html)), 4)
    olcu["metin_ornegi"] = metin[:300]
    return olcu


def uuid_bul(html: str) -> list[str]:
    return sorted(set(UUID_RE.findall(html)))


def rsc_kayitlari(html: str) -> list[dict]:
    """Şirket listesi sayfasındaki gömülü JSON kayıtlarını çıkarır.

    Uyarı: bu HTML'in içindeki bir script string'i, yani tırnaklar kaçışlı.
    Önce kaçışı geri al, sonra JSON olarak oku.
    """
    duz = html.replace('\\"', '"')
    kayitlar = []
    for ham in KAYIT_RE.findall(duz):
        try:
            kayitlar.append(json.loads(ham))
        except json.JSONDecodeError:
            continue
    return kayitlar


def script_kaynaklari(html: str) -> list[str]:
    corba = BeautifulSoup(html, "html.parser")
    return [s.get("src") for s in corba.find_all("script") if s.get("src")][:20]


def sayfalama_izleri(html: str) -> list[str]:
    """Sayfalama parametresi izleri. Bulunması kanıt değil, ipucudur."""
    izler = []
    for kalip in (
        r"page\w*\s*[=:]\s*\d+",
        r"pageSize\s*[=:]\s*\d+",
        r"fromDate|toDate",
        r"sayfa\s*[=:]?\s*\d+",
        r"totalCount|toplamKayit|recordCount",
        r"\bpageIndex\b|\bpageNumber\b|\boffset\b|\blimit\b",
    ):
        for m in re.finditer(kalip, html, re.I):
            izler.append(m.group(0))
            if len(izler) > 30:
                return sorted(set(izler))
    return sorted(set(izler))


# --- Çekim -----------------------------------------------------------------


def getir_fabrikasi(gunluk: list[dict]):
    """Çekici'nin ağ katmanını sarar; HTTP durumu ve yönlendirmeyi kaydeder.

    Çekici.getir yalnızca gövdeyi döndürüyor (200 dışını istisnaya çeviriyor);
    rapor için durum kodu ve son URL lazım, o yüzden burada yakalanıyor.
    """
    import requests

    def getir(url: str, basliklar: dict):
        t0 = time.monotonic()
        y = requests.get(url, headers=basliklar, timeout=30)
        gunluk.append(
            {
                "istenen_url": url,
                "son_url": y.url,
                "yonlendirme_zinciri": [h.status_code for h in y.history],
                "durum": y.status_code,
                "sure_sn": round(time.monotonic() - t0, 2),
                "bayt": len(y.content),
                "icerik_turu": y.headers.get("Content-Type", ""),
                "sunucu": y.headers.get("Server", ""),
            }
        )
        return y.status_code, y.text, dict(y.headers)

    return getir


def cek(cekici: Çekici, url: str, sonuc: dict) -> str | None:
    """Tek URL çeker, hata halinde ölçümü bozmadan None döner."""
    onceki = dict(cekici.istatistik)
    try:
        govde = cekici.getir(url)
    except BütçeAşıldı as e:
        sonuc["hata"] = f"BÜTÇE AŞILDI: {e}"
        raise
    except (ÇekimHatası, Exception) as e:  # noqa: BLE001 — keşifte her hata veridir
        sonuc["hata"] = f"{type(e).__name__}: {e}"
        return None
    sonuc["kaynak"] = (
        "onbellek" if cekici.istatistik["onbellek"] > onceki["onbellek"] else "ag"
    )
    return govde


def agdan_cekilen_toplam() -> int:
    """Önbellek indeksindeki satır sayısı = bugüne kadar ağa çıkılan istek."""
    ix = ONBELLEK / "index.tsv"
    if not ix.exists():
        return 0
    return sum(1 for _ in ix.open(encoding="utf-8"))


# --- Rotalar ---------------------------------------------------------------


def rota_robots(cekici: Çekici) -> dict:
    """Nazik istemci önce kuralları okur (Spec §3.2)."""
    s = {"ad": "robots.txt", "url": "https://kap.org.tr/robots.txt"}
    govde = cek(cekici, s["url"], s)
    if govde is None:
        return s
    s["icerik"] = govde[:2000]
    s["bist_sirketler_yasak_mi"] = bool(
        re.search(r"Disallow:\s*/\s*$", govde, re.M)
    )
    return s


def rota_1_sirket_listesi(cekici: Çekici) -> dict:
    s = {"ad": "1 — Şirket listesi", "url": ROTA_1}
    govde = cek(cekici, ROTA_1, s)
    if govde is None:
        return s

    s["olcu"] = govde_olc(govde)
    s["script_src"] = script_kaynaklari(govde)
    s["sayfalama_izleri"] = sayfalama_izleri(govde)

    # Asıl bulgu: veri, HTML tablosunda VE gömülü RSC yükünde iki kez var.
    # Yapılandırılmış olan ikincisi; DOM kazımaya gerek yok.
    kayitlar = rsc_kayitlari(govde)
    s["rsc_kayit_sayisi"] = len(kayitlar)
    s["rsc_alanlari"] = sorted(kayitlar[0]) if kayitlar else []
    s["benzersiz_ticker"] = len({k.get("stockCode") for k in kayitlar})
    s["bos_ticker"] = sum(1 for k in kayitlar if not k.get("stockCode"))
    s["uye_tipleri"] = sorted({k.get("kapMemberType") for k in kayitlar})
    s["rsc_ornek"] = kayitlar[:2]
    s["ticker_uuid_haritasi_kuruldu"] = bool(kayitlar)
    # Pazar (Yıldız/Ana/Alt) bu kayıtlarda var mı? XKTUM ön şartı (Spec §0.4)
    s["pazar_alani_var"] = any(
        "market" in a.lower() or "pazar" in a.lower() for a in s["rsc_alanlari"]
    )

    # DOM tarafı: RSC yükü kaybolursa geri düşülecek katman burası.
    corba = BeautifulSoup(govde, "html.parser")
    satirlar = corba.find_all("tr")
    s["tablo_satiri"] = len(satirlar)
    s["ticker_slug_esleme_sayisi"] = len(ticker_slug_haritasi(govde))
    for anahtar, kalip in (
        ("pazar_metni_gecti", r"Yıldız Pazar|Ana Pazar|Alt Pazar"),
        ("bilinen_ticker_gecti", r"\bTHYAO\b|\bGARAN\b|\bASELS\b"),
    ):
        s[anahtar] = bool(re.search(kalip, govde))
    s["ilk_satir_ornegi"] = [
        " | ".join(h.get_text(" ", strip=True) for h in tr.find_all(["td", "th"]))[:200]
        for tr in satirlar[:5]
    ]
    return s


def rota_2_bildirim_gecmisi(cekici: Çekici, uuid: str | None, kaynak: str) -> dict:
    s = {"ad": "2 — Bildirim geçmişi", "uuid": uuid, "uuid_kaynagi": kaynak}
    if not uuid:
        s["hata"] = "Denenecek member uuid bulunamadı."
        return s
    s["url"] = f"https://kap.org.tr/tr/bildirim-sorgu-sonuc?member={uuid}"
    govde = cek(cekici, s["url"], s)
    if govde is None:
        return s

    s["olcu"] = govde_olc(govde)
    s["sayfalama_izleri"] = sayfalama_izleri(govde)

    # bildirim_id sayfada link olarak DEĞİL, satırdaki checkbox id'sinde.
    # /tr/Bildirim/{id} linki aramak boş küme döndürüyor — ilk turda bu oldu.
    satirlar = _bildirim_satirlari(govde)
    s["kayit_sayisi"] = len(satirlar)
    s["bildirim_id_ornegi"] = [i for i, _ in satirlar[:3]]
    s["tarih_araligi"] = [satirlar[-1][1], satirlar[0][1]] if satirlar else []
    s["_satirlar"] = satirlar

    corba = BeautifulSoup(govde, "html.parser")
    tablo = corba.find("table")
    if tablo:
        basliklar = tablo.find_all("tr")[0]
        s["basliklar"] = [h.get_text(" ", strip=True) for h in basliklar.find_all(["th", "td"])]
        # Boş sonuç metni tabloNUN İÇİNDE mi (gerçekten boş) yoksa yalnızca
        # i18n sözlüğünde mi (çeviri dizesi) geçiyor — ikisi farklı şey.
        s["bos_sonuc_tabloda"] = "Bildirim bulunamadı" in tablo.get_text()

    # KAFİF satırları doğrudan konu metninden ayıklanabiliyor mu?
    kafif = []
    if tablo:
        for tr in tablo.find_all("tr")[1:]:
            if "Katılım Finansı İlkeleri Bilgi Formu" not in tr.get_text(" ", strip=True):
                continue
            inp = tr.find("input", {"name": "notification-checkbox"})
            tds = [x.get_text(" ", strip=True) for x in tr.find_all("td")]
            kafif.append(
                {
                    "bildirim_id": inp.get("id") if inp else None,
                    "tarih": tds[2] if len(tds) > 2 else "",
                    "yil": tds[-3] if len(tds) > 3 else "",
                    "periyot": tds[-2] if len(tds) > 2 else "",
                }
            )
    s["kafif_satirlari"] = kafif
    s["bilinen_bildirim_listede"] = any(k["bildirim_id"] == "1566002" for k in kafif)
    return s


def _bildirim_satirlari(html: str) -> list[tuple[str, str]]:
    """(bildirim_id, tarih) çiftleri. id, satırdaki checkbox'ın id'sinde."""
    corba = BeautifulSoup(html, "html.parser")
    tablo = corba.find("table")
    if not tablo:
        return []
    cikti = []
    for tr in tablo.find_all("tr")[1:]:
        inp = tr.find("input", {"name": "notification-checkbox"})
        tds = tr.find_all("td")
        if inp and inp.get("id") and len(tds) > 2:
            cikti.append((inp["id"], tds[2].get_text(" ", strip=True)))
    return cikti


def rota_2_parametre_sondasi(cekici: Çekici, uuid: str, temel: list) -> list[dict]:
    """Sorgu penceresini genişleten bir parametre var mı?

    Formda tarih alanı yok, bu yüzden ampirik deneniyor. Sonuç temel
    kümeden farklıysa parametre işleniyor demektir; aynıysa yok sayılıyor.
    Bu sorunun cevabı Faz 2'yi (tarihsel geri doldurma) belirliyor.
    """
    temel_idler = {i for i, _ in temel}
    denemeler = [
        "&fromDate=01.01.2024&toDate=31.12.2024",
        "&year=2024",
        "&startDate=01.01.2024&endDate=31.12.2024",
        "&disclosureClass=DG",
    ]
    sonuclar = []
    for ek in denemeler:
        s = {"parametre": ek}
        url = f"https://kap.org.tr/tr/bildirim-sorgu-sonuc?member={uuid}{ek}"
        govde = cek(cekici, url, s)
        if govde is None:
            sonuclar.append(s)
            continue
        satirlar = _bildirim_satirlari(govde)
        idler = {i for i, _ in satirlar}
        s["kayit"] = len(satirlar)
        s["tarih_araligi"] = [satirlar[-1][1], satirlar[0][1]] if satirlar else []
        s["temelden_farkli"] = idler != temel_idler
        s["yeni_id_sayisi"] = len(idler - temel_idler)
        sonuclar.append(s)
    return sonuclar


def ticker_slug_haritasi(html: str) -> dict[str, str]:
    """ticker → '1107-turk-hava-yollari-a-o'.

    Spec §1.1 iki ayrı KAP kimliğinden söz ediyor ve eşlemeyi ayrı bir iş
    sayıyor. Ölçüm gösteriyor ki ikisi de aynı sayfada: mkkMemberOid gömülü
    RSC yükünde, sayısal id + slug ise satırın <a href>'inde.
    """
    corba = BeautifulSoup(html, "html.parser")
    harita = {}
    for tr in corba.find_all("tr"):
        hucreler = tr.find_all("td")
        if not hucreler:
            continue
        ticker = hucreler[0].get_text(" ", strip=True)
        baglanti = tr.find("a", href=re.compile(r"/tr/sirket-bilgileri/ozet/"))
        if ticker and baglanti:
            harita[ticker] = baglanti["href"].rsplit("/", 1)[-1]
    return harita


def ek_sondalar(cekici: Çekici, r1_html: str) -> list[dict]:
    """İki açık soruyu kapatan sondalar: (a) sayısal id gerçekten kfif
    rotasında çalışıyor mu, (b) bildirim sorgusu THY'ye özel değil, başka
    şirkette de aynı yapıyı veriyor mu (n=1 → n=2)."""
    harita = ticker_slug_haritasi(r1_html)
    kayitlar = {k["stockCode"]: k for k in rsc_kayitlari(r1_html)}
    sonuclar = []

    s = {"soru": "kfif rotası sayısal id + slug ile açılıyor mu?", "ticker": "THYAO"}
    if "THYAO" in harita:
        s["url"] = f"https://kap.org.tr/tr/kfif/{harita['THYAO']}"
        govde = cek(cekici, s["url"], s)
        if govde is not None:
            s["olcu"] = govde_olc(govde)
            s["kafif_icerigi_var"] = "Katılım Finans" in govde
            s["tablo_sayisi"] = s["olcu"]["tablo_sayisi"]
            s["bilgi_mevcut_degil"] = "Bilgi Mevcut Değil" in govde
    sonuclar.append(s)

    s = {"soru": "bildirim sorgusu başka şirkette de aynı mı?", "ticker": "ASELS"}
    if "ASELS" in kayitlar:
        oid = kayitlar["ASELS"]["mkkMemberOid"]
        s["url"] = (
            f"https://kap.org.tr/tr/bildirim-sorgu-sonuc?member={oid}"
            "&disclosureClass=DG"
        )
        govde = cek(cekici, s["url"], s)
        if govde is not None:
            satirlar = _bildirim_satirlari(govde)
            s["kayit"] = len(satirlar)
            s["tarih_araligi"] = [satirlar[-1][1], satirlar[0][1]] if satirlar else []
            corba = BeautifulSoup(govde, "html.parser")
            s["kafif_satirlari"] = [
                tr.find("input", {"name": "notification-checkbox"}).get("id")
                for tr in corba.find_all("tr")
                if "Katılım Finansı İlkeleri Bilgi Formu" in tr.get_text(" ", strip=True)
                and tr.find("input", {"name": "notification-checkbox"})
            ]
    sonuclar.append(s)
    return sonuclar


def rota_3_tekil_bildirim(cekici: Çekici) -> dict:
    s = {"ad": "3 — Tekil bildirim", "url": ROTA_3}
    govde = cek(cekici, ROTA_3, s)
    if govde is None:
        return s
    s["olcu"] = govde_olc(govde)

    # Canlı gövde ile diskteki dosyanın ayrıştırma sonuçları aynı mı?
    s["karsilastirma"] = {}
    for etiket, kaynak_html in (
        ("canli", govde),
        ("disk", YEREL_THY.read_text(encoding="utf-8", errors="ignore")
         if YEREL_THY.exists() else None),
    ):
        if kaynak_html is None:
            s["karsilastirma"][etiket] = {"hata": "dosya yok"}
            continue
        try:
            b = ayristir(kaynak_html, bildirim_id=1566002, ticker="THYAO")
        except AyristirmaHatasi as e:
            s["karsilastirma"][etiket] = {"hata": f"AyristirmaHatasi: {e}"}
            continue
        kontrol = self_check(b)
        s["karsilastirma"][etiket] = {
            "sablon_imzasi": b.sablon_imzasi,
            "kalem_sayisi": len(b.kalemler),
            "beyan_dolu": sum(1 for v in b.beyanlar.values() if v is not None),
            "evet_beyanlar": sorted(k for k, v in b.beyanlar.items() if v),
            "gonderim_ts": str(b.gonderim_ts),
            "sha256": b.raw_sha256[:16],
            "self_check": "GEÇTİ" if kontrol.gecti else "KALDI",
            "oranlar": {
                ad: str(getattr(kontrol.hesaplanan, ad))
                for ad in ("gelir", "varlik", "borc")
            },
            "sapmalar": {k: str(v) for k, v in kontrol.sapmalar.items()},
        }
    return s


# --- Ana akış --------------------------------------------------------------


def main() -> int:
    sinirlayici = HızSınırlayıcı(min_aralik=2.0, jitter=1.0, oturum_butcesi=50)
    gunluk: list[dict] = []
    cekici = Çekici(
        ONBELLEK,
        sinirlayici=sinirlayici,
        getir_fn=getir_fabrikasi(gunluk),
    )

    ag_baslangic = agdan_cekilen_toplam()
    rapor: dict = {"rotalar": [], "kesildi": None}

    # Diskteki bildirimde de 32-hex dizeler var, ama hepsi member oid değil;
    # ilkini körlemesine almak yanlış sorgu üretiyor (ilk turda bu oldu).
    # Doğru kaynak rota 1: ticker → mkkMemberOid.
    if YEREL_THY.exists():
        rapor["yerel_thy_uuid_adaylari"] = uuid_bul(
            YEREL_THY.read_text(encoding="utf-8", errors="ignore")
        )[:5]

    try:
        rapor["rotalar"].append(rota_robots(cekici))
        r1 = rota_1_sirket_listesi(cekici)
        rapor["rotalar"].append(r1)

        uuid, kaynak = None, "çözülemedi"
        if r1.get("rsc_kayit_sayisi"):
            # önbellekten okunur, ağa çıkmaz
            for k in rsc_kayitlari(cekici.getir(ROTA_1)):
                if k.get("stockCode") == "THYAO":
                    uuid = k["mkkMemberOid"]
                    kaynak = "rota 1, ticker=THYAO → mkkMemberOid"
                    break
        r2 = rota_2_bildirim_gecmisi(cekici, uuid, kaynak)
        rapor["rotalar"].append(r2)
        if uuid and r2.get("kayit_sayisi"):
            rapor["parametre_sondasi"] = rota_2_parametre_sondasi(
                cekici, uuid, r2.pop("_satirlar")
            )
        r2.pop("_satirlar", None)
        rapor["rotalar"].append(rota_3_tekil_bildirim(cekici))
        if r1.get("rsc_kayit_sayisi"):
            rapor["ek_sondalar"] = ek_sondalar(cekici, cekici.getir(ROTA_1))
    except BütçeAşıldı as e:
        rapor["kesildi"] = str(e)

    rapor["istatistik"] = dict(cekici.istatistik)
    rapor["sinirlayici_sayac"] = sinirlayici.kullanilan
    rapor["ag_istegi_bu_calistirma"] = agdan_cekilen_toplam() - ag_baslangic
    rapor["ag_istegi_kumulatif"] = agdan_cekilen_toplam()
    rapor["http_gunlugu"] = gunluk

    OLCUM_JSON.write_text(
        json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(rapor, ensure_ascii=False, indent=2)[:12000])
    print(f"\n[ölçüm yazıldı: {OLCUM_JSON}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
