"""Karar motoru (Spec §2).

Kapılar sırayla değerlendirilir; ilk eleme sebebinde durulur ama
tüm finansal aşımlar birlikte raporlanır (tolerans durum makinesi
'herhangi bir kriterde aşım' mantığıyla çalışıyor).

H1-H4 hipotezleri burada kural olarak kodludur ama doğrulanmamıştır;
Faz 4 mutabakatında sınanacak.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from .model import KafifBildirim, BEYAN_ALANLARI
from .oranlar import Oranlar, hesapla

# Limitler ve tolerans bantları (Standart md. 3.5: limitin %10'u kadar aşım)
LIMIT = {
    "gelir": Decimal("5"),
    "varlik": Decimal("33"),
    "borc": Decimal("33"),
}
BANT = {ad: lim * Decimal("1.1") for ad, lim in LIMIT.items()}
# gelir -> 5.5, varlik/borc -> 36.3


class Karar(str, Enum):
    UYGUN = "UYGUN"
    TOLERANSTA = "TOLERANSTA"
    UYGUN_DEGIL = "UYGUN_DEGIL"
    KAPSAM_DISI = "KAPSAM_DISI"
    BELIRSIZ = "BELIRSIZ"


@dataclass
class KararSonucu:
    karar: Karar
    kodlar: list[str] = field(default_factory=list)
    gerekceler: list[str] = field(default_factory=list)
    oranlar: Oranlar | None = None
    asimlar: dict[str, Decimal] = field(default_factory=dict)
    onceki_donem_toleransta: bool = False

    def ozet(self) -> str:
        s = self.karar.value
        if self.kodlar:
            s += " [" + ", ".join(self.kodlar) + "]"
        return s


# Kapı tanımları: (kod, beyan alanları, gerekçe)
KESIN_KAPILAR: list[tuple[str, tuple[str, ...], str]] = [
    ("G1_ESAS_SOZLESME", ("b1_1", "b1_2"),
     "Esas sözleşmede Standart md. 1.2 faaliyeti/ortaklığı beyan edilmiş"),
    ("G2_IMTIYAZ", ("b2_1", "b2_2"),
     "Katılım finansı ilkelerine aykırı imtiyaz beyan edilmiş (Standart md. 1.8)"),
    ("G3_MADDE_15", ("b3_1", "b3_2"),
     "Standart md. 1.5 kapsamında açıklama/karar beyan edilmiş"),
    ("G4_DOGRUDAN_AYKIRI",
     ("b4_1", "b4_2", "b4_3", "b4_4", "b4_5", "b4_6", "b4_7"),
     "Rehber md. 3.1 kapsamında doğrudan aykırı faaliyet/gelir beyan edilmiş"),
]


def _asim_hesapla(oranlar: Oranlar) -> dict[str, Decimal]:
    """Limiti aşan kriterleri ve aşım miktarını döndürür."""
    degerler = {"gelir": oranlar.gelir, "varlik": oranlar.varlik, "borc": oranlar.borc}
    return {
        ad: deger - LIMIT[ad]
        for ad, deger in degerler.items()
        if deger is not None and deger > LIMIT[ad]
    }


def degerlendir(
    b: KafifBildirim,
    *,
    mali_sektor_muaf: bool = False,
    onceki_donem_toleransta: bool = False,
    oranlar: Oranlar | None = None,
) -> KararSonucu:
    """Tek bir bildirim için uygunluk kararı üretir.

    onceki_donem_toleransta: aynı şirketin bir önceki döneminin kararı
    TOLERANSTA ise True. Md. 3.5 gereği bu durumda ikinci dönemde
    herhangi bir aşım doğrudan elemedir.
    """
    if mali_sektor_muaf:
        return KararSonucu(
            Karar.KAPSAM_DISI,
            ["G0_MUAF"],
            ["Mali sektör şirketi; KAFİF doldurma yükümlülüğü yok"],
        )

    kodlar: list[str] = []
    gerekceler: list[str] = []

    # --- Kesin kapılar (G1-G4) -------------------------------------------
    for kod, alanlar, gerekce in KESIN_KAPILAR:
        tetikleyen = [a for a in alanlar if b.beyanlar.get(a) is True]
        if tetikleyen:
            adlar = ", ".join(BEYAN_ALANLARI[a][1] for a in tetikleyen)
            return KararSonucu(
                Karar.UYGUN_DEGIL,
                [kod],
                [f"{gerekce}: {adlar}"],
                oranlar=oranlar or hesapla(b),
                onceki_donem_toleransta=onceki_donem_toleransta,
            )

    # Beyanı okunamayan alan varsa karar güvenilir değil
    eksik = b.eksik_beyanlar()
    if eksik:
        return KararSonucu(
            Karar.BELIRSIZ,
            ["G_EKSIK_BEYAN"],
            [f"Beyanı okunamayan alanlar: {', '.join(eksik)}"],
            oranlar=oranlar or hesapla(b),
            onceki_donem_toleransta=onceki_donem_toleransta,
        )

    # --- Finansal kapılar (G5-G7) ----------------------------------------
    o = oranlar or hesapla(b)
    asimlar = _asim_hesapla(o)

    if not asimlar:
        return KararSonucu(
            Karar.UYGUN, [], [], oranlar=o,
            onceki_donem_toleransta=onceki_donem_toleransta,
        )

    kapi_kodu = {"gelir": "G5_GELIR", "varlik": "G6_VARLIK", "borc": "G7_BORC"}

    # Md. 3.5: önceki dönem toleranstaysa herhangi bir aşım elemedir
    if onceki_donem_toleransta:
        for ad in asimlar:
            kodlar.append(kapi_kodu[ad])
        gerekceler.append(
            "Önceki dönem toleranstaydı; bu dönemde aşım devam ediyor "
            f"({', '.join(f'{a}={getattr(o, a)}%' for a in asimlar)})"
        )
        return KararSonucu(
            Karar.UYGUN_DEGIL, kodlar, gerekceler, o, asimlar, True
        )

    # Bant dışına çıkan var mı?
    bant_disi = [
        ad for ad, _ in asimlar.items()
        if getattr(o, ad) > BANT[ad]
    ]
    if bant_disi:
        for ad in bant_disi:
            kodlar.append(kapi_kodu[ad])
        gerekceler.append(
            "Tolerans bandı aşıldı: "
            + ", ".join(f"{ad}={getattr(o, ad)}% > {BANT[ad]}%" for ad in bant_disi)
        )
        return KararSonucu(
            Karar.UYGUN_DEGIL, kodlar, gerekceler, o, asimlar, False
        )

    # Bant içinde ve önceki dönem temiz -> bir dönem beklenir
    for ad in asimlar:
        kodlar.append(kapi_kodu[ad] + "_TOLERANS")
    gerekceler.append(
        "Limit aşıldı ama tolerans bandı içinde; sonraki değerleme dönemine kadar beklenir: "
        + ", ".join(f"{ad}={getattr(o, ad)}% (limit {LIMIT[ad]}%, bant {BANT[ad]}%)"
                    for ad in asimlar)
    )
    return KararSonucu(Karar.TOLERANSTA, kodlar, gerekceler, o, asimlar, False)


def seri_degerlendir(
    bildirimler: list[KafifBildirim],
    *,
    mali_sektor_muaf: bool = False,
) -> list[tuple[KafifBildirim, KararSonucu]]:
    """Bir şirketin bildirimlerini kronolojik sırayla değerlendirir.

    Tolerans durumu şirket bazında taşınır (H4), kriter bazında değil:
    gelir kriterinden toleransa düşüp sonraki dönem borç kriterinde
    aşan bir şirket elenir.
    """
    sirali = sorted(
        bildirimler,
        key=lambda b: (b.yil or 0, 0 if b.periyot == "6 Aylık" else 1,
                       b.gonderim_ts or 0),
    )
    sonuclar = []
    onceki_toleransta = False
    for b in sirali:
        s = degerlendir(
            b,
            mali_sektor_muaf=mali_sektor_muaf,
            onceki_donem_toleransta=onceki_toleransta,
        )
        sonuclar.append((b, s))
        # BELIRSIZ durumunda önceki durumu koruyoruz; veri eksikliği
        # toleransı sıfırlamamalı.
        if s.karar != Karar.BELIRSIZ:
            onceki_toleransta = s.karar == Karar.TOLERANSTA
    return sonuclar
