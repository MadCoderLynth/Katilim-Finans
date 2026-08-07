"""RSC (Next.js flight) yükü çözücüsünün testleri — ağa çıkmaz.

Bu dosyadaki iki test, **üretimde yakalanmış iki gerçek hatanın** regresyon
testidir. İkisi de aynı sınıftan: sessiz veri kaybı — kayıt kayboluyor ama
hiçbir yerde hata çıkmıyor.

  1. Naif kaçış çözme (`replace('\\"', '"')`) JSON'un kendi kaçışlarını
     bozuyordu; özetinde tırnak geçen bildirimler `json.loads`'ta düşüyordu.
     Gerçek vaka: DITAS, sunucu 26 kayıt dedi, 24 ayıklandı.
  2. Açılış parantezi eşleşmenin SONUNDAN aranıyordu; `{"alan":` kalıbında bu
     bir sonraki (iç) parantezi buluyordu. Gerçek vaka: 746 şirket kaydının
     30'u iç nesneye kayıp şirket sayısı 716 görünüyordu.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from katilim import rsc  # noqa: E402


def _push(json_metni: str) -> str:
    """JSON metnini KAP'ın yaptığı gibi JS dize literaline gömer."""
    return f"<script>self.__next_f.push([1,{json.dumps(json_metni)}])</script>"


def test_govde_kacisli_tirnagi_bozmaz():
    ic = '{"summary":"yönelik \\"Pay Alım Teklifi\\" bildirimi"}'
    html = "<html>" + _push(ic) + "</html>"
    cozulmus = rsc.govde(html)
    assert cozulmus == ic
    assert json.loads(cozulmus)["summary"] == 'yönelik "Pay Alım Teklifi" bildirimi'


def test_ozetinde_tirnak_gecen_kayit_dusmuyor():
    """DITAS vakası: naif çözmede bu kayıt sessizce kayboluyordu."""
    ic = (
        '[{"disclosureBasic":{"disclosureIndex":1482468,'
        '"title":"Pay Alım Teklifi Bilgi Formu",'
        '"summary":"Şirketimiz paylarına yönelik \\"Pay Alım Teklifi\\" süreci"}},'
        '{"disclosureBasic":{"disclosureIndex":1482469,"title":"Sade","summary":null}}]'
    )
    a = rsc.deger_nesneleri("<html>" + _push(ic) + "</html>", "disclosureBasic")
    assert a.bozuk == 0, f"{a.bozuk} kayıt ayrıştırılamadı"
    assert [k["disclosureIndex"] for k in a.kayitlar] == [1482468, 1482469]
    assert '"Pay Alım Teklifi"' in a.kayitlar[0]["summary"]


def test_ic_ice_nesnede_dis_kayit_aliniyor():
    """`{"alan":` kalıbında açılış parantezi eşleşmenin BAŞINDA."""
    ic = '[{"mkkMemberOid":"dis","yuk":{"mkkMemberOid":"ic","x":1},"kapMemberType":"IGS"}]'
    a = rsc.baslayan_nesneler("<html>" + _push(ic) + "</html>", "mkkMemberOid")
    assert a.bozuk == 0
    dis = [k for k in a.kayitlar if k.get("mkkMemberOid") == "dis"]
    assert len(dis) == 1, [k.get("mkkMemberOid") for k in a.kayitlar]
    assert dis[0]["kapMemberType"] == "IGS", "dış nesne eksik ayıklanmış"
    assert dis[0]["yuk"]["mkkMemberOid"] == "ic"


def test_parcaya_bolunmus_kayit_birlestiriliyor():
    """Next.js yükü bir kaydı iki push çağrısına bölebiliyor."""
    html = (
        "<html>"
        + _push('{"disclosureBasic":{"disclosureIndex":1,')
        + _push('"title":"Katılım Finansı İlkeleri Bilgi Formu"}}')
        + "</html>"
    )
    a = rsc.deger_nesneleri(html, "disclosureBasic")
    assert len(a.kayitlar) == 1 and a.kayitlar[0]["disclosureIndex"] == 1


def test_bozuk_kayit_sayiliyor_yutulmuyor():
    """Ayrıştırılamayan aday sessizce düşmez, sayılır."""
    ic = '[{"disclosureBasic":{"disclosureIndex":1}},{"disclosureBasic":{bozuk}}]'
    a = rsc.deger_nesneleri("<html>" + _push(ic) + "</html>", "disclosureBasic")
    assert a.aday == 2 and len(a.kayitlar) == 1 and a.bozuk == 1


def test_push_yoksa_naif_coze_geri_dusuyor():
    """Sentetik/eski gövdeler okunmaya devam etsin diye emniyet kemeri."""
    assert rsc.govde('<div>{\\"a\\":1}</div>') == '<div>{"a":1}</div>'


def test_kapanmayan_nesne_hata_firlatir():
    try:
        rsc.nesne_metni('{"a":{"b":1}', 0)
    except rsc.RSCOkunamadi:
        return
    raise AssertionError("kapanmayan nesnede RSCOkunamadi bekleniyordu")


if __name__ == "__main__":
    import traceback

    t = [(a, f) for a, f in sorted(globals().items()) if a.startswith("test_")]
    kotu = 0
    for a, f in t:
        try:
            f()
            print(f"  ok    {a}")
        except Exception:
            kotu += 1
            print(f"  HATA  {a}\n{traceback.format_exc()}")
    print(f"\n{len(t)-kotu}/{len(t)} test geçti")
    raise SystemExit(1 if kotu else 0)
