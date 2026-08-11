"""Faz 0 test paketi.

İki katman, ve aradaki fark önemli:

  A) GERÇEK VERİ testleri — THY 2025/Yıllık bildiriminin yayımlanmış
     rakamları. Bunlar gerçek doğrulamadır; oran formüllerinin ve karar
     motorunun doğru olduğunu KAP'ın kendi çıktısına karşı kanıtlar.

  B) SENTETİK HTML testi — KAP'ın tablo yapısını taklit eden bir HTML.
     Bu bir duman testidir, kanıt değil: parser'ın mekaniğinin (imza
     eşlemesi, Türkçe sayı okuma, kalem çıkarımı) çalıştığını gösterir,
     ama gerçek KAP HTML'inin bu yapıda olduğunu KANITLAMAZ.
     Gerçek doğrulama, elde bir .html dosyasıyla `cli dogrula` çalıştırınca.
"""

from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from katilim.model import KafifBildirim  # noqa: E402
from katilim.oranlar import hesapla, self_check  # noqa: E402
from katilim.karar import (  # noqa: E402
    Karar, degerlendir, seri_degerlendir, BANT, LIMIT,
)
from katilim import ayristirici  # noqa: E402
from katilim.metin import parse_sayi, parse_para_carpani, parse_yil_donem  # noqa: E402

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "thy_2025_yillik.json"


def thy() -> KafifBildirim:
    return KafifBildirim.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))


# ===== A) Gerçek veri testleri ============================================

def test_thy_oranlari_yeniden_hesaplaniyor():
    o = hesapla(thy())
    assert o.gelir == Decimal("4.92"), o.gelir
    assert o.varlik == Decimal("18.02"), o.varlik
    assert o.borc == Decimal("7.24"), o.borc


def test_thy_self_check_geciyor():
    sc = self_check(thy())
    assert sc.gecti, sc.rapor()
    assert not sc.notlar, sc.notlar


def test_thy_tablo_toplamlari_formla_tutuyor():
    b = thy()
    beklenen = {
        "4C": 113103, "4D": 60498, "4E": 1068575,
        "5F": 426982, "5G": 67069, "5H": 1996745,
        "6I": 783575, "6J": 638976, "4B": 0,
    }
    for tablo, deger in beklenen.items():
        assert b.toplam(tablo) == Decimal(deger), f"{tablo}: {b.toplam(tablo)}"


def test_thy_karari_G4_ile_eleniyor():
    """THY üç oranı da geçiyor ama 4A/alkol bayrağı kesin eleme."""
    s = degerlendir(thy())
    assert s.karar is Karar.UYGUN_DEGIL
    assert s.kodlar == ["G4_DOGRUDAN_AYKIRI"]
    assert "Alkollü" in s.gerekceler[0]
    # Oranların hepsi limit altında olmasına rağmen elendi:
    assert s.oranlar.gelir < LIMIT["gelir"]
    assert s.oranlar.varlik < LIMIT["varlik"]
    assert s.oranlar.borc < LIMIT["borc"]


def test_thy_gelir_orani_limite_yakin():
    """%4,92 -> %5 limitine 0,08 puan. İzleme listesi gerekçesi."""
    o = hesapla(thy())
    assert LIMIT["gelir"] - o.gelir < Decimal("0.10")


# ===== Karar motoru kapıları ==============================================

def _temiz() -> KafifBildirim:
    """Tüm beyanları hayır, oranları limit altı bir bildirim."""
    b = thy()
    b.beyanlar = {k: False for k in b.beyanlar}
    return b


def test_temiz_bildirim_uygun():
    assert degerlendir(_temiz()).karar is Karar.UYGUN


def test_kapilar_sirayla_calisiyor():
    for alan, kod in [
        ("b1_1", "G1_ESAS_SOZLESME"),
        ("b2_2", "G2_IMTIYAZ"),
        ("b3_1", "G3_MADDE_15"),
        ("b4_4", "G4_DOGRUDAN_AYKIRI"),
    ]:
        b = _temiz()
        b.beyanlar[alan] = True
        s = degerlendir(b)
        assert s.karar is Karar.UYGUN_DEGIL and s.kodlar == [kod], (alan, s)


