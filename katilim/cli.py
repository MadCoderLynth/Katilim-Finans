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


def cmd_indir(args) -> int:
    """Faz 1.4a — 1.2'nin listelediği tüm KAFİF formlarını indir ve arşivle.

    AYRIŞTIRMAZ. Parser'a dokunmadığı için 1.3'ü beklemez.
    """
    from . import bildirim, toplayici
    from .cekici import BütçeAşıldı, HızSınırlayıcı, Çekici

    gecmis = bildirim.oku(args.gecmis_csv)
    if not gecmis:
        print(f"{args.gecmis_csv} yok. Önce: python -m katilim.cli bildirimler",
              file=sys.stderr)
        return 2

    if args.ornek:
        # Duman testi: ilk N pay kodunun formları. Parser kapısı DEĞİL,
        # indirme döngüsünün kendi testi.
        secili = sorted({s["ticker"] for s in gecmis})[: args.ornek]
        gecmis = [s for s in gecmis if s["ticker"] in secili]
        print(f"DUMAN TESTİ: {len(secili)} pay kodu, {len(gecmis)} satır")

    cekici = Çekici(
        args.onbellek,
        sinirlayici=HızSınırlayıcı(
            min_aralik=args.aralik, jitter=1.0, oturum_butcesi=args.butce
        ),
    )

    def ilerleme(sira, toplam, kayit):
        if sira % args.her == 0 or sira == toplam:
            print(f"  [{sira:5d}/{toplam}] {kayit.ticker:8s} {kayit.bildirim_id} "
                  f"{kayit.durum:12s} {kayit.bayt:>8,} B "
                  f"(ağ: {cekici.istatistik['ag']})", flush=True)

    def kontrol_noktasi(ind):
        toplayici.indeksi_yaz(ind, args.indeks_csv)

    kesildi = None
    try:
        indirme = toplayici.formlari_indir(
            gecmis, cekici,
            ham_dizini=args.ham,
            ilerleme=ilerleme,
            kontrol_noktasi=kontrol_noktasi,
        )
    except BütçeAşıldı as e:
        # Bütçe bir arıza değil, karar noktası. O ana kadarki iş diskte.
        kesildi = str(e)
        print(f"\nBÜTÇE AŞILDI: {e}", file=sys.stderr)
        print("Kısmi arşiv korundu; bütçeyi bilinçli yükseltip tekrar koşun.",
              file=sys.stderr)
        return 2

    toplayici.indeksi_yaz(indirme, args.indeks_csv)

    # indirildi_mi işaretini 1.2'nin CSV'sine geri yaz.
    inen = {
        k.bildirim_id for k in indirme.kayitlar
        if k.durum in (toplayici.DURUM_INDIRILDI, toplayici.DURUM_ZATEN_VARDI)
    }
    for s in gecmis:
        if s["bildirim_id"] in inen:
            s["indirildi_mi"] = True
    if not args.ornek:
        bildirim.yaz(gecmis, args.gecmis_csv)

    # KAFİF'i olmayan şirketler: sessizce atlanmaz.
    beyan = []
    durum_yolu = pathlib.Path(args.durum_csv)
    if durum_yolu.exists():
        with open(durum_yolu, newline="", encoding="utf-8-sig") as f:
            beyan = toplayici.beyan_durumlari(evren.oku(args.evren_csv), list(csv.DictReader(f)))
        toplayici.beyan_durumlarini_yaz(beyan, args.beyan_csv)

    o = toplayici.ozet(indirme, beyan)
    print(f"\nARŞİV -> {args.ham}")
    print(f"  bildirim          : {o['bildirim']}")
    print(f"  durum dağılımı    : {o['durum_dagilimi']}")
    print(f"  arşivdeki form    : {o['arsivdeki_form']}")
    print(f"  gönderim aralığı  : {o['en_eski']} .. {o['en_yeni']}")
    print(f"  boyut (min/med/max): {o['bayt_min']:,} / {o['bayt_medyan']:,} / {o['bayt_max']:,} B"
          f"   toplam {o['bayt_toplam']/1e6:.0f} MB")
    print(f"  PENCERE DIŞI      : {o['pencere_disi']} kimlik -> "
          f"{o['pencere_disi_inen']} indi, {o['pencere_disi_yok']} yok (404)")
    if beyan:
        print(f"  beyan durumu      : {o['beyan_dagilimi']}")
    print(f"  istek             : {cekici.istatistik}")
    if indirme.uyarilar:
        print(f"\nUYARI ({len(indirme.uyarilar)}):", file=sys.stderr)
        for u in indirme.uyarilar[:20]:
            print(f"  {u}", file=sys.stderr)

    hatali = o["durum_dagilimi"].get(toplayici.DURUM_HATA, 0)
    yok = o["durum_dagilimi"].get(toplayici.DURUM_YOK, 0)
    return 1 if (hatali or yok or kesildi) else 0


