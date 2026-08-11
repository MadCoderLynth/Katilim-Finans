"""Karar motoru (Spec §2).

Kapılar sırayla değerlendirilir; ilk eleme sebebinde durulur ama
tüm finansal aşımlar birlikte raporlanır (tolerans durum makinesi
'herhangi bir kriterde aşım' mantığıyla çalışıyor).

H1-H4 hipotezleri burada kural olarak kodludur ama doğrulanmamıştır;
Faz 4 mutabakatında sınanacak.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
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


# --- Tolerans zinciri: TEK UYGULAMA ----------------------------------------
#
# ⚠ Bu bölüm zincirin **tek** uygulamasıdır. `panel.panel_uret` buraya
# delege eder; bir zamanlar kendi kopyasını taşıyordu ve `seri_degerlendir`
# bildirim bazında kalınca ikisi ayrıştı: `panel.csv` doğru, `cli toplu`
# sahte eleme üretiyordu. İkinci bir kopya açmayın.

ZINCIR_TEMIZ = ""
ZINCIR_BOSLUGU = "ZINCIR_BOSLUGU"

# Bir dönemin ATLANDIĞINI gösteren asgari sessizlik. KAFİF yarıyıllık:
# ardışık bildirimler arası ölçülen medyan 185 gün, p90 206, en uzun 259
# (1.276 formluk arşiv). 280 gün ≈ 1,5 kadans — bunu aşan aralık, arada
# bir dönemin hiç verilmediği anlamına gelir.
#
# Boşluğu beyan durumuyla aramak YANLIŞ olurdu: panelde satırı olan her
# şirket zaten BEYAN_VAR'dır, yani o sinyal hiç tetiklenmez ve "boşluk yok"
# diye yanıltır. Boşluk şirketin KENDİ serisindeki sessizliktir.
ZINCIR_BOSLUK_GUN = 280


def _zaman(b) -> datetime | None:
    return getattr(b, "gonderim_ts", None)


def _donem(b) -> tuple:
    return (getattr(b, "yil", None), getattr(b, "periyot", None))


def zincirle_degerlendir(
    ogeler: list,
    karar_fn,
    *,
    anahtar_fn=_donem,
    zaman_fn=_zaman,
    bosluk_gun: int = ZINCIR_BOSLUK_GUN,
) -> list[tuple[object, KararSonucu, str]]:
    """Tolerans zincirini DÖNEM bazında yürütür. Zincirin tek uygulaması.

    ## ZİNCİR DÖNEM BAZINDA YÜRÜR, BİLDİRİM BAZINDA DEĞİL (2.3)

    Md. 3.5 ardışık **değerleme dönemlerini** düzenliyor. Aynı dönemin
    düzeltilmiş bir bildirimi YENİ BİR DÖNEM DEĞİLDİR. Zincir bildirim
    listesi üzerinde yürütülürse bir düzeltme, kendi döneminin önceki
    kaydını "önceki dönem" sanar ve toleransı sahte biçimde tetikler —
    3.1'in çevirdiği 5 satırın 4'ü (ALVES, DCTTR, DOGUB, KONTR) bu
    artefakttı.

    ## Sıralama yalnız zaman damgasıyla

    Dönem etiketi kronoloji taşımıyor: 1.2 ölçtü ki periyot yalnız
    6 Aylık/Yıllık değil (`9 Aylık` 7, `3 Aylık` 5 kayıt), ve futbol
    kulüpleri 31 Mayıs kapanışı yüzünden "2024/Yıllık"ı ağustosta veriyor.
    Dönem SIRASI da bu yüzden her dönemin **ilk gönderiminden** türetiliyor.

    Zaman damgası olmayan kayıt en SONA konur: bilinmeyen bir tarihi
    geçmişe yerleştirmek sonraki dönemlerin durumunu sessizce değiştirirdi.

    ## Look-ahead korunuyor (spec §5.1)

    P(n) değerlendirilirken "önceki dönem durumu", P(n−1)'in **P(n)'in
    gönderim anında geçerli olan** kaydından gelir — bugünkü nihai
    kaydından değil. Öğeler gönderim sırasıyla işlenip dönem durumu yol
    boyunca güncellendiği için bu kendiliğinden sağlanıyor.

    `karar_fn(oge, onceki_donem_toleransta) -> KararSonucu`.

    Döner: `(öğe, karar, zincir_notu)` üçlüleri, gönderim sırasında.
    """
    sirali = sorted(
        ogeler,
        key=lambda o: (zaman_fn(o) is None, zaman_fn(o) or datetime.min),
    )

    # Dönem sırası: her dönemin İLK gönderimine göre.
    ilk_gonderim: dict[tuple, datetime] = {}
    for o in sirali:
        a, t = anahtar_fn(o), zaman_fn(o)
        if a not in ilk_gonderim and t:
            ilk_gonderim[a] = t
    donem_sirasi = [a for a, _ in sorted(ilk_gonderim.items(), key=lambda kv: kv[1])]
    onceki_anahtari = {
        d: (donem_sirasi[i - 1] if i else None) for i, d in enumerate(donem_sirasi)
    }

    # Zincir boşluğu: ardışık DÖNEMLER arası sessizlik.
    bosluklu: set[tuple] = set()
    for a, b in zip(donem_sirasi, donem_sirasi[1:]):
        if (ilk_gonderim[b] - ilk_gonderim[a]).days > bosluk_gun:
            bosluklu.add(b)

    # Dönem -> o ana kadar yayımlanmış en son kaydın TOLERANSTA olup olmadığı.
    donem_durumu: dict[tuple, bool] = {}
    sonuclar = []
    for o in sirali:
        a = anahtar_fn(o)
        onceki_a = onceki_anahtari.get(a)
        onceki_tol = donem_durumu.get(onceki_a, False) if onceki_a is not None else False

        s = karar_fn(o, onceki_tol)

        # Bu kayıt KENDİ döneminin durumunu günceller; zinciri ilerletmez.
        #
        # BELIRSIZ durumu SIFIRLAMAZ (kural 2'nin zincir karşılığı: veri
        # eksikliği "temize çıkma" değildir). Dönem bazlı zincirde bu,
        # durumu "yok" bırakmak DEĞİL önceki dönemin durumunu DEVRALMAK
        # demektir — yok bırakmak sonraki dönem için sessizce `False`
        # üretir ve toleransı sıfırlar.
        donem_durumu[a] = (
            onceki_tol if s.karar == Karar.BELIRSIZ else s.karar == Karar.TOLERANSTA
        )
        sonuclar.append(
            (o, s, ZINCIR_BOSLUGU if a in bosluklu else ZINCIR_TEMIZ)
        )
    return sonuclar


def seri_degerlendir(
    bildirimler: list[KafifBildirim],
    *,
    mali_sektor_muaf: bool = False,
    oranlar_fn=None,
) -> list[tuple[KafifBildirim, KararSonucu]]:
    """Bir şirketin bildirimlerini dönem bazlı zincirle değerlendirir.

    Tolerans durumu şirket bazında taşınır (H4), kriter bazında değil:
    gelir kriterinden toleransa düşüp sonraki dönem borç kriterinde
    aşan bir şirket elenir.

    Zincir mantığı `zincirle_degerlendir`'de — tek uygulama.

    `oranlar_fn`: bildirim -> `Oranlar`. Verilmezse oranlar kalemlerden
    hesaplanır. **Panel bunu ÖZET alanını verecek şekilde geçiyor** (H5
    varsayılanı, spec §2.3): iki farklı oran kaynağı kullanmak snapshot ile
    tarihsel paneli sessizce ayrıştırırdı.
    """

    def _karar(b, onceki_tol):
        return degerlendir(
            b,
            mali_sektor_muaf=mali_sektor_muaf,
            onceki_donem_toleransta=onceki_tol,
            oranlar=oranlar_fn(b) if oranlar_fn else None,
        )

    return [(b, s) for b, s, _not in zincirle_degerlendir(bildirimler, _karar)]