def test_eksik_beyan_belirsiz_uretir():
    b = _temiz()
    b.beyanlar["b4_3"] = None
    assert degerlendir(b).karar is Karar.BELIRSIZ


def _oranli(gelir=None, varlik=None, borc=None) -> KafifBildirim:
    """Verilen oranları üretecek şekilde kalemleri kurgular."""
    from katilim.model import Kalem
    b = _temiz()
    b.kalemler = []
    tv = Decimal(1000)
    b.kalemler.append(Kalem("5H", None, "Toplam Varlıklar", tv))
    b.kalemler.append(Kalem("4E", 1, "Hasılat", Decimal(1000)))
    b.kalemler.append(Kalem("4C", 1, "x", (gelir or Decimal(0)) * 10))
    b.kalemler.append(Kalem("4B", 1, "x", Decimal(0)))
    b.kalemler.append(Kalem("4D", 1, "x", Decimal(0)))
    b.kalemler.append(Kalem("5F", 1, "x", (varlik or Decimal(0)) * 10))
    b.kalemler.append(Kalem("5G", 1, "x", Decimal(0)))
    b.kalemler.append(Kalem("6I", 1, "x", (borc or Decimal(0)) * 10))
    b.kalemler.append(Kalem("6J", 1, "x", Decimal(0)))
    b.ozet_gelir_orani = gelir or Decimal(0)
    b.ozet_varlik_orani = varlik or Decimal(0)
    b.ozet_borc_orani = borc or Decimal(0)
    return b


def test_tolerans_bandi_icinde_beklemede():
    b = _oranli(gelir=Decimal("5.4"))
    s = degerlendir(b)
    assert s.karar is Karar.TOLERANSTA
    assert s.kodlar == ["G5_GELIR_TOLERANS"]


def test_tolerans_bandi_disinda_eleme():
    b = _oranli(gelir=Decimal("5.6"))
    assert degerlendir(b).karar is Karar.UYGUN_DEGIL


def test_bant_sinirlari():
    assert BANT["gelir"] == Decimal("5.5")
    assert BANT["varlik"] == Decimal("36.3")
    assert BANT["borc"] == Decimal("36.3")


def test_ikinci_donemde_tolerans_sifirlaniyor():
    """Md. 3.5: önceki dönem toleranstaysa, bu dönemde küçük bir aşım bile eler."""
    b = _oranli(gelir=Decimal("5.1"))
    assert degerlendir(b, onceki_donem_toleransta=False).karar is Karar.TOLERANSTA
    assert degerlendir(b, onceki_donem_toleransta=True).karar is Karar.UYGUN_DEGIL


def test_tolerans_sirket_bazinda_kriter_bazinda_degil():
    """H4: gelirden toleransa düşüp sonraki dönem borçta aşan şirket elenir."""
    d1 = _oranli(gelir=Decimal("5.2"))
    d1.yil, d1.periyot = 2025, "6 Aylık"
    d1.gonderim_ts = datetime(2025, 8, 13, 18, 0, 0)
    d2 = _oranli(borc=Decimal("34"))
    d2.yil, d2.periyot = 2025, "Yıllık"
    d2.gonderim_ts = datetime(2026, 3, 11, 18, 0, 0)
    sonuc = seri_degerlendir([d2, d1])  # sıralamayı motor yapmalı
    assert [s.karar for _, s in sonuc] == [Karar.TOLERANSTA, Karar.UYGUN_DEGIL]