def cmd_panel(args) -> int:
    """Faz 1.4b — arşivi ayrıştır, snapshot panelini üret. Ağa çıkmaz."""
    from . import panel, toplayici

    sirketler = evren.oku(args.evren_csv)
    if not sirketler:
        print(f"{args.evren_csv} yok. Önce: python -m katilim.cli evren --yenile",
              file=sys.stderr)
        return 2
    muafiyet = {s.ticker: s.mali_sektor_muaf for s in sirketler}

    def ilerleme(sira, toplam):
        print(f"  {sira}/{toplam} ayrıştırıldı", flush=True)

    try:
        kayitlar, rapor = panel.ayristir_arsiv(
            args.ham,
            indeks_csv=args.indeks_csv,
            evren_tickerlari=set(muafiyet),
            ilerleme=ilerleme,
        )
    except panel.ArsivOkunamadi as e:
        print(f"ARŞİV OKUNAMADI: {e}", file=sys.stderr)
        return 2

    satirlar = panel.snapshot_uret(kayitlar, muafiyet=muafiyet)
    yol = panel.yaz(satirlar, args.csv)
    o = panel.ozet(satirlar, rapor)

    # Faz 3.1 — tolerans zincirli tarihsel panel (spec §1.5 şeması).
    beyanlar = {}
    beyan_yolu = pathlib.Path(args.beyan_csv)
    if beyan_yolu.exists():
        with open(beyan_yolu, newline="", encoding="utf-8-sig") as f:
            beyanlar = {r["ticker"]: r["durum"] for r in csv.DictReader(f)}
    kararlar = panel.panel_uret(kayitlar, sirketler, beyan_durumlari=beyanlar)
    karar_yolu = panel.panel_yaz(kararlar, args.karar_csv)
    ko = panel.panel_ozet(kararlar, snapshot=satirlar)

    # Faz 2.3 — düzeltme çözümü. Eskiler SİLİNMEZ; olay ayrı tabloya.
    from . import toplayici as _t
    gecerli, olaylar = _t.duzeltmeleri_coz(kayitlar)
    duz_yolu = _t.duzeltme_olaylarini_yaz(olaylar, args.duzeltme_csv)

    print(f"\nSNAPSHOT -> {yol}")
    print(f"  panel satırı      : {o['panel_satiri']} "
          f"({o['benzersiz_bildirim']} bildirim, {o['benzersiz_ticker']} pay kodu)")
    print(f"  ayrıştırma        : {o['ayristirilan']} okundu, "
          f"{o['ayristirma_hatasi']} hata, {o['dosyasi_yok']} dosyası yok")
    print(f"  self-check        : {o['self_check']}   karantina: {o['karantina']}")
    print(f"  karar (ÖZET)      : {o['karar_dagilimi']}")
    print(f"  karar (kalem)     : {o['karar_kalem_dagilimi']}")
    print(f"  oran ayrışan      : {o['oran_ayrisiyor']}  "
          f"H5 ayırt edici: {o['h5_ayirt_edici']}  karar çeviren: {o['h5_karar_ceviren']}")
    for s in o["h5_karar_ceviren_liste"]:
        print(f"      * {s}")
    print(f"  şablon imzası     : {o['sablon_imzasi']}")
    print(f"  form etiketi ayrışan: {o['form_etiketi_ayrisan']}")
    print(f"  gönderim aralığı  : {o['en_eski']} .. {o['en_yeni']}")

    print(f"\nTOLERANS ZİNCİRLİ PANEL -> {karar_yolu}")
    print(f"  satır             : {ko['satir']} ({ko['ticker']} pay kodu)")
    print(f"  karar dağılımı    : {ko['karar_dagilimi']}")
    print(f"  önceki dönem tol. : {ko['onceki_donem_tolerans']}")
    print(f"  ZİNCİR BOŞLUĞU    : {ko['zincir_boslugu']} satır")
    print(f"  zincirin çevirdiği: {ko['zincirin_cevirdigi']} satır")
    for t, yil, per, eski, yeni in ko["cevrilen_liste"]:
        print(f"      * {t:7s} {yil}/{per:9s} {eski} -> {yeni}")

    ceviren = [o for o in olaylar if o.karar_ceviren_beyan]
    oranli = [o for o in olaylar if o.oran_degisti]
    print(f"\nDÜZELTME OLAYLARI -> {duz_yolu}")
    print(f"  olay              : {len(olaylar)} "
          f"({len({(o.ticker, o.yil, o.periyot) for o in olaylar})} dönem, "
          f"{len({o.ticker for o in olaylar})} pay kodu)")
    print(f"  geçerli kayıt     : {len(gecerli)} (dönemin en geç bildirimi)")
    print(f"  oranı değişen     : {len(oranli)}")
    print(f"  BEYAN ÇEVİREN     : {len(ceviren)}  <- karar doğrudan değişir")
    for o in ceviren[:10]:
        print(f"      * {o.ticker:7s} {o.yil}/{o.periyot:9s} "
              f"{ {k: f'{a} -> {b}' for k, (a, b) in o.degisen_beyanlar.items()} }")

    if rapor.hatali:
        print(f"\nAYRIŞTIRMA HATASI ({len(rapor.hatali)}):", file=sys.stderr)
        for bid, mesaj in rapor.hatali[:20]:
            print(f"  {bid}: {mesaj}", file=sys.stderr)
    if rapor.evrende_olmayan:
        print(f"\nEVRENDE OLMAYAN KOD: {sorted(set(rapor.evrende_olmayan))}",
              file=sys.stderr)
    return 1 if (rapor.hatali or rapor.dosyasi_yok) else 0


