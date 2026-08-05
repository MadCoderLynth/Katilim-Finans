"""Türkçe metin ve sayı normalizasyonu.

KAP çıktısında sayılar Türkçe formatta: binlik ayırıcı nokta, ondalık virgül.
Etiket eşlemesi büyük/küçük harf ve aksana duyarsız yapılır.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation

# Türkçeye özgü harfleri doğrudan ASCII karşılığına eşliyoruz.
# Kritik: 'ı' (noktasız i) Unicode'da ayrıştırılamaz, NFKD ile 'i'ye dönmez.
# Sadece NFKD'ye güvenirsek 'ortaklarının' -> 'ortaklar n' olur ve
# etiket eşlemesi sessizce başarısız olur.
_TR_MAP = str.maketrans({
    "ı": "i", "İ": "i", "I": "i",
    "ş": "s", "Ş": "s",
    "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u",
    "ö": "o", "Ö": "o",
    "ç": "c", "Ç": "c",
    "â": "a", "Â": "a",
    "î": "i", "Î": "i",
    "û": "u", "Û": "u",
})


def normalize(s: str | None) -> str:
    """Etiket eşlemesi için kanonik biçim.

    Küçük harfe indirir, aksanları düşürür, noktalama ve fazla boşlukları temizler.
    'Şirketin  KENDİSİNİN,' ve 'sirketin kendisinin' aynı çıktıyı verir.
    """
    if not s:
        return ""
    s = s.translate(_TR_MAP).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9%]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def contains(haystack: str, needle: str) -> bool:
    """Normalize edilmiş içerik araması."""
    return normalize(needle) in normalize(haystack)


_SAYI_RE = re.compile(r"^-?[\d.\s]*\d(?:,\d+)?$")


def parse_sayi(s: str | None) -> Decimal | None:
    """Türkçe formatlı sayıyı Decimal'e çevirir.

    '1.068.575'  -> 1068575
    '4,92'       -> 4.92
    '0'          -> 0
    ''/None/'-'  -> None
    """
    if s is None:
        return None
    s = s.strip().replace("\xa0", " ")
    if s in ("", "-", "—"):
        return None
    if not _SAYI_RE.match(s):
        return None
    s = s.replace(".", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_evet_hayir(s: str | None) -> bool | None:
    """'EVET' -> True, 'HAYIR' -> False, diğer -> None.

    None dönmesi 'beyan edilmemiş' demektir ve sessizce False'a çevrilmez;
    eksik beyan ile 'hayır' beyanı farklı şeylerdir.
    """
    n = normalize(s)
    if n == "evet":
        return True
    if n == "hayir":
        return False
    return None


_CARPAN_RE = re.compile(r"^([\d.]+)\s*(tl|try)?$", re.IGNORECASE)


def parse_para_carpani(s: str | None) -> int:
    """'1.000.000 TL' -> 1000000, 'TL' -> 1.

    Sunum para birimi alanı tutarların hangi katta verildiğini söyler.
    Yanlış okunması tüm tutarları 10^6 kaydırır, bu yüzden varsayılan yok:
    tanınmayan biçimde hata fırlatır.
    """
    if not s:
        raise ValueError("Sunum para birimi alanı boş")
    t = s.strip().replace("\xa0", " ")
    t = re.sub(r"\s+", " ", t)
    if normalize(t) in ("tl", "try", "turk lirasi"):
        return 1
    m = _CARPAN_RE.match(t)
    if not m:
        raise ValueError(f"Sunum para birimi çözümlenemedi: {s!r}")
    return int(m.group(1).replace(".", ""))


_DONEM_RE = re.compile(r"(\d{4})\s*/\s*(.+)")


def parse_yil_donem(s: str | None) -> tuple[int, str]:
    """'2025 / Yıllık' -> (2025, 'Yıllık')."""
    if not s:
        raise ValueError("Yıl/dönem alanı boş")
    m = _DONEM_RE.search(s.strip())
    if not m:
        raise ValueError(f"Yıl/dönem çözümlenemedi: {s!r}")
    donem = m.group(2).strip()
    n = normalize(donem)
    if "yillik" in n:
        donem_kanonik = "Yıllık"
    elif "6" in n:
        donem_kanonik = "6 Aylık"
    else:
        donem_kanonik = donem
    return int(m.group(1)), donem_kanonik
