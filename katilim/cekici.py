"""KAP çekim katmanı — hız sınırlı, önbellekli, idempotent (Spec §3.2).

Tasarım önceliği sırası:

  1. ÖNBELLEK. En güçlü hız sınırı, isteği hiç yapmamaktır. Diskte olan
     sayfa tekrar çekilmez. Bir ajan döngüde aynı URL'i yüz kez isterse
     ağa bir kez çıkılır.
  2. ASGARİ ARALIK. İstekler arası sabit gecikme + jitter. Tek thread;
     paralellik bilinçli olarak yok.
  3. OTURUM BÜTÇESİ. Sert üst sınır. Aşılınca uyumaz, HATA FIRLATIR —
     çünkü sonsuz uyuyan bir ajan, duran bir ajandan daha kötüdür:
     sorunu gizler.
  4. GERİ ÇEKİLME. 429/5xx'te üstel bekleme, Retry-After'a saygı.

KAP'ın resmî public API'si yok. Bu katman iyi niyetli bir istemci gibi
davranmak zorunda: kendini tanıtır, yavaş gider, hata görünce durur.
"""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

VARSAYILAN_UA = (
    "katilim-motor/0.1 (arastirma amacli; KAFIF uygunluk paneli)"
)


class BütçeAşıldı(RuntimeError):
    """Oturum istek bütçesi doldu. Bilinçli olarak istisna: sessizce
    beklemek yerine duruyoruz."""


class ÇekimHatası(RuntimeError):
    pass


@dataclass
class HızSınırlayıcı:
    """Asgari aralık + jitter + oturum bütçesi.

    min_aralik: iki istek arasındaki en az süre (saniye)
    jitter: 0..jitter arası rastgele ek gecikme; düzenli aralıkla
            istek atmak bot imzasıdır, kırmak iyidir
    oturum_butcesi: bu nesne ömrü boyunca izin verilen azami istek
    """

    min_aralik: float = 2.0
    jitter: float = 1.0
    oturum_butcesi: int = 500

    # None = henüz istek yapılmadı. 0.0 kullanmak hatalıydı: monotonic()
    # sıfır dönerse `if self._son_istek` falsy olur ve gecikme atlanır.
    _son_istek: float | None = field(default=None, repr=False)
    _sayac: int = field(default=0, repr=False)
    _uyku: Callable[[float], None] = field(default=time.sleep, repr=False)
    _saat: Callable[[], float] = field(default=time.monotonic, repr=False)

    @property
    def kullanilan(self) -> int:
        return self._sayac

    def bekle(self) -> float:
        """Sıradaki istekten önce çağrılır. Beklenen süreyi döndürür."""
        if self._sayac >= self.oturum_butcesi:
            raise BütçeAşıldı(
                f"Oturum bütçesi doldu ({self.oturum_butcesi} istek). "
                "Bütçeyi bilinçli olarak yükseltin; otomatik artmaz."
            )

        simdi = self._saat()
        if self._son_istek is None:
            beklenecek = 0.0
        else:
            gecen = simdi - self._son_istek
            hedef = self.min_aralik + random.uniform(0, self.jitter)
            beklenecek = max(0.0, hedef - gecen)
        if beklenecek > 0:
            self._uyku(beklenecek)
        self._son_istek = self._saat()
        self._sayac += 1
        return beklenecek


@dataclass
class Önbellek:
    """URL -> disk. Ham HTML her zaman saklanır (Spec §3.2)."""

    kok: Path

    def __post_init__(self) -> None:
        self.kok = Path(self.kok)
        self.kok.mkdir(parents=True, exist_ok=True)

    def _yol(self, url: str) -> Path:
        ad = hashlib.sha256(url.encode()).hexdigest()[:24]
        return self.kok / f"{ad}.html"

    def var_mi(self, url: str) -> bool:
        return self._yol(url).exists()

    def oku(self, url: str) -> str:
        return self._yol(url).read_text(encoding="utf-8", errors="ignore")

    def yaz(self, url: str, icerik: str) -> Path:
        p = self._yol(url)
        p.write_text(icerik, encoding="utf-8")
        (self.kok / "index.tsv").open("a", encoding="utf-8").write(
            f"{p.name}\t{url}\n"
        )
        return p


class Çekici:
    """Hız sınırlı, önbellekli HTTP istemcisi.

    Ağ katmanı `getir_fn` ile dışarıdan verilir; böylece test edilebilir
    ve `requests` zorunlu bağımlılık olmaz.
    """

    def __init__(
        self,
        onbellek_dizini: str | Path = "veri/onbellek",
        *,
        sinirlayici: HızSınırlayıcı | None = None,
        getir_fn: Callable[[str, dict], tuple[int, str, dict]] | None = None,
        azami_deneme: int = 3,
        user_agent: str = VARSAYILAN_UA,
    ) -> None:
        self.onbellek = Önbellek(onbellek_dizini)
        self.sinirlayici = sinirlayici or HızSınırlayıcı()
        self.getir_fn = getir_fn or _requests_ile_getir
        self.azami_deneme = azami_deneme
        self.user_agent = user_agent
        self.istatistik = {"onbellek": 0, "ag": 0, "yeniden_deneme": 0}

    def getir(self, url: str, *, zorla: bool = False) -> str:
        if not zorla and self.onbellek.var_mi(url):
            self.istatistik["onbellek"] += 1
            return self.onbellek.oku(url)

        basliklar = {"User-Agent": self.user_agent, "Accept-Language": "tr,en"}
        son_hata: Exception | None = None

        for deneme in range(1, self.azami_deneme + 1):
            self.sinirlayici.bekle()
            try:
                durum, govde, yanit_basliklari = self.getir_fn(url, basliklar)
            except Exception as e:  # ağ hatası
                son_hata = e
                self._geri_cekil(deneme, None)
                continue

            if durum == 200:
                self.istatistik["ag"] += 1
                self.onbellek.yaz(url, govde)
                return govde

            if durum in (429, 500, 502, 503, 504):
                son_hata = ÇekimHatası(f"HTTP {durum}: {url}")
                self._geri_cekil(deneme, yanit_basliklari.get("Retry-After"))
                continue

            raise ÇekimHatası(f"HTTP {durum}: {url}")

        raise ÇekimHatası(
            f"{self.azami_deneme} denemede alınamadı: {url}"
        ) from son_hata

    def _geri_cekil(self, deneme: int, retry_after: str | None) -> None:
        self.istatistik["yeniden_deneme"] += 1
        if retry_after:
            try:
                self.sinirlayici._uyku(float(retry_after))
                return
            except (TypeError, ValueError):
                pass
        # üstel: 4, 8, 16 sn + jitter
        self.sinirlayici._uyku(2 ** (deneme + 1) + random.uniform(0, 1))


def _requests_ile_getir(url: str, basliklar: dict) -> tuple[int, str, dict]:
    import requests  # yalnızca gerçekten ağa çıkarken gerekir

    y = requests.get(url, headers=basliklar, timeout=30)
    return y.status_code, y.text, dict(y.headers)