def test_temize_donunce_tolerans_kalkiyor():
    d1 = _oranli(gelir=Decimal("5.2"))
    d1.yil, d1.periyot = 2025, "6 Aylık"
    d1.gonderim_ts = datetime(2025, 8, 13, 18, 0, 0)
    d2 = _oranli(gelir=Decimal("4.0"))
    d2.yil, d2.periyot = 2025, "Yıllık"
    d2.gonderim_ts = datetime(2026, 3, 11, 18, 0, 0)
    d3 = _oranli(gelir=Decimal("5.2"))
    d3.yil, d3.periyot = 2026, "6 Aylık"
    d3.gonderim_ts = datetime(2026, 8, 5, 18, 0, 0)
    kararlar = [s.karar for _, s in seri_degerlendir([d1, d2, d3])]
    assert kararlar == [Karar.TOLERANSTA, Karar.UYGUN, Karar.TOLERANSTA]


def test_ayni_donem_duzeltmesi_zinciri_ilerletmiyor():
    """GERÇEK VAKA — DCTTR. Aynı dönemin düzeltmesi YENİ DÖNEM DEĞİLDİR.

    `seri_degerlendir` bildirim bazında yürüdüğü sürece üçüncü kayıt,
    ikinciyi (aynı dönemin düzeltilmiş hâli) "önceki dönem" sanıyor ve
    "önceki dönem TOLERANSTA + bu dönem aşım → UYGUN_DEGIL" kuralını
    işletiyordu. Sonuç: XKTUM üyesi bir şirketi eliyorduk (sahte eleme).

    Md. 3.5 ardışık DEĞERLEME DÖNEMLERİNİ düzenliyor. Doğru davranış:
    2025/Yıllık'ın önceki dönemi 2025/6 Aylık (UYGUN), dolayısıyla ikinci
    Yıllık kaydı da TOLERANSTA kalır.
    """
    d1 = _oranli(gelir=Decimal("0.75"), borc=Decimal("28.82"))
    d1.yil, d1.periyot = 2025, "6 Aylık"
    d1.gonderim_ts = datetime(2025, 8, 7, 18, 14)
    d2 = _oranli(gelir=Decimal("4.97"), borc=Decimal("34.62"))   # DUZELTILEN
    d2.yil, d2.periyot = 2025, "Yıllık"
    d2.gonderim_ts = datetime(2026, 3, 10, 18, 0)
    d3 = _oranli(gelir=Decimal("4.66"), borc=Decimal("35.85"))   # DUZENLENEN
    d3.yil, d3.periyot = 2025, "Yıllık"
    d3.gonderim_ts = datetime(2026, 4, 6, 18, 0)

    kararlar = [s.karar for _, s in seri_degerlendir([d1, d2, d3])]
    assert kararlar == [Karar.UYGUN, Karar.TOLERANSTA, Karar.TOLERANSTA], kararlar

    # Düzeltme kendi döneminin ÖNCEKİSİNİ görmeli, kendi eski kaydını değil.
    sonuclar = seri_degerlendir([d1, d2, d3])
    assert sonuclar[2][1].onceki_donem_toleransta is False


def test_ayni_donem_uc_bildirim_sonraki_donemi_bir_kez_etkiliyor():
    """Aynı dönemin üç kaydı, sonraki dönem için TEK bir durum üretir.

    PNLSN örüntüsü (aynı dönem 3 bildirim). Sonraki dönemin gördüğü durum,
    o dönemin gönderim anında geçerli olan SON kayıttan gelir — look-ahead
    yok, ama zincir de üç kez ilerlemiyor.
    """
    a1 = _oranli(gelir=Decimal("4.0"))
    a1.yil, a1.periyot = 2025, "6 Aylık"
    a1.gonderim_ts = datetime(2025, 8, 8, 18, 0)
    a2 = _oranli(gelir=Decimal("5.3"))          # düzeltme: toleransa düşürdü
    a2.yil, a2.periyot = 2025, "6 Aylık"
    a2.gonderim_ts = datetime(2025, 8, 13, 18, 0)
    a3 = _oranli(gelir=Decimal("5.2"))          # ikinci düzeltme, hâlâ bantta
    a3.yil, a3.periyot = 2025, "6 Aylık"
    a3.gonderim_ts = datetime(2025, 9, 4, 18, 0)
    b1 = _oranli(gelir=Decimal("5.1"))          # sonraki DÖNEM, bantta aşım
    b1.yil, b1.periyot = 2025, "Yıllık"
    b1.gonderim_ts = datetime(2026, 3, 4, 18, 0)

    kararlar = [s.karar for _, s in seri_degerlendir([a1, a2, a3, b1])]
    # İlk üçü aynı dönem: zincir ilerlemiyor, üçü de kendi başına değerlenir.
    assert kararlar[:3] == [Karar.UYGUN, Karar.TOLERANSTA, Karar.TOLERANSTA]
    # Sonraki dönem, 6 Aylık'ın SON durumunu (TOLERANSTA) görüyor -> elenir.
    assert kararlar[3] is Karar.UYGUN_DEGIL


