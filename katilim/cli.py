"""Komut satırı arayüzü.

    python -m katilim.cli dogrula thy.html      # ayrıştır + self-check + karar
    python -m katilim.cli dok     thy.html      # tanı: tabloları imzalarıyla dök
    python -m katilim.cli json    thy.html      # yapılandırılmış çıktı
    python -m katilim.cli toplu   ./html_klasoru --csv panel.csv
    python -m katilim.cli evren --yenile         # şirket evreni (1 istek)
    python -m katilim.cli bildirimler            # KAFİF kimlikleri (Faz 1.2)

`dogrula` çıkışı, self-check geçmezse sıfırdan farklıdır; toplu işlerde
karantina mantığını buna bağlayabilirsiniz.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

from . import evren
from .ayristirici import AyristirmaHatasi, ayristir, dok
from .karar import degerlendir, seri_degerlendir
from .oranlar import self_check


def _oku(yol: str) -> str:
    return pathlib.Path(yol).read_text(encoding="utf-8", errors="ignore")


def _ticker_tahmin(yol: str) -> str:
    return pathlib.Path(yol).stem.split("_")[0].upper()


def cmd_dogrula(args) -> int:
    html = _oku(args.dosya)
    try:
        b = ayristir(html, ticker=_ticker_tahmin(args.dosya))
    except AyristirmaHatasi as e:
        print(f"AYRIŞTIRMA HATASI: {e}", file=sys.stderr)
        return 2

    sc = self_check(b)
    s = degerlendir(b)

    print(f"Şirket        : {b.ticker}")
    print(f"Dönem         : {b.yil} / {b.periyot}  ({b.finansal_tablo_niteligi})")
    print(f"Gönderim      : {b.gonderim_ts}")
    print(f"Sunum birimi  : x{b.para_birimi_carpani:,}".replace(",", "."))
    print(f"Şablon imzası : {b.sablon_imzasi}")
    print(f"SHA256        : {b.raw_sha256[:16]}…")
    print()
    print(f"SELF-CHECK    : {'GEÇTİ' if sc.gecti else 'KALDI'}")
    print(sc.rapor())
    print()
    print(f"KARAR         : {s.ozet()}")
    for g in s.gerekceler:
        print(f"  · {g}")

    evetler = [k for k, v in b.beyanlar.items() if v is True]
    if evetler:
        print(f"  EVET beyanlar : {', '.join(evetler)}")

    if not sc.gecti:
        print(
            "\nUYARI: self-check kaldı; karar güvenilir değil. "
            "Tanı için: python -m katilim.cli dok " + args.dosya,
            file=sys.stderr,
        )
        return 1
    return 0


def cmd_dok(args) -> int:
    print(dok(_oku(args.dosya)))
    return 0


def cmd_json(args) -> int:
    b = ayristir(_oku(args.dosya), ticker=_ticker_tahmin(args.dosya))
    print(json.dumps(b.to_dict(), ensure_ascii=False, indent=2))
    return 0


def cmd_toplu(args) -> int:
    """Bir klasördeki tüm .html dosyalarını işleyip panel üretir.

    Dosya adı konvansiyonu: TICKER_YIL_DONEM.html (örn. THYAO_2025_yillik.html)
    Tolerans durum makinesi şirket bazında, kronolojik sırayla işletilir.
    """
    klasor = pathlib.Path(args.klasor)
    dosyalar = sorted(klasor.glob("*.html")) + sorted(klasor.glob("*.htm"))
    if not dosyalar:
        print(f"{klasor} içinde html bulunamadı", file=sys.stderr)
        return 2

    per_sirket: dict[str, list] = {}
    karantina: list[tuple[str, str]] = []

    for d in dosyalar:
        ticker = _ticker_tahmin(str(d))
        try:
            b = ayristir(_oku(str(d)), ticker=ticker)
        except AyristirmaHatasi as e:
            karantina.append((d.name, str(e)))
            continue
        sc = self_check(b)
        if not sc.gecti:
            karantina.append((d.name, "self-check kaldı: " + "; ".join(sc.notlar)))
            continue
        per_sirket.setdefault(ticker, []).append(b)

    satirlar = []
    for ticker, bildirimler in sorted(per_sirket.items()):
        for b, s in seri_degerlendir(bildirimler):
            satirlar.append({
                "ticker": ticker,
                "yil": b.yil,
                "periyot": b.periyot,
                "gecerlilik_baslangic": b.gonderim_ts.isoformat() if b.gonderim_ts else "",
                "karar": s.karar.value,
                "kodlar": "|".join(s.kodlar),
                "gelir_orani": s.oranlar.gelir if s.oranlar else "",
                "varlik_orani": s.oranlar.varlik if s.oranlar else "",
                "borc_orani": s.oranlar.borc if s.oranlar else "",
                "onceki_donem_toleransta": s.onceki_donem_toleransta,
            })

    basliklar = list(satirlar[0].keys()) if satirlar else []
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=basliklar)
            w.writeheader()
            w.writerows(satirlar)
        print(f"{len(satirlar)} satır yazıldı -> {args.csv}")
    else:
        gen = [max(len(str(b)), *(len(str(r[b])) for r in satirlar)) for b in basliklar]
        print("  ".join(b.ljust(g) for b, g in zip(basliklar, gen)))
        for r in satirlar:
            print("  ".join(str(r[b]).ljust(g) for b, g in zip(basliklar, gen)))

    if karantina:
        print(f"\nKARANTİNA ({len(karantina)} dosya):", file=sys.stderr)
        for ad, sebep in karantina:
            print(f"  {ad}: {sebep}", file=sys.stderr)
    return 1 if karantina else 0


def cmd_evren(args) -> int:
    """BIST şirket evrenini gösterir; --yenile ile KAP'tan tazeler.

    Varsayılan olarak ağa ÇIKMAZ. Çekim bilinçli bir eylem olmalı.
    """
    if not args.yenile:
        sirketler = evren.oku(args.csv)
        if not sirketler:
            print(
                f"{args.csv} yok. Önce: python -m katilim.cli evren --yenile",
                file=sys.stderr,
            )
            return 2
        muaf = sum(1 for s in sirketler if s.mali_sektor_muaf is True)
        belirsiz = [s.ticker for s in sirketler if s.mali_sektor_muaf is None]
        print(f"{args.csv}: {len(sirketler)} pay kodu, "
              f"{len({s.kap_member_uuid for s in sirketler})} tüzel kişi")
        print(f"  mali sektör muaf : {muaf}")
        print(f"  EL İLE BAKILACAK : {len(belirsiz)} -> {', '.join(belirsiz)}")
        return 0

    from .cekici import BütçeAşıldı, HızSınırlayıcı, Çekici

    cekici = Çekici(
        args.onbellek,
        sinirlayici=HızSınırlayıcı(min_aralik=2.0, jitter=1.0, oturum_butcesi=args.butce),
    )
    try:
        html = cekici.getir(evren.BIST_SIRKETLER_URL, zorla=args.zorla)
    except BütçeAşıldı as e:
        print(f"BÜTÇE: {e}", file=sys.stderr)
        return 2

    sirketler, rapor = evren.evreni_ayristir(html)
    if not sirketler:
        # "0 kayıt" ile "sayfa okunamadı" farklı şeyler; ikisi de sessiz
        # geçilmemeli (ROTA_KESFI_RAPORU.md §10).
        print("EVREN BOŞ: sayfa alındı ama tek kayıt çıkarılamadı. "
              "RSC yükü değişmiş olabilir.", file=sys.stderr)
        return 2

    onceki = evren.oku(args.csv)
    arsiv = evren.yaz(sirketler, args.csv)
    eklenen, cikan = evren.fark(onceki, sirketler)

    print(f"EVREN         : {len(sirketler)} pay kodu -> {args.csv}")
    print(rapor.rapor())
    if rapor.belirsiz:
        print(f"  EL İLE BAKILACAK : {', '.join(rapor.belirsiz)}")
    if arsiv:
        print(f"  önceki sürüm     : {arsiv}")
    if onceki:
        print(f"\nEVREN DEĞİŞİMİ: +{len(eklenen)} / -{len(cikan)}")
        if eklenen:
            print(f"  eklenen : {', '.join(eklenen)}")
        if cikan:
            print(f"  çıkan   : {', '.join(cikan)}")
    print(f"\nistek: {cekici.istatistik}")

    # Eşleşmeyen kayıt sessizce düşmedi ama temiz de değil.
    return 1 if (rapor.slug_bulunamayan or rapor.domda_olup_rscde_olmayan) else 0


def cmd_bildirimler(args) -> int:
    """Faz 1.2 — muaf olmayan her tüzel kişi için KAFİF kimliklerini topla.

    Form İNDİRMEZ; yalnız kimlik listesi çıkarır. Sorgu ekseni uuid,
    çıktı ekseni ticker.
    """
    from . import bildirim
    from .cekici import BütçeAşıldı, HızSınırlayıcı, Çekici

    sirketler = evren.oku(args.evren_csv)
    if not sirketler:
        print(f"{args.evren_csv} yok. Önce: python -m katilim.cli evren --yenile",
              file=sys.stderr)
        return 2

    cekici = Çekici(
        args.onbellek,
        sinirlayici=HızSınırlayıcı(
            min_aralik=args.aralik, jitter=1.0, oturum_butcesi=args.butce
        ),
    )

    # 1) DG filtresi doğrulaması. Filtre KAFİF kaybettiriyorsa tam tarama
    #    koşulmaz — bu bir karar noktası, kod içinden çözülmez.
    if args.dg_ornek:
        print(f"DG doğrulaması: {args.dg_ornek} şirkette filtreli/filtresiz karşılaştırma…")
        try:
            dg = bildirim.dg_dogrula(sirketler, cekici, ornek=args.dg_ornek)
        except BütçeAşıldı as e:
            print(f"BÜTÇE: {e}", file=sys.stderr)
            return 2
        for s in dg["satirlar"]:
            print(f"  {s['ticker']:14s} DG {s['dg_kayit']:3d} kayıt / {s['dg_kafif']} KAFİF"
                  f"   filtresiz {s['filtresiz_kayit']:3d} / {s['filtresiz_kafif']}"
                  f"   {'DG DIŞI: ' + str(s['dg_disinda_kafif']) if s['dg_disinda_kafif'] else 'tam'}")
        for s in dg["hata"]:
            print(f"  {s['ticker']:14s} HATA {s['hata']}", file=sys.stderr)
        if not dg["guvenli"]:
            print("\nDG FİLTRESİ KAFİF KAYBETTİRİYOR — tam tarama koşulmadı.",
                  file=sys.stderr)
            print("Filtreyi bırakma kararı size ait (plan 1.2, karar noktası).",
                  file=sys.stderr)
            return 2
        print(f"  -> DG filtresi {dg['ornek']} şirkette KAFİF kaybettirmedi.\n")

    # 2) Tam tarama.
    def ilerleme(sira, toplam, durum):
        if sira % args.her == 0 or sira == toplam:
            print(f"  [{sira:4d}/{toplam}] {'/'.join(durum.tickerlar):14s} "
                  f"{durum.durum:16s} kafif={durum.kafif_sayisi} "
                  f"(istek: {cekici.istatistik['ag']})", flush=True)

    def kontrol_noktasi(t):
        bildirim.yaz(bildirim.indirilenleri_koru(t.satirlar, args.csv), args.csv)
        bildirim.durumlari_yaz(t.durumlar, args.durum_csv)

    kesildi = None
    try:
        toplama = bildirim.gecmisi_topla(
            sirketler, cekici, ilerleme=ilerleme, kontrol_noktasi=kontrol_noktasi
        )
    except BütçeAşıldı as e:
        # Bütçe bir arıza değil, karar noktası: o ana kadarki iş korunur.
        kesildi = str(e)
        print(f"\nBÜTÇE AŞILDI: {e}", file=sys.stderr)
        return 2

    bildirim.yaz(bildirim.indirilenleri_koru(toplama.satirlar, args.csv), args.csv)
    bildirim.durumlari_yaz(toplama.durumlar, args.durum_csv)
    o = bildirim.ozet(toplama)

    print(f"\nBİLDİRİM GEÇMİŞİ -> {args.csv}")
    print(f"  tüzel kişi        : {o['tuzel_kisi']}  (sorgulanan {o['sorgulanan']})")
    print(f"  durum dağılımı    : {o['durum_dagilimi']}")
    print(f"  KAFİF/şirket      : {o['kafif_kova']}")
    print(f"  ticker satırı     : {o['ticker_satiri']}")
    print(f"  BENZERSİZ form    : {o['benzersiz_form']}   <- 1.4'ün indireceği")
    print(f"  gönderim aralığı  : {o['en_eski']} .. {o['en_yeni']}")
    print(f"  dönem dağılımı    : {o['donem_dagilimi']}")
    print(f"  istek             : {cekici.istatistik}")
    if toplama.uyarilar:
        print(f"\nUYARI ({len(toplama.uyarilar)}):", file=sys.stderr)
        for u in toplama.uyarilar[:20]:
            print(f"  {u}", file=sys.stderr)

    okunamayan = o["durum_dagilimi"].get(bildirim.DURUM_OKUNAMADI, 0)
    hatali = o["durum_dagilimi"].get(bildirim.DURUM_CEKIM_HATASI, 0)
    return 1 if (okunamayan or hatali or kesildi) else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="katilim", description=__doc__)
    alt = p.add_subparsers(dest="komut", required=True)

    for ad, fn in (("dogrula", cmd_dogrula), ("dok", cmd_dok), ("json", cmd_json)):
        sp = alt.add_parser(ad)
        sp.add_argument("dosya")
        sp.set_defaults(fn=fn)

    sp = alt.add_parser("toplu")
    sp.add_argument("klasor")
    sp.add_argument("--csv", help="çıktıyı CSV'ye yaz")
    sp.set_defaults(fn=cmd_toplu)

    sp = alt.add_parser("evren")
    sp.add_argument("--yenile", action="store_true", help="KAP'tan tazele (1 istek)")
    sp.add_argument("--csv", default=str(evren.EVREN_CSV))
    sp.add_argument("--onbellek", default="veri/onbellek")
    sp.add_argument("--butce", type=int, default=5, help="oturum istek bütçesi")
    sp.add_argument("--zorla", action="store_true", help="önbelleği atla")
    sp.set_defaults(fn=cmd_evren)

    sp = alt.add_parser("bildirimler")
    sp.add_argument("--evren-csv", default=str(evren.EVREN_CSV))
    sp.add_argument("--csv", default="veri/evren/bildirim_gecmisi.csv")
    sp.add_argument("--durum-csv", default="veri/evren/sorgu_durumu.csv")
    sp.add_argument("--onbellek", default="veri/onbellek")
    sp.add_argument("--butce", type=int, default=800, help="oturum istek bütçesi")
    # Yalnız YUKARI yönde oynatılır. Yavaşlamak nazik, hızlanmak değil.
    sp.add_argument("--aralik", type=float, default=2.0,
                    help="istekler arası asgari saniye (düşürmeyin)")
    sp.add_argument("--dg-ornek", type=int, default=10,
                    help="DG filtresi doğrulaması için şirket sayısı (0=atla)")
    sp.add_argument("--her", type=int, default=25, help="kaç şirkette bir ilerleme bas")
    sp.set_defaults(fn=cmd_bildirimler)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