def cmd_ozet(args) -> int:
    """Faz 1.1b — özet sayfalarından pazar / sektör / endeks üyeliği."""
    from . import ozet
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

    def ilerleme(sira, toplam, durum):
        if sira % args.her == 0 or sira == toplam:
            print(f"  [{sira:4d}/{toplam}] {'/'.join(durum.tickerlar):12s} "
                  f"{durum.durum:14s} pazar={durum.pazar or '-':12s} "
                  f"endeks={durum.endeks_sayisi:2d} (ağ: {cekici.istatistik['ag']})",
                  flush=True)

    def kontrol_noktasi(t):
        ozet.durumlari_yaz(t, args.durum_csv)
        ozet.endeks_uyeligi_yaz(t, args.endeks_csv)

    kesildi = None
    try:
        toplama = ozet.ozetleri_topla(
            sirketler, cekici, ilerleme=ilerleme, kontrol_noktasi=kontrol_noktasi
        )
    except BütçeAşıldı as e:
        kesildi = str(e)
        print(f"\nBÜTÇE AŞILDI: {e}", file=sys.stderr)
        print("Kısmi sonuç diskte; bütçeyi bilinçli yükseltip tekrar koşun.",
              file=sys.stderr)
        return 2

    yazilan = ozet.evrene_bas(sirketler, toplama)

    # 33 belirsiz muafiyeti sektör alanıyla yeniden değerlendir.
    # Kapatılamayan MUAF İŞARETLENMEZ: yanlış muafiyet şirketi panelden
    # sessizce düşürür, fazladan sorgulamak yalnız istek harcar.
    yeniden = ozet.belirsizleri_yeniden_degerlendir(sirketler)
    evren.yaz(sirketler, args.evren_csv)
    ozet.endeks_uyeligi_yaz(toplama, args.endeks_csv)
    ozet.durumlari_yaz(toplama, args.durum_csv)

    dagilim: dict[str, int] = {}
    for d in toplama.durumlar:
        dagilim[d.durum] = dagilim.get(d.durum, 0) + 1
    pazarlar: dict[str, int] = {}
    for p in toplama.pazarlar.values():
        pazarlar[p or "(yok)"] = pazarlar.get(p or "(yok)", 0) + 1

    print(f"\nÖZET SAYFALARI -> {args.evren_csv}")
    print(f"  tüzel kişi        : {len(toplama.durumlar)}  (pay koduna yazılan: {yazilan})")
    print(f"  durum             : {dagilim}")
    print(f"  pazar dağılımı    : {dict(sorted(pazarlar.items(), key=lambda kv: -kv[1]))}")
    print(f"  endeks satırı     : {sum(len(v) for v in toplama.endeksler.values())} "
          f"-> {args.endeks_csv}")
    katilim_kod = {
        t for t, e in toplama.endeksler.items()
        if any("KATILIM" in x.upper() for x in e)
    }
    print(f"  KATILIM endeksinde: {len(katilim_kod)} pay kodu")
    print(f"  istek             : {cekici.istatistik}")

    if yeniden:
        kapanan = [x for x in yeniden if x[2] is not None]
        kalan = [x for x in yeniden if x[2] is None]
        print(f"\nBELİRSİZ MUAFİYET: {len(yeniden)} -> kapanan {len(kapanan)}, "
              f"kalan {len(kalan)}")
        for s, _eski, yeni, gerekce in kapanan:
            print(f"  {s.ticker:7s} -> {'MUAF' if yeni else 'MUAF DEĞİL'}: {gerekce}")
        for s, _eski, _yeni, gerekce in kalan:
            print(f"  {s.ticker:7s} -> BELİRSİZ: {gerekce}")
    if toplama.uyarilar:
        print(f"\nUYARI ({len(toplama.uyarilar)}):", file=sys.stderr)
        for u in toplama.uyarilar[:20]:
            print(f"  {u}", file=sys.stderr)

    kotu = sum(
        dagilim.get(k, 0)
        for k in (ozet.DURUM_OKUNAMADI, ozet.DURUM_CEKIM_HATASI, ozet.DURUM_SLUG_YOK)
    )
    return 1 if (kotu or kesildi) else 0