def test_zincir_tek_uygulama_panel_delege_ediyor():
    """`panel.panel_uret` kendi zincirini kurmamalı — iki uygulama ayrışır.

    Bir zamanlar ayrıştılar: `panel.csv` doğruydu ama `cli toplu` sahte
    eleme üretiyordu.
    """
    from katilim import karar as karar_modulu
    from katilim import panel as panel_modulu

    assert panel_modulu.ZINCIR_BOSLUK_GUN is karar_modulu.ZINCIR_BOSLUK_GUN
    assert panel_modulu.zincirle_degerlendir is karar_modulu.zincirle_degerlendir
    kaynak = pathlib.Path(karar_modulu.__file__).with_name("panel.py").read_text(
        encoding="utf-8"
    )
    assert "onceki_donem_anahtari" not in kaynak, (
        "panel.py yeniden kendi zincirini kuruyor"
    )


def test_siralama_yalniz_gonderim_ts_ile():
    """3/6/9 Aylık ve Yıllık karışık seri: kronoloji dönem etiketinden GELMEZ.

    Eski anahtar `(yil, 0 if periyot=="6 Aylık" else 1, ts)` idi; 3 Aylık,
    9 Aylık ve Yıllık aynı kovaya düşüyor ve mayısta verilen bir 3 Aylık,
    ağustosta verilen 6 Aylık'tan sonra sıralanıyordu.
    """
    kayitlar = []
    # (yil, periyot, gonderim_ts) — dönem etiketi ile zaman KASITEN ters
    plan = [
        (2024, "Yıllık", datetime(2025, 8, 11, 23, 45)),   # futbol kulübü
        (2025, "3 Aylık", datetime(2025, 8, 19, 18, 12)),
        (2025, "6 Aylık", datetime(2025, 9, 2, 18, 0)),
        (2025, "9 Aylık", datetime(2025, 11, 10, 20, 12)),
        (2025, "Yıllık", datetime(2026, 3, 4, 18, 57)),
        (2026, "3 Aylık", datetime(2026, 5, 6, 19, 6)),
    ]
    for yil, per, ts in plan:
        b = _oranli()
        b.yil, b.periyot, b.gonderim_ts = yil, per, ts
        kayitlar.append(b)

    import random
    karisik = list(kayitlar)
    random.Random(20260810).shuffle(karisik)
    sirali = [b.gonderim_ts for b, _ in seri_degerlendir(karisik)]
    assert sirali == sorted(sirali), sirali
    assert sirali == [ts for _, _, ts in plan]


def test_zaman_damgasiz_kayit_sona_gidiyor():
    """Bilinmeyen tarih geçmişe yerleştirilirse sonraki dönemlerin tolerans
    durumunu sessizce değiştirir; bu yüzden en SONA konuyor."""
    b1 = _oranli()
    b1.gonderim_ts = datetime(2025, 8, 13, 18, 0)
    b2 = _oranli()
    b2.gonderim_ts = None
    sirali = [b.gonderim_ts for b, _ in seri_degerlendir([b2, b1])]
    assert sirali == [datetime(2025, 8, 13, 18, 0), None]


def test_mali_sektor_kapsam_disi():
    assert degerlendir(thy(), mali_sektor_muaf=True).karar is Karar.KAPSAM_DISI


