"""KAFİF bildiriminin veri modeli.

Spec §1. Ham bildirim, beyanlar ve kalemler ayrı taşınır; oranlar
türetilmiş değerdir ve asla ham veri gibi muamele görmez.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from decimal import Decimal

# 13 beyan bayrağı. Anahtar -> (bölüm, insan okunur ad)
BEYAN_ALANLARI: dict[str, tuple[str, str]] = {
    "b1_1": ("1", "Esas sözleşmede md. 1.2 faaliyeti"),
    "b1_2": ("1", "Esas sözleşmede md. 1.2 şirketine ortaklık"),
    "b2_1": ("2", "Kâr payı imtiyazı"),
    "b2_2": ("2", "Tasfiye payı imtiyazı"),
    "b3_1": ("3", "Md. 1.5 kamuoyu açıklaması"),
    "b3_2": ("3", "Md. 1.5 mahkeme/kamu kurumu kararı"),
    "b4_1": ("4A", "Alkollü içki/gıda"),
    "b4_2": ("4A", "Domuz mamulleri"),
    "b4_3": ("4A", "Tütün üretim/toptan"),
    "b4_4": ("4A", "Kumar"),
    "b4_5": ("4A", "Katılım dışı finans sektörü"),
    "b4_6": ("4A", "Aykırı yayıncılık"),
    "b4_7": ("4A", "Otel/turizm/eğlence"),
}

TUTAR_TABLOLARI = ("4B", "4C", "4D", "4E", "5F", "5G", "5H", "6I", "6J")


@dataclass
class Kalem:
    tablo: str
    kalem_no: int | None
    kalem_adi: str
    tutar_ham: Decimal  # formda göründüğü gibi (sunum birimiyle)

    def tutar_tl(self, carpan: int) -> Decimal:
        return self.tutar_ham * carpan


@dataclass
class KafifBildirim:
    """Tek bir KAFİF bildiriminin tam içeriği."""

    bildirim_id: int | None = None
    ticker: str | None = None
    gonderim_ts: datetime | None = None

    yil: int | None = None
    periyot: str | None = None  # '6 Aylık' | 'Yıllık'
    finansal_tablo_niteligi: str | None = None  # 'Konsolide' | 'Solo'
    para_birimi_carpani: int = 1
    is_duzeltme: bool = False

    # Özet bilgilerde formun kendi hesapladığı oranlar (self-check referansı)
    ozet_gelir_orani: Decimal | None = None
    ozet_varlik_orani: Decimal | None = None
    ozet_borc_orani: Decimal | None = None

    beyanlar: dict[str, bool | None] = field(default_factory=dict)
    kalemler: list[Kalem] = field(default_factory=list)
    aciklamalar: dict[str, str] = field(default_factory=dict)

    sablon_imzasi: str | None = None
    raw_sha256: str | None = None

    # -- yardımcılar ------------------------------------------------------

    def tablo(self, ad: str) -> list[Kalem]:
        return [k for k in self.kalemler if k.tablo == ad]

    def toplam(self, ad: str) -> Decimal:
        """Bir tablonun kalem toplamı.

        Formdaki TOPLAM satırı parse edilmez; toplamı biz hesaplarız.
        Böylece formun toplam satırı da dolaylı olarak doğrulanmış olur.
        """
        return sum((k.tutar_ham for k in self.tablo(ad)), Decimal(0))

    @property
    def donem_anahtari(self) -> tuple[int, str]:
        return (self.yil, self.periyot)

    def eksik_beyanlar(self) -> list[str]:
        return [k for k in BEYAN_ALANLARI if self.beyanlar.get(k) is None]

    def eksik_tablolar(self) -> list[str]:
        var = {k.tablo for k in self.kalemler}
        return [t for t in TUTAR_TABLOLARI if t not in var]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["gonderim_ts"] = self.gonderim_ts.isoformat() if self.gonderim_ts else None
        for key in ("ozet_gelir_orani", "ozet_varlik_orani", "ozet_borc_orani"):
            d[key] = str(d[key]) if d[key] is not None else None
        d["kalemler"] = [
            {**k.__dict__, "tutar_ham": str(k.tutar_ham)} for k in self.kalemler
        ]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "KafifBildirim":
        d = dict(d)
        kalemler = [
            Kalem(
                tablo=k["tablo"],
                kalem_no=k.get("kalem_no"),
                kalem_adi=k["kalem_adi"],
                tutar_ham=Decimal(str(k["tutar_ham"])),
            )
            for k in d.pop("kalemler", [])
        ]
        ts = d.pop("gonderim_ts", None)
        oranlar = {
            key: (Decimal(str(d.pop(key))) if d.get(key) is not None else None)
            for key in ("ozet_gelir_orani", "ozet_varlik_orani", "ozet_borc_orani")
        }
        obj = cls(**d, **oranlar)
        obj.kalemler = kalemler
        obj.gonderim_ts = datetime.fromisoformat(ts) if ts else None
        return obj
