"""Çekici testleri — sahte saat ve sahte ağ ile, gerçek istek yapılmaz."""
import sys, pathlib, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from katilim.cekici import HızSınırlayıcı, Çekici, BütçeAşıldı, ÇekimHatası


class SahteSaat:
    def __init__(self): self.t = 0.0; self.uykular = []
    def saat(self): return self.t
    def uyku(self, s): self.uykular.append(s); self.t += s


def _sinirlayici(**kw):
    s = SahteSaat()
    hs = HızSınırlayıcı(min_aralik=2.0, jitter=0.0, **kw)
    hs._uyku = s.uyku; hs._saat = s.saat
    return hs, s


def test_asgari_aralik_uygulaniyor():
    hs, s = _sinirlayici()
    hs.bekle()                      # ilk istek beklemez
    assert s.uykular == []
    hs.bekle()
    assert s.uykular == [2.0], s.uykular


def test_gecen_sure_dusuluyor():
    hs, s = _sinirlayici()
    hs.bekle(); s.t += 5.0          # iş 5 sn sürdü
    hs.bekle()
    assert s.uykular == [], "aralık zaten geçmişse beklememeli"


def test_butce_asilinca_hata():
    hs, _ = _sinirlayici(oturum_butcesi=3)
    for _ in range(3): hs.bekle()
    try:
        hs.bekle()
    except BütçeAşıldı:
        return
    raise AssertionError("bütçe aşımında hata bekleniyordu")


def test_onbellek_agi_atliyor():
    with tempfile.TemporaryDirectory() as d:
        cagri = []
        def sahte(url, b):
            cagri.append(url); return 200, "<html>x</html>", {}
        hs, _ = _sinirlayici()
        c = Çekici(d, sinirlayici=hs, getir_fn=sahte)
        for _ in range(5):
            c.getir("https://kap.org.tr/tr/Bildirim/1")
        assert len(cagri) == 1, f"ağa {len(cagri)} kez çıkıldı, 1 bekleniyordu"
        assert c.istatistik == {"onbellek": 4, "ag": 1, "yeniden_deneme": 0}


def test_429_geri_cekilme_ve_retry_after():
    with tempfile.TemporaryDirectory() as d:
        durumlar = [(429, {"Retry-After": "7"}), (200, {})]
        def sahte(url, b):
            k, h = durumlar.pop(0); return k, "<html>ok</html>", h
        hs, s = _sinirlayici()
        c = Çekici(d, sinirlayici=hs, getir_fn=sahte)
        assert c.getir("https://x/1") == "<html>ok</html>"
        assert 7.0 in s.uykular, s.uykular
        assert c.istatistik["yeniden_deneme"] == 1


def test_404_yeniden_denenmiyor():
    with tempfile.TemporaryDirectory() as d:
        cagri = []
        def sahte(url, b):
            cagri.append(url); return 404, "", {}
        hs, _ = _sinirlayici()
        try:
            Çekici(d, sinirlayici=hs, getir_fn=sahte).getir("https://x/yok")
        except ÇekimHatası:
            assert len(cagri) == 1, "kalıcı hatada yeniden denenmemeli"
            return
        raise AssertionError("hata bekleniyordu")


if __name__ == "__main__":
    import traceback
    t = [(a, f) for a, f in sorted(globals().items()) if a.startswith("test_")]
    kotu = 0
    for a, f in t:
        try:
            f(); print(f"  ok    {a}")
        except Exception:
            kotu += 1; print(f"  HATA  {a}\n{traceback.format_exc()}")
    print(f"\n{len(t)-kotu}/{len(t)} test geçti")
