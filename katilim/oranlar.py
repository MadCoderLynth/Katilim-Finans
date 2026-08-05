"""Oran yeniden hesabı ve self-check (Spec §0.1).

Bu modül parser'ın doğruluk testidir. Alt tablolardan yeniden hesaplanan
üç oran, formun özet alanlarıyla eşleşmiyorsa parse hatalıdır veya şablon
değişmiştir. İki durumda da kayıt karantinaya alınır, sessizce kabul edilmez.

Formüller (KAFİF özet alanlarından):
    gelir  = (4B + 4C - 4D) / 4E * 100
    varlik = (5F - 5G)      / 5H * 100
    borc   = (6I - 6J)      / 5H * 100
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from .model import KafifBildirim

TOLERANS = Decimal("0.01")  # özet alanı 2 ondalıkla yayımlanıyor


def _yuvarla(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class Oranlar:
    gelir: Decimal | None
    varlik: Decimal | None
    borc: Decimal | None


@dataclass
class SelfCheck:
    gecti: bool
    hesaplanan: Oranlar
    ozet: Oranlar
    sapmalar: dict[str, Decimal]
    notlar: list[str]

    def rapor(self) -> str:
        satirlar = []
        for ad in ("gelir", "varlik", "borc"):
            h = getattr(self.hesaplanan, ad)
            o = getattr(self.ozet, ad)
            fark = self.sapmalar.get(ad)
            isaret = "OK " if (fark is not None and abs(fark) <= TOLERANS) else "!! "
            satirlar.append(
                f"  {isaret}{ad:7s} hesaplanan={h}  ozet={o}  fark={fark}"
            )
        for n in self.notlar:
            satirlar.append(f"  -- {n}")
        return "\n".join(satirlar)


def _bol(pay: Decimal, payda: Decimal) -> Decimal | None:
    if payda is None or payda == 0:
        return None
    return _yuvarla(pay / payda * 100)


def hesapla(b: KafifBildirim) -> Oranlar:
    """Üç oranı alt tablolardan yeniden hesaplar.

    Payda her üç oranda da toplam varlıklar (5H). Bu KAFİF'in kendi
    tanımı; BIST'in max(ort. PD, toplam varlık) paydası daha büyük
    olacağı için buradaki oran BIST oranının üst sınırıdır (Spec §0.2).
    """
    toplam_varlik = b.toplam("5H")

    gelir = _bol(b.toplam("4B") + b.toplam("4C") - b.toplam("4D"), b.toplam("4E"))
    varlik = _bol(b.toplam("5F") - b.toplam("5G"), toplam_varlik)
    borc = _bol(b.toplam("6I") - b.toplam("6J"), toplam_varlik)

    return Oranlar(gelir=gelir, varlik=varlik, borc=borc)


def self_check(b: KafifBildirim) -> SelfCheck:
    """Hesaplanan oranları formun özet alanlarıyla karşılaştırır."""
    hesaplanan = hesapla(b)
    ozet = Oranlar(b.ozet_gelir_orani, b.ozet_varlik_orani, b.ozet_borc_orani)

    sapmalar: dict[str, Decimal] = {}
    notlar: list[str] = []
    gecti = True

    for ad in ("gelir", "varlik", "borc"):
        h = getattr(hesaplanan, ad)
        o = getattr(ozet, ad)
        if h is None or o is None:
            gecti = False
            notlar.append(f"{ad}: karşılaştırılamadı (hesaplanan={h}, ozet={o})")
            continue
        fark = h - o
        sapmalar[ad] = fark
        if abs(fark) > TOLERANS:
            gecti = False
            notlar.append(f"{ad}: sapma {fark} > tolerans {TOLERANS}")

    eksik_t = b.eksik_tablolar()
    if eksik_t:
        gecti = False
        notlar.append(f"eksik tablolar: {', '.join(eksik_t)}")

    eksik_b = b.eksik_beyanlar()
    if eksik_b:
        notlar.append(f"beyanı okunamayan alanlar: {', '.join(eksik_b)}")

    return SelfCheck(gecti, hesaplanan, ozet, sapmalar, notlar)
