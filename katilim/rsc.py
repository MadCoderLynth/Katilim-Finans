"""Next.js RSC (flight) yükünün çözülmesi — KAP sayfalarının ortak veri kabı.

KAP'ın üç sayfası da (şirket listesi, bildirim sorgusu, bildirim) veriyi aynı
biçimde taşıyor: `<script>self.__next_f.push([1,"…"])</script>` çağrılarının
içinde, **JS dize literali olarak kaçışlanmış JSON.**

## Neden ayrı bir modül

Buradaki tek fonksiyonun sessiz bir veri kaybı hatası vardı ve bu hata
üretimde yakalandı (1.2 taraması, DITAS 26 kayıt dedi 24 ayıklandı).

Eski yol yükü `html.replace('\\"', '"')` ile çözüyordu. Bu, JSON'un KENDİ
kaçışlarını da bozar:

    JSON metni        : {"summary":"yönelik \"Pay Alım\" bildirimi"}
    JS literalinde    : {\"summary\":\"yönelik \\\"Pay Alım\\\" bildirimi\"}
    naif replace sonu : {"summary":"yönelik \\"Pay Alım\\" bildirimi"}   ← BOZUK

Yani **özetinde tırnak geçen her bildirim** `json.loads`'ta düşüyor ve
kayıt sessizce yok oluyordu. Doğru yol, JS dize literalini `json.loads` ile
çözmek: çıktı, kaçışları yerinde duran geçerli JSON metni olur.

## Kayıp sayılır, yutulmaz

`Ayiklama.bozuk` alanı, aday olarak görülüp ayrıştırılamayan nesne sayısını
taşır. Çağıran bunu **görmezden gelmemeli**: 0'dan büyükse sayfa yapısı
değişmiş ya da yeni bir kaçış vakası çıkmış demektir. Kural 7'nin aynı
mantığı — "kayıt gelmedi" ile "kaydı okuyamadım" ayrı şeylerdir.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

# self.__next_f.push([1,"…"]) — ikinci öğe JS dize literali.
_PUSH_RE = re.compile(
    r'self\.__next_f\.push\(\s*\[\s*\d+\s*,\s*("(?:[^"\\]|\\.)*")', re.S
)


class RSCOkunamadi(RuntimeError):
    """Yük yapısı beklenen biçimde değil."""


def govde(html: str) -> str:
    """Sayfadaki flight yükünü çözülmüş JSON metni olarak döndürür.

    Parçalar sırayla birleştirilir: Next.js yükü birden çok `push` çağrısına
    bölebiliyor ve bir kayıt tam da sınıra denk gelebiliyor. Birleştirmek,
    parçalanmış kaydı kurtarır.

    Hiç `push` bloğu yoksa naif kaçış çözmeye geri düşülür — bu bir onay
    değil, sentetik/eski gövdeleri okumayı sürdüren bir emniyet kemeri.
    """
    parcalar = []
    for m in _PUSH_RE.finditer(html):
        try:
            parcalar.append(json.loads(m.group(1)))
        except json.JSONDecodeError:
            continue
    if parcalar:
        return "".join(parcalar)
    return html.replace('\\"', '"')


def nesne_metni(metin: str, acilis: int) -> str:
    """`metin[acilis]`'teki '{' ile eşleşen '}' arasını döndürür.

    Alan sırasına dayanan bir regex yerine parantez eşlemesi: KAP alan
    sırasını değiştirirse regex sessizce boş küme döndürürdü — yani
    "kayıt yok" gibi görünen bir ayrıştırma hatası.

    Dize içindeki süslü parantezler ve kaçışlı tırnaklar sayılmaz.
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
    raise RSCOkunamadi("JSON nesnesi kapanmadan gövde bitti")


@dataclass
class Ayiklama:
    """Ayıklamanın kendi kendini denetleme çıktısı."""

    kayitlar: list[dict]
    aday: int

    @property
    def bozuk(self) -> int:
        """Aday olarak görülüp ayrıştırılamayan nesne sayısı. 0 olmalı."""
        return self.aday - len(self.kayitlar)


def _topla(metin: str, kalip: re.Pattern) -> Ayiklama:
    """Kalıbın eşleştiği yerdeki nesneyi ayıklar.

    Açılış parantezi **eşleşmenin başından itibaren** aranır, sonundan değil:
    `{"alan":` biçimindeki kalıpta eşleşme zaten '{' ile başlıyor ve
    sonundan aramak BİR SONRAKİ parantezi bulur. (Bu hata bir kez yapıldı:
    746 şirket kaydının 30'u sessizce iç nesneye kayıyordu.)
    """
    kayitlar: list[dict] = []
    aday = 0
    for m in kalip.finditer(metin):
        acilis = metin.index("{", m.start())
        aday += 1
        try:
            kayitlar.append(json.loads(nesne_metni(metin, acilis)))
        except (json.JSONDecodeError, RSCOkunamadi):
            continue
    return Ayiklama(kayitlar=kayitlar, aday=aday)


def deger_nesneleri(html: str, anahtar: str) -> Ayiklama:
    """`"anahtar": { … }` biçimindeki nesneler (ör. `disclosureBasic`)."""
    return _topla(govde(html), re.compile(rf'"{re.escape(anahtar)}":\s*\{{'))


def baslayan_nesneler(html: str, ilk_alan: str) -> Ayiklama:
    """`{"ilk_alan": …}` ile BAŞLAYAN nesneler (ör. şirket listesi kayıtları)."""
    return _topla(govde(html), re.compile(rf'\{{\s*"{re.escape(ilk_alan)}":'))
