"""THY 2025/Yıllık KAFİF altın standart fixture'ı.

Kaynak: KAP Bildirim 1566002, gönderim 04.03.2026 18:57:54.
Tutarlar formda göründüğü gibi (sunum birimi 1.000.000 TL).

Beklenen özet oranlar: gelir 4,92 | varlık 18,02 | borç 7,24
"""

import json
import pathlib

KALEMLER = {
    "4B": [
        ("Sağlığa zararlı tütün ürünlerinin perakende satışı ve sunumu", 0),
        ("Uygun faaliyet göstermeyen şirketlere sunulan iş ve hizmetler", 0),
        ("Uygun faaliyet göstermeyen şirketlerden elde edilen kira gelirleri", 0),
        ("Reklam, marka, sponsorluk ve aracılık faaliyetleri", 0),
    ],
    "4C": [
        ("Esas Faaliyetlerden Diğer Gelirler", 30134),
        ("Finansman Gelirleri", 30150),
        ("Yatırım Faaliyetlerinden Gelirler", 48223),
        ("Finans Sektörü Faaliyetleri Hasılatı", 0),
        ("Özkaynak Yöntemiyle Değerlenen Yatırımların Karlarından Paylar", 4596),
    ],
    "4D": [
        ("Fiyat farkı gelirleri", 0),
        ("Kur farkı gelirleri", 17075),
        ("Vade farkı gelirleri", 159),
        ("Katılım esaslı kıymetlerden ve fonlardan elde edilen gelirler", 1764),
        ("SGK prim gelirleri", 0),
        ("Katılım bankalarından alınan promosyon gelirleri", 0),
        ("Müşteri peşinatları irad kaydı", 0),
        ("Konusu kalmayan karşılıklar", 213),
        ("Hizmet gelirleri", 0),
        ("Kira ve bakım onarım gelirleri", 1456),
        ("Ardiye gelirleri", 0),
        ("Tazminat ve gecikme ceza gelirleri", 3678),
        ("Sigorta hasar tazminat gelirleri", 0),
        ("Dava gelirleri", 0),
        ("Uygun şirketlerden elde edilen temettü gelirleri", 41),
        ("Diğer uygun sayılan gelirler", 36112),
    ],
    "4E": [
        ("Hasılat", 955472),
        ("Esas Faaliyetlerden Diğer Gelirler", 30134),
        ("Finansman Gelirleri", 30150),
        ("Yatırım Faaliyetlerinden Gelirler", 48223),
        ("Finans Sektörü Faaliyetleri Hasılatı", 0),
        ("Özkaynak Yöntemiyle Değerlenen Yatırımların Karlarından Paylar", 4596),
    ],
    "5F": [
        ("Nakit ve Nakit Benzerleri", 86035),
        ("Finansal Yatırımlar", 297692),
        ("Türev Araçlar", 10583),
        ("Finans Sektörü Faaliyetlerinden Alacaklar", 0),
        ("Özkaynak Yöntemiyle Değerlenen Yatırımlar", 32672),
        ("İştirakler, İş Ortaklıkları ve Bağlı Ortaklıklardaki Yatırımlar", 0),
    ],
    "5G": [
        ("Çekler", 0),
        ("Kasa", 31),
        ("Vadesiz mevduat hesapları", 36112),
        ("Katılım esaslı yatırım araçlarındaki tutarlar", 0),
        ("Uygun iştirak ve bağlı ortaklıklardaki şirket payları", 13257),
        ("Kredi kartı alacakları", 0),
        ("Diğer uygun sayılan varlıklar", 17669),
    ],
    "5H": [("Toplam Varlıklar", 1996745)],
    "6I": [
        ("Kısa Vadeli Borçlanmalar", 70069),
        ("Uzun Vadeli Borçlanmaların Kısa Vadeli Kısımları", 92367),
        ("Uzun Vadeli Borçlanmalar", 601817),
        ("Türev Araçlar", 6359),
        ("Finans Sektörü Faaliyetlerinden Borçlar", 0),
        ("Diğer Borçlar", 12963),
    ],
    "6J": [
        ("Kiralama işlemlerinden borçlar", 638976),
        ("Katılım bankalarından alınmış krediler", 0),
        ("Kira sertifikası, sukuk vb. ihraçlar", 0),
        ("Diğer uygun sayılan borçlar", 0),
    ],
}

BEYANLAR = {
    "b1_1": False, "b1_2": False,
    "b2_1": False, "b2_2": False,
    "b3_1": False, "b3_2": False,
    "b4_1": True,   # alkollü içki/gıda -> iştirak kaynaklı, kesin eleme
    "b4_2": False, "b4_3": False, "b4_4": False,
    "b4_5": False, "b4_6": False, "b4_7": False,
}


def olustur() -> dict:
    kalemler = []
    for tablo, satirlar in KALEMLER.items():
        for i, (ad, tutar) in enumerate(satirlar, start=1):
            kalemler.append({
                "tablo": tablo,
                "kalem_no": i if tablo != "5H" else None,
                "kalem_adi": ad,
                "tutar_ham": str(tutar),
            })
    return {
        "bildirim_id": 1566002,
        "ticker": "THYAO",
        "gonderim_ts": "2026-03-04T18:57:54",
        "yil": 2025,
        "periyot": "Yıllık",
        "finansal_tablo_niteligi": "Konsolide",
        "para_birimi_carpani": 1000000,
        "is_duzeltme": False,
        "ozet_gelir_orani": "4.92",
        "ozet_varlik_orani": "18.02",
        "ozet_borc_orani": "7.24",
        "beyanlar": BEYANLAR,
        "kalemler": kalemler,
        "aciklamalar": {},
        "sablon_imzasi": "KAP-2024",
        "raw_sha256": None,
    }


if __name__ == "__main__":
    hedef = pathlib.Path(__file__).with_name("thy_2025_yillik.json")
    hedef.write_text(
        json.dumps(olustur(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"yazıldı: {hedef}")