# ===== Türkçe sayı/metin ==================================================

def test_turkce_sayi_okuma():
    assert parse_sayi("1.068.575") == Decimal("1068575")
    assert parse_sayi("4,92") == Decimal("4.92")
    assert parse_sayi("0") == Decimal(0)
    assert parse_sayi("") is None
    assert parse_sayi("Konsolide") is None


def test_para_carpani():
    assert parse_para_carpani("1.000.000 TL") == 1000000
    assert parse_para_carpani("1.000 TL") == 1000
    assert parse_para_carpani("TL") == 1


def test_yil_donem():
    assert parse_yil_donem("2025 / Yıllık") == (2025, "Yıllık")
    assert parse_yil_donem("2024 / 6 Aylık") == (2024, "6 Aylık")


# ===== B) Parser duman testi (sentetik HTML) ==============================

def _sentetik_html() -> str:
    """KAP tablo yapısını taklit eden HTML. Kanıt değil, duman testi."""
    b = thy()
    parcalar = ["<html><body>", "<div>Gönderim Tarihi</div><div>04.03.2026 18:57:54</div>"]
    parcalar.append(
        "<table>"
        "<tr><td>Sunum Para Birimi</td><td>1.000.000 TL</td></tr>"
        "<tr><td>Verilerin Ait Olduğu Finansal Tablo Yılı / Dönemi</td><td>2025 / Yıllık</td></tr>"
        "<tr><td>Finansal Tablo Niteliği</td><td>Konsolide</td></tr>"
        "<tr><td>5) Şirketin Katılım Finansı İlkelerine Uygun Olmayan Gelirlerinin Oranı (%)</td><td>4,92</td></tr>"
        "<tr><td>6) Şirketin Katılım Finansı İlkelerine Uygun Olmayan Varlıklarının Oranı (%)</td><td>18,02</td></tr>"
        "<tr><td>7) Şirketin Katılım Finansı İlkelerine Uygun Olmayan Borçlarının Oranı (%)</td><td>7,24</td></tr>"
        "</table>"
    )
    parcalar.append(
        "<table>"
        "<tr><td>1) Şirketin kendisinin, tüzel kişi ortaklarının veya iştiraklerinin esas"
        " sözleşmelerinde Standart madde 1.2'de sayılan faaliyetlerden herhangi birinin"
        " yapılabileceği yazıyor mu?</td><td>HAYIR</td><td></td></tr>"
        "<tr><td>2) ... Standart madde 1.2'de sayılan faaliyetlerden herhangi biri olan"
        " şirketlere ortak olunabileceği yazıyor mu?</td><td>HAYIR</td><td></td></tr>"
        "</table>"
    )
    parcalar.append(
        "<table>"
        "<tr><td>1) Şirketin pay grupları arasında kâr payı imtiyazı bulunuyor mu?</td><td>HAYIR</td></tr>"
        "<tr><td>2) Şirketin pay grupları arasında tasfiye payı imtiyazı bulunuyor mu?</td><td>HAYIR</td></tr>"
        "</table>"
    )
    parcalar.append(
        "<table>"
        "<tr><td>1) ... kamuoyuna yapılmış bir açıklama bulunuyor mu?</td><td>HAYIR</td></tr>"
        "<tr><td>2) ... mahkemelerce alınmış herhangi bir karar bulunuyor mu?</td><td>HAYIR</td></tr>"
        "</table>"
    )
    dortA = [
        ("alkollü içki/gıda üretim ve ticaretine yönelik", "EVET"),
        ("domuz mamullerinin üretim ve ticaretine yönelik", "HAYIR"),
        ("içime yönelik tütün mamulleri üretim ve toptan ticaretine yönelik", "HAYIR"),
        ("kumar veya kumar hükmünde", "HAYIR"),
        ("katılım esaslı olanlar hariç finans sektörü faaliyeti", "HAYIR"),
        ("ahlaka ve islami değerlere aykırı yayıncılık", "HAYIR"),
        ("islami değerlerle bağdaşmayan otel işletmeciliği, turizm", "HAYIR"),
    ]
    parcalar.append("<table>" + "".join(
        f"<tr><td>{i}) Şirketin kendisinin, tüzel kişi ortaklarının veya iştiraklerinin, "
        f"{ad} faaliyeti ve/veya geliri bulunuyor mu?</td><td>{v}</td></tr>"
        for i, (ad, v) in enumerate(dortA, 1)
    ) + "</table>")

    def tr_sayi(x: Decimal) -> str:
        return f"{int(x):,}".replace(",", ".")

    for tablo in ("4B", "4C", "4D", "4E", "5F", "5G", "5H", "6I", "6J"):
        satirlar = ["<tr><td></td><td>1.000.000 TL</td></tr>",
                    "<tr><td></td><td>2025 / Yıllık</td></tr>",
                    "<tr><td></td><td>Konsolide</td></tr>"]
        toplam = Decimal(0)
        for k in b.tablo(tablo):
            on = f"{k.kalem_no}) " if k.kalem_no else ""
            satirlar.append(f"<tr><td>{on}{k.kalem_adi}</td><td>{tr_sayi(k.tutar_ham)}</td></tr>")
            toplam += k.tutar_ham
        if tablo != "5H":
            satirlar.append(f"<tr><td>TOPLAM</td><td>{tr_sayi(toplam)}</td></tr>")
        parcalar.append("<table>" + "".join(satirlar) + "</table>")

    parcalar.append("</body></html>")
    return "".join(parcalar)