def cmd_olaylar(args) -> int:
    """Faz 5.1 — panelden look-ahead'sız olay serisi. Ağa çıkmaz."""
    from datetime import datetime as _dt

    from . import olay

    kesim = None
    if args.kesim:
        kesim = _dt.strptime(args.kesim, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )
    try:
        olaylar = olay.olaylari_uret(args.panel_csv, args.donem_csv, kesim=kesim)
    except olay.OlayGirdisiYok as e:
        print(f"GİRDİ YOK: {e}", file=sys.stderr)
        return 2

    o = olay.ozet(olaylar, kesim)
    print(f"OLAY SERİSİ{f' (kesim {args.kesim})' if args.kesim else ''}")
    print(f"  olay / pay kodu   : {o['olay']} / {o['pay_kodu']}")
    print(f"  tip               : {o['tip']}")
    print(f"  olgunluk          : {o['kesinlik']}"
          f"   (eşik p95={olay.DUZELTME_P95_GUN} gün)")
    print(f"  karşı olay        : {o['karsi_olay']}  (düzeltme; İPTAL yok)")
    print(f"  G1 teyitsiz       : {o['g1_teyitsiz']}  "
          "(olumlu karar, düzeltmeyle teyit edilmemiş)")
    print(f"  öncüllük (gün)    : medyan {o['oncul_gun_medyan']} "
          f"[{o['oncul_gun_min']}..{o['oncul_gun_max']}]")
    print(f"  p95 sonrası temiz : {o['temiz_pencere_medyan']} gün "
          "<- hız/kesinlik ödünleşmesinin fiyatı (5.2 bunu ölçecek)")

    # İlk bildirim ile karşı olayı AYIRARAK göster: ikisinin penceresi
    # farklı ve 5.2 iki rejimi ayrı ölçecek.
    for ad, alt in (("ilk bildirim", [x for x in olaylar if not x.karsi_olay]),
                    ("karşı olay  ", [x for x in olaylar if x.karsi_olay])):
        g = sorted((x.endeks_yururluk_ts - x.olay_ts.date()).days
                   for x in alt if x.endeks_yururluk_ts)
        if g:
            med = g[len(g) // 2]
            print(f"    {ad}: n={len(alt):3d}  öncüllük medyan {med:3d} gün  "
                  f"-> p95 sonrası {med - olay.DUZELTME_P95_GUN:+d} gün")

    yol = olay.yaz(olaylar, args.csv or olay.OLAY_CSV)
    print(f"\n  {len(olaylar)} olay -> {yol}")
    return 0


def _en_yeni_snapshot() -> str:
    """`veri/panel/` içindeki en yeni `snapshot_*.csv`.

    Sabit bir dosya adı (eskiden `snapshot_20260808.csv`) panel yeniden
    üretildiğinde sessizce BAYAT veriyle mutabakat koşturuyordu. Ad kalıbı
    `snapshot_YYYYMMDD.csv` olduğu için sözlük sırası = tarih sırası.

    Hiç snapshot yoksa yol UYDURULMAZ: var olmayan bir ad dönülür ve
    `mutabakat` okurken `MutabakatGirdisiYok` fırlatır (kural 7 — "dosya
    yok" sessizce "kayıt yok"a dönüşmemeli).
    """
    dizin = pathlib.Path("veri/panel")
    adaylar = sorted(dizin.glob("snapshot_*.csv"))
    return str(adaylar[-1]) if adaylar else str(dizin / "snapshot_YOK.csv")


def _mut_donem_csv():
    from . import mutabakat
    return mutabakat.DONEM_CSV


def _mut_olay_csv():
    from . import mutabakat
    return mutabakat.OLAY_CSV


def _cmd_mutabakat_degisim(args, mutabakat) -> int:
    """Faz 4.2 — resmî listedeki DEĞİŞİMLE karşılaştırma. Ağa çıkmaz."""
    sirketler = evren.oku(args.evren_csv)
    if not sirketler:
        print(f"{args.evren_csv} yok.", file=sys.stderr)
        return 2
    # Değişim modu tolerans zincirli paneli ister: nokta-zaman karar
    # ancak dönemler arası taşınmış durumla doğru olur.
    panel = args.panel_csv
    if "snapshot" in str(panel) and pathlib.Path("veri/panel/panel.csv").exists():
        panel = "veri/panel/panel.csv"
        print(f"  not: değişim modu tolerans zincirli paneli kullanıyor ({panel})")
    try:
        m = mutabakat.karsilastir_degisim(
            panel_csv=panel, donem=args.donem,
            evren_tickerlari={s.ticker for s in sirketler},
            donem_csv=args.donem_csv, olay_csv=args.olay_csv,
        )
        iz = None
        if pathlib.Path(args.duzeltme_csv).exists():
            iz = mutabakat.duzeltme_olay_eslemesi(
                args.duzeltme_csv, olay_csv=args.olay_csv,
                donem_csv=args.donem_csv,
            )
    except mutabakat.MutabakatGirdisiYok as e:
        print(f"GİRDİ YOK: {e}", file=sys.stderr)
        return 2

    oran, k, n = m.uyusmazlik_orani()
    mat = m.matris()
    print(f"DEĞİŞİM MUTABAKATI — {m.donem.etiket} "
          f"(kesim {m.donem.duyuru:%d.%m.%Y}, DUYURU tarihi)")
    print(f"  olay              : {len(m.olaylar)}  {m.sinif_dagilimi()}")
    print(f"  matris            : UYGUN/içeride {mat.get(('UYGUN','ICERIDE'),0)} · "
          f"UYGUN_DEGIL/dışarıda {mat.get(('UYGUN_DEGIL','DISARIDA'),0)} · "
          f"YANLIŞ POZİTİF {mat.get(('UYGUN','DISARIDA'),0)} · "
          f"yanlış negatif {mat.get(('UYGUN_DEGIL','ICERIDE'),0)}")
    print(f"  uyuşmazlık        : {k} / {n} = %{oran*100:.2f}")
    for e in m.uyusmazliklar:
        print(f"    {e.ticker:7s} {e.olay:6s} karar={e.simdiki_karar:12s} "
              f"kod={e.simdiki_kodlar or '-':26s} [{e.hipotez}] {e.on_teshis}")
    print("  hipotez bazında   :")
    for h, d in mutabakat.hipotez_ozeti(m).items():
        print(f"    {h:4s} olay={d['olay']:3d} eşleşen={d['eslesti']:3d} "
              f"uyuşmazlık={d['uyusmazlik']}")
    if iz:
        print(f"  düzeltme izi      : {iz['eslesen']} eşleşen / "
              f"{iz['ters_yon']} ters yön / {iz['karar_ceviren_duzeltme']} toplam")

    taban = mutabakat.taban_oran(panel, m.donem.duyuru)
    print(f"  taban oran        : %{taban[0]*100:.1f} UYGUN (n={taban[1]}) "
          "— testin gücü")
    yol = pathlib.Path(f"MUTABAKAT_{m.donem.etiket}.md")
    yol.write_text(mutabakat.degisim_raporu(m, iz, taban), encoding="utf-8")
    print(f"\n  rapor -> {yol}")
    return 0


def cmd_mutabakat(args) -> int:
    """4.0 nokta-zaman mutabakat; `--donem` verilirse 4.2 DEĞİŞİM mutabakatı.

    İki mod ayrı tutuldu: 4.0 durumu, 4.2 değişimi karşılaştırıyor ve
    ikincisinin örneklemi yalnız giriş/çıkış olayları.
    """
    from . import mutabakat

    if args.donem:
        return _cmd_mutabakat_degisim(args, mutabakat)

    sirketler = evren.oku(args.evren_csv)
    if not sirketler:
        print(f"{args.evren_csv} yok.", file=sys.stderr)
        return 2
    try:
        m = mutabakat.karsilastir(
            sirketler, panel_csv=args.panel_csv, endeks_csv=args.endeks_csv,
            beyan_csv=args.beyan_csv,
        )
        oran_iliski = mutabakat.oran_ayrismasi_duzeltme_iliskisi(args.panel_csv)
    except mutabakat.MutabakatGirdisiYok as e:
        print(f"GİRDİ YOK: {e}", file=sys.stderr)
        return 2

    oran, gercek, n = m.uyusmazlik_orani()
    print(f"ÖN MUTABAKAT (son endeks revizyonu: {m.revizyon:%d.%m.%Y})")
    print(f"  sınıf dağılımı    : {m.sinif_dagilimi()}")
    print(f"  GERÇEK uyuşmazlık : {gercek} / karşılaştırılabilir {n} = %{oran*100:.2f}")
    print(f"  yanlış pozitif    : {sum(1 for s in m.satirlar if s.yanlis_pozitif)}"
          "  (biz UYGUN, BIST dışarıda — pahalı olan hata)")
    print(f"\n  PANELDE YOK ({len(m.panelde_yok)}) — XKTUM üyesi, kaydımız yok:")
    for s in sorted(m.panelde_yok, key=lambda z: z.ticker):
        print(f"    {s.ticker:7s} {s.bizim_karar:16s} {s.unvan[:44]}")
    print(f"\n  GERÇEK UYUŞMAZLIKLAR ({len(m.gercek_uyusmazliklar)}):")
    for s in sorted(m.gercek_uyusmazliklar, key=lambda z: z.ticker):
        print(f"    {s.ticker:7s} karar={s.bizim_karar:12s} "
              f"kod={s.red_kodlari or '-':28s} XKTUM="
              f"{'içinde' if s.xktum_uyesi else 'dışında'}")
    if oran_iliski.get("uygulanamaz"):
        print(f"\n  oran ayrışması ↔ düzeltme: {oran_iliski['uygulanamaz']}")
        return 0
    print("\n  oran ayrışması ↔ düzeltme:")
    print(f"    ayrışan {oran_iliski['oran_ayrisiyor']}, bunların "
          f"{oran_iliski['bunlardan_duzeltme']}'i düzeltme "
          f"(%{oran_iliski['ayrisan_duzeltme_orani']*100:.1f}) · "
          f"panel geneli %{oran_iliski['genel_duzeltme_orani']*100:.1f}")
    return 0


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

    sp = alt.add_parser("indir")
    sp.add_argument("--gecmis-csv", default="veri/evren/bildirim_gecmisi.csv")
    sp.add_argument("--durum-csv", default="veri/evren/sorgu_durumu.csv")
    sp.add_argument("--evren-csv", default=str(evren.EVREN_CSV))
    sp.add_argument("--indeks-csv", default="veri/ham/arsiv_indeksi.csv")
    sp.add_argument("--beyan-csv", default="veri/evren/beyan_durumu.csv")
    sp.add_argument("--ham", default="veri/ham")
    sp.add_argument("--onbellek", default="veri/onbellek")
    sp.add_argument("--butce", type=int, default=2600, help="oturum istek bütçesi")
    sp.add_argument("--aralik", type=float, default=2.0,
                    help="istekler arası asgari saniye (düşürmeyin)")
    sp.add_argument("--ornek", type=int, default=0,
                    help="duman testi: yalnız ilk N pay kodunun formları")
    sp.add_argument("--her", type=int, default=50, help="kaç bildirimde bir ilerleme bas")
    sp.set_defaults(fn=cmd_indir)

    sp = alt.add_parser("olaylar")
    sp.add_argument("--panel-csv", default="veri/panel/panel.csv")
    sp.add_argument("--donem-csv", default="veri/referans/xktum_donemler.csv")
    sp.add_argument("--csv", default=None,
                    help="çıktı yolu (varsayılan: veri/panel/olaylar.csv)")
    sp.add_argument("--kesim", default=None,
                    help="YYYY-MM-DD — seriyi o tarihteki veriyle üret "
                         "(nokta-zaman yeniden üretim)")
    sp.set_defaults(fn=cmd_olaylar)

    sp = alt.add_parser("panel")
    sp.add_argument("--ham", default="veri/ham")
    sp.add_argument("--indeks-csv", default="veri/ham/arsiv_indeksi.csv")
    sp.add_argument("--evren-csv", default=str(evren.EVREN_CSV))
    sp.add_argument("--csv", default=None,
                    help="çıktı yolu (varsayılan: veri/panel/snapshot_{bugün}.csv)")
    sp.add_argument("--karar-csv", default="veri/panel/panel.csv",
                    help="tolerans zincirli panel (Faz 3.1)")
    sp.add_argument("--beyan-csv", default="veri/evren/beyan_durumu.csv")
    sp.add_argument("--duzeltme-csv", default="veri/panel/duzeltme_olaylari.csv")
    sp.set_defaults(fn=cmd_panel)

    sp = alt.add_parser("ozet")
    sp.add_argument("--evren-csv", default=str(evren.EVREN_CSV))
    sp.add_argument("--endeks-csv", default="veri/evren/endeks_uyeligi.csv")
    sp.add_argument("--durum-csv", default="veri/evren/ozet_durumu.csv")
    sp.add_argument("--onbellek", default="veri/onbellek")
    sp.add_argument("--butce", type=int, default=800, help="oturum istek bütçesi")
    sp.add_argument("--aralik", type=float, default=2.0,
                    help="istekler arası asgari saniye (düşürmeyin)")
    sp.add_argument("--her", type=int, default=50, help="kaç şirkette bir ilerleme bas")
    sp.set_defaults(fn=cmd_ozet)

    sp = alt.add_parser("mutabakat")
    sp.add_argument("--donem", default=None,
                    help="revizyon dönemi (ör. 2025-10) — DEĞİŞİM mutabakatı (4.2)")
    sp.add_argument("--donem-csv", default=str(_mut_donem_csv()))
    sp.add_argument("--olay-csv", default=str(_mut_olay_csv()))
    sp.add_argument("--duzeltme-csv", default="veri/panel/duzeltme_olaylari.csv")
    sp.add_argument("--panel-csv", default=_en_yeni_snapshot())
    sp.add_argument("--endeks-csv", default="veri/evren/endeks_uyeligi.csv")
    sp.add_argument("--beyan-csv", default="veri/evren/beyan_durumu.csv")
    sp.add_argument("--evren-csv", default=str(evren.EVREN_CSV))
    sp.set_defaults(fn=cmd_mutabakat)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