def test_parser_sentetik_html_uzerinde_calisiyor():
    b = ayristirici.ayristir(_sentetik_html(), bildirim_id=1566002, ticker="THYAO")
    assert b.yil == 2025 and b.periyot == "Yıllık"
    assert b.para_birimi_carpani == 1000000
    assert b.finansal_tablo_niteligi == "Konsolide"
    assert not b.eksik_tablolar(), b.eksik_tablolar()
    assert not b.eksik_beyanlar(), b.eksik_beyanlar()
    assert b.beyanlar["b4_1"] is True
    assert b.beyanlar["b4_4"] is False
    sc = self_check(b)
    assert sc.gecti, sc.rapor()
    assert degerlendir(b).kodlar == ["G4_DOGRUDAN_AYKIRI"]


def test_parser_4C_4E_ayrimi():
    """En kırılgan nokta: aynı kalemleri paylaşan iki tablo."""
    b = ayristirici.ayristir(_sentetik_html())
    assert b.toplam("4C") == Decimal(113103)
    assert b.toplam("4E") == Decimal(1068575)


def test_parser_toplam_satirini_yutmuyor():
    """TOPLAM satırı kalem olarak sayılırsa tüm tutarlar iki katına çıkar."""
    b = ayristirici.ayristir(_sentetik_html())
    assert len(b.tablo("4D")) == 16
    assert b.toplam("4D") == Decimal(60498)


def test_parser_tanimayinca_hata_veriyor():
    try:
        ayristirici.ayristir("<html><body><table><tr><td>alakasız</td></tr></table></body></html>")
    except ayristirici.AyristirmaHatasi:
        return
    raise AssertionError("tanınmayan HTML'de hata bekleniyordu")


# ===== Bağımsız koşucu ====================================================
# pytest yoksa da çalışsın: python3 tests/test_motor.py

def _kos() -> int:
    import traceback
    testler = [
        (ad, fn) for ad, fn in sorted(globals().items())
        if ad.startswith("test_") and callable(fn)
    ]
    basarisiz = []
    for ad, fn in testler:
        try:
            fn()
            print(f"  ok    {ad}")
        except Exception:
            basarisiz.append(ad)
            print(f"  HATA  {ad}")
            print("        " + traceback.format_exc().replace("\n", "\n        "))
    print(f"\n{len(testler) - len(basarisiz)}/{len(testler)} test geçti")
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(_kos())
