"""Tek sayfalık yerel portal — Faz 5.3 (c).

    python -m katilim.portal

**Amaç terminale girmemek, güzel bir site yapmak değil.** Tek dosya, tek
sayfa, tek `<style>` bloğu, CDN yok, JS çerçevesi yok, yeni bağımlılık yok
(stdlib `http.server` + `subprocess`).

## İki kural

1. **Portal VERİ ÜRETMEZ.** Yalnız `katilim.api`'yi çağırır. İkinci bir
   doğruluk kaynağı olmasın diye kart içeriği CSV'den değil `hisse_karti`
   çıktısından geliyor; `kesinlik` çağrı anında hesaplanıyor (5.1 kararı).
2. **Yalnız 127.0.0.1'e bağlanır.** Bu bir yayın sunucusu değil.

## Bakım düğmeleri TEHLİKELİDİR

`bildirimler` ~650, `indir` ~2.600 istek harcıyor ve KAP'a yük bindiriyor.
Bu yüzden: son koşu tarihi ve bütçe düğmenin yanında yazılı, tek tıkla
başlamıyor (onay adımı var), koşarken düğme kilitli, çıktı satır satır
akıyor ve **hata/BütçeAşıldı ekranda kırmızı görünüyor** — sessizce
"bitti" sayılmıyor (kural 7).

Bütçe **kod içinden büyütülmez**: aşağıdaki sabitler CLI'nin varsayılanı
ile aynı ve `BütçeAşıldı` bir arıza değil, kullanıcıya getirilecek bir
karar noktasıdır.
"""

from __future__ import annotations

import html
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import api
from . import olay as _olay

ADRES = "127.0.0.1"
PORT = 8731

# Bakım işleri. Bütçeler CLI varsayılanlarıyla AYNI ve buradan büyütülmez.
BAKIM = {
    "bildirimler": {
        "ad": "Bildirimleri tara",
        "komut": [sys.executable, "-m", "katilim.cli", "bildirimler",
                  "--butce", "800"],
        "butce": "~650 istek (bütçe 800) · ~40 dk",
        "izlenen": Path("veri/evren/bildirim_gecmisi.csv"),
        "aciklama": "KAFİF bildirim kimliklerini tazeler. Kayan pencere "
                    "yüzünden en kritik bakım işi budur.",
    },
    "indir": {
        "ad": "Formları indir",
        "komut": [sys.executable, "-m", "katilim.cli", "indir",
                  "--butce", "2600"],
        "butce": "~2.600 istek (bütçe 2600) · ~2 saat",
        "izlenen": Path("veri/ham/arsiv_indeksi.csv"),
        "aciklama": "Kimliği bilinen ama diskte olmayan formları çeker. "
                    "İdempotan: var olanı yeniden indirmez.",
    },
}

RENK = {
    "UYGUN": "uygun", "TOLERANSTA": "tolerans", "UYGUN_DEGIL": "degil",
    "GORUS_YOK": "notr", "KAPSAM_DISI": "notr",
}

STIL = """
:root{--bg:#12141a;--kart:#1b1e27;--cizgi:#2b303d;--metin:#dde1ea;
--soluk:#828ba0;--vurgu:#6ea8fe;
--yesil:#2ea060;--sari:#b8860b;--kirmizi:#c0392b;--gri:#4a5162}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--metin);
font:14px/1.55 -apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1000px;margin:0 auto;padding:24px 18px 60px}
h1{font-size:18px;margin:0 0 16px;font-weight:600}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;
color:var(--soluk);margin:26px 0 8px;font-weight:600}
form.ara{display:flex;gap:8px;margin-bottom:20px}
input[type=text]{flex:1;background:var(--kart);border:1px solid var(--cizgi);
color:var(--metin);padding:10px 12px;border-radius:6px;font-size:15px;
text-transform:uppercase}
button{background:var(--kart);border:1px solid var(--cizgi);color:var(--metin);
padding:10px 16px;border-radius:6px;cursor:pointer;font-size:14px}
button:hover:not(:disabled){border-color:var(--vurgu)}
button:disabled{opacity:.45;cursor:not-allowed}
.kart{background:var(--kart);border:1px solid var(--cizgi);border-radius:8px;
padding:16px 18px;margin-bottom:14px}
.ust{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;
align-items:flex-start}
.unvan{font-size:16px;font-weight:600}
.meta{color:var(--soluk);font-size:13px;margin-top:3px}
.karar{font-size:26px;font-weight:700;padding:10px 18px;border-radius:8px;
text-align:center;white-space:nowrap}
.karar small{display:block;font-size:11px;font-weight:400;opacity:.85;
margin-top:3px;text-transform:none}
.uygun{background:var(--yesil);color:#fff}
.tolerans{background:var(--sari);color:#fff}
.degil{background:var(--kirmizi);color:#fff}
.notr{background:var(--gri);color:#fff}
.uyari{border-left:3px solid var(--sari);background:#241f10;padding:9px 12px;
border-radius:4px;margin:6px 0;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:var(--soluk);font-weight:600;padding:6px 8px;
border-bottom:1px solid var(--cizgi);white-space:nowrap}
td{padding:6px 8px;border-bottom:1px solid #232733}
tr.gecersiz td{opacity:.42}
.rozet{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11px;
border:1px solid var(--cizgi);color:var(--soluk);margin-right:4px}
.rozet.aktif{border-color:var(--yesil);color:#7fd4a3}
code{font-size:12px;color:#e6b673}
.bos{color:var(--soluk);font-style:italic;padding:8px 0}
/* --- Bakım: GÖRSEL OLARAK AYRI --- */
.bakim{margin-top:56px;border-top:2px dashed #46331f;padding-top:20px}
.bakim h2{color:#d89a4a}
.bakim .kart{border-color:#46331f;background:#1d1913}
.bakim .butce{color:#d89a4a;font-size:12px;margin:4px 0 10px}
.bakim .son{color:var(--soluk);font-size:12px}
pre.cikti{background:#0d0f14;border:1px solid var(--cizgi);border-radius:6px;
padding:10px;max-height:320px;overflow:auto;font-size:12px;white-space:pre-wrap;
margin:10px 0 0}
pre.cikti .hata{color:#ff6b5e;font-weight:600}
"""


# --- HTML üretimi (sunucudan bağımsız, test edilebilir) -------------------


def _e(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _ts(d, kalip="%d.%m.%Y %H:%M") -> str:
    return d.strftime(kalip) if d else "—"


def kart_html(kart: dict) -> str:
    """`api.hisse_karti` çıktısını HTML'e çevirir. Veri ÜRETMEZ."""
    d = kart["durum"]
    an = kart["tarih"]
    p = []
    A = p.append

    A('<div class="kart"><div class="ust"><div>')
    A(f'<div class="unvan">{_e(kart["ticker"])} — {_e(kart["unvan"])}</div>')
    A(f'<div class="meta">{_e(kart["pazar"])} · {_e(kart["sektor"])}</div>')
    A(f'<div class="meta">muafiyet: {_e(kart["muafiyet"])} · '
      f'beyan: {_e(kart["beyan_durumu"])}</div>')
    A('</div>')
    kodlar = ", ".join(d.red_kodlari) or "—"
    A(f'<div class="karar {RENK.get(d.karar, "notr")}">{_e(d.karar)}'
      f'<small>{_e(kodlar)}</small>'
      f'<small>{_ts(d.gecerlilik_baslangic, "%d.%m.%Y")} · '
      f'{_e(d.yil)}/{_e(d.periyot)}</small></div>')
    A('</div>')
    for u in kart["uyarilar"]:
        A(f'<div class="uyari">{_e(u)}</div>')
    A('</div>')

    # --- Endeks üyeliği + XKTUM geçmişi
    A('<h2>Katılım endeksi üyeliği</h2><div class="kart">')
    kat = [x for x in kart["endeksler"] if "KATILIM" in x.upper()]
    if kat:
        A("".join(f'<span class="rozet aktif">{_e(x)}</span>' for x in kat))
    else:
        A('<div class="bos">Katılım endekslerinde üyelik yok.</div>')
    gec = kart["xktum_gecmisi"]
    if gec:
        A('<table><tr><th>XKTUM dönemi</th><th>üye</th><th>kaynak</th></tr>')
        for r in gec:
            var = r["endekste_mi"] == "EVET"
            A(f'<tr><td>{_e(r["donem_baslangic"])} – {_e(r["donem_bitis"])}</td>'
              f'<td>{"EVET" if var else "hayır"}</td>'
              f'<td><code>{_e(r["kaynak_dosya"])}</code></td></tr>')
        A('</table>')
    A('</div>')

    # --- Karar geçmişi
    A('<h2>Karar geçmişi</h2><div class="kart">')
    g = kart["karar_gecmisi"]
    if not g:
        A('<div class="bos">Panelde kaydı yok.</div>')
    else:
        A('<table><tr><th>geçerlilik</th><th>dönem</th><th>karar</th>'
          '<th>gelir</th><th>varlık</th><th>borç</th><th>red kodları</th>'
          '<th></th></tr>')
        for r in g:
            # Düzeltmeyle geçersiz kılınan satır SOLUK — silinmiyor.
            sinif = "" if r["gecerli_kayit"] else ' class="gecersiz"'
            isaret = "✔ geçerli" if r["gecerli_kayit"] else "geçersiz kılındı"
            if r["karantinali"]:
                isaret += " · ⚠ karantina"
            if r["duzeltme_izi"]:
                isaret += f' · {r["duzeltme_izi"]}'
            A(f'<tr{sinif}><td>{_ts(r["gecerlilik_baslangic"])}</td>'
              f'<td>{_e(r["yil"])}/{_e(r["periyot"])}</td>'
              f'<td>{_e(r["karar"])}</td><td>{_e(r["gelir_orani"])}</td>'
              f'<td>{_e(r["varlik_orani"])}</td><td>{_e(r["borc_orani"])}</td>'
              f'<td><code>{_e(r["red_kodlari"] or "—")}</code></td>'
              f'<td class="meta">{_e(isaret)}</td></tr>')
        A('</table>')
    A('</div>')

    # --- Olaylar (kesinlik ÇAĞRI ANINDA hesaplanıyor)
    A('<h2>Olaylar</h2><div class="kart">')
    if not kart["olaylar"]:
        A('<div class="bos">Olay yok — ilk gözlem bir değişim değildir.</div>')
    else:
        A('<table><tr><th>tip</th><th>tarih</th><th>endeks yürürlük</th>'
          '<th>öncüllük</th><th>olgunluk</th><th>not</th></tr>')
        for o in kart["olaylar"]:
            oncul = ((o.endeks_yururluk_ts - o.olay_ts.date()).days
                     if o.endeks_yururluk_ts else "—")
            notlar = []
            if o.karsi_olay:
                notlar.append("karşı olay")
            if o.g1_teyitsiz:
                notlar.append("G1 teyitsiz")
            if o.kilpayi_kriterleri:
                notlar.append(o.kilpayi_kriterleri)
            A(f'<tr><td>{_e(o.olay_tipi)}</td><td>{_ts(o.olay_ts)}</td>'
              f'<td>{_e(o.endeks_yururluk_ts or "—")}</td>'
              f'<td>{_e(oncul)} gün</td>'
              f'<td>{_e(o.kesinlik(an))}</td>'
              f'<td class="meta">{_e(" · ".join(notlar) or "—")}</td></tr>')
        A('</table>')
    A('</div>')

    # --- Düzeltmeler
    A('<h2>Düzeltmeler</h2><div class="kart">')
    dz = kart["duzeltmeler"]
    if not dz:
        A('<div class="bos">Düzeltme yok.</div>')
    else:
        A('<table><tr><th>dönem</th><th>ilk</th><th>düzeltme</th>'
          '<th>değişen</th><th>karar çevirdi mi</th></tr>')
        for r in dz:
            degisen = "; ".join(x for x in (r.get("degisen_oranlar", ""),
                                            r.get("degisen_beyanlar", "")) if x)
            A(f'<tr><td>{_e(r["yil"])}/{_e(r["periyot"])}</td>'
              f'<td>{_e(r.get("ilk_gonderim_ts", "")[:16])}</td>'
              f'<td>{_e(r.get("duzeltme_gonderim_ts", "")[:16])}</td>'
              f'<td>{_e(degisen or "—")}</td>'
              f'<td>{_e(r.get("karar_ceviren_beyan", ""))}</td></tr>')
        A('</table>')
    A('</div>')
    return "".join(p)


def _bakim_html() -> str:
    p = ['<section class="bakim"><h2>Bakım — KAP\'a istek gönderir</h2>']
    p.append('<div class="uyari">Bu düğmeler ağa çıkar ve KAP\'a yük '
             'bindirir. Bütçe kod içinden büyütülmez; <code>BütçeAşıldı</code> '
             'bir arıza değil, karar noktasıdır.</div>')
    for anahtar, i in BAKIM.items():
        yol = i["izlenen"]
        son = (datetime.fromtimestamp(yol.stat().st_mtime).strftime(
            "%d.%m.%Y %H:%M") if yol.exists() else "hiç koşulmadı")
        p.append(
            f'<div class="kart"><div class="unvan">{_e(i["ad"])}</div>'
            f'<div class="meta">{_e(i["aciklama"])}</div>'
            f'<div class="butce">bütçe: {_e(i["butce"])}</div>'
            f'<div class="son">son koşu: {_e(son)} '
            f'<code>{_e(yol)}</code></div>'
            f'<div style="margin-top:10px">'
            f'<button id="b-{anahtar}" onclick="bakimBaslat(\'{anahtar}\')">'
            f'{_e(i["ad"])}</button>'
            f'<span id="o-{anahtar}" class="meta"></span></div>'
            f'<pre class="cikti" id="c-{anahtar}" style="display:none"></pre>'
            f'</div>'
        )
    p.append('</section>')
    return "".join(p)


_JS = """
async function bakimBaslat(is){
  const ad = document.getElementById('b-'+is);
  const cikti = document.getElementById('c-'+is);
  const onay = document.getElementById('o-'+is);
  // TEK TIKLA BAŞLAMAZ: önce onay adımı.
  if(ad.dataset.onay !== '1'){
    ad.dataset.onay='1';
    ad.textContent='Emin misiniz? Tekrar tıklayın';
    onay.textContent=' — bu işlem KAP\\'a yüzlerce istek gönderir';
    setTimeout(()=>{ if(ad.dataset.onay==='1'){ad.dataset.onay='0';
      ad.textContent=ad.dataset.ad; onay.textContent='';} }, 8000);
    return;
  }
  ad.dataset.onay='0'; ad.disabled=true; onay.textContent=' — koşuyor…';
  cikti.style.display='block'; cikti.textContent='';
  // Diğer bakım düğmesi de kilitlensin: iki koşu aynı anda olmamalı.
  document.querySelectorAll('.bakim button').forEach(b=>b.disabled=true);
  try{
    const y = await fetch('/bakim/'+is, {method:'POST'});
    const okuyucu = y.body.getReader();
    const cz = new TextDecoder();
    while(true){
      const {done, value} = await okuyucu.read();
      if(done) break;
      const parca = cz.decode(value, {stream:true});
      // Hata satırlarını KIRMIZI göster; sessizce bitmiş sayılmasın.
      for(const satir of parca.split('\\n')){
        if(!satir) continue;
        const el = document.createElement('span');
        if(/HATA|BÜTÇE|BütçeAşıldı|Traceback|ÇIKIŞ KODU [^0]/i.test(satir)){
          el.className='hata';
        }
        el.textContent = satir + '\\n';
        cikti.appendChild(el);
      }
      cikti.scrollTop = cikti.scrollHeight;
    }
  }catch(e){
    const el=document.createElement('span');
    el.className='hata'; el.textContent='\\nBAĞLANTI HATASI: '+e+'\\n';
    cikti.appendChild(el);
  }finally{
    document.querySelectorAll('.bakim button').forEach(b=>{
      b.disabled=false; b.textContent=b.dataset.ad;});
    onay.textContent='';
  }
}
document.querySelectorAll('.bakim button').forEach(b=>{
  b.dataset.ad=b.textContent; b.dataset.onay='0';});
"""


def sayfa_html(ticker: str | None = None, govde: str | None = None) -> str:
    """Tam sayfa. `govde` verilmezse `ticker`'a göre karttan üretilir."""
    if govde is None:
        govde = ""
        if ticker:
            try:
                govde = kart_html(api.hisse_karti(ticker))
            except api.BilinmeyenTicker:
                govde = (f'<div class="kart"><div class="unvan">'
                         f'{_e(ticker)} — evrende yok</div><div class="meta">'
                         'Bu pay kodu <code>veri/evren/sirketler.csv</code>\'de '
                         'bulunamadı. Yazım hatası olabilir; "kaydı yok" ile '
                         'karıştırmayın.</div></div>')
            except api.VeriYok as e:
                govde = (f'<div class="kart"><div class="unvan">Veri yok</div>'
                         f'<div class="meta">{_e(e)}</div></div>')
    return (
        "<!doctype html><html lang=tr><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        "<title>Katılım Uygunluk Portalı</title>"
        f"<style>{STIL}</style></head><body><main>"
        "<h1>Katılım Uygunluk Portalı</h1>"
        "<form class=ara method=get action=/>"
        f"<input type=text name=ticker autofocus autocomplete=off "
        f"placeholder='Pay kodu (ör. THYAO)' value='{_e(ticker or '')}'>"
        "<button type=submit>Ara</button></form>"
        f"{govde}{_bakim_html()}"
        f"<script>{_JS}</script></main></body></html>"
    )


# --- Sunucu ----------------------------------------------------------------


class _Islek(BaseHTTPRequestHandler):
    def log_message(self, *a):    # sunucu günlüğü konsolu doldurmasın
        pass

    def do_GET(self):
        u = urlparse(self.path)
        if u.path not in ("/", "/index.html"):
            self.send_error(404, "yok")
            return
        q = parse_qs(u.query)
        ticker = (q.get("ticker", [""])[0] or "").strip().upper() or None
        govde = sayfa_html(ticker).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def do_POST(self):
        anahtar = urlparse(self.path).path.rsplit("/", 1)[-1]
        if anahtar not in BAKIM:
            self.send_error(404, "bilinmeyen bakım işi")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        komut = BAKIM[anahtar]["komut"]
        self._yaz(f"$ {' '.join(komut)}\n\n")
        try:
            sp = subprocess.Popen(
                komut, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
                cwd=str(Path.cwd()),
            )
            for satir in sp.stdout:            # satır satır akıt
                self._yaz(satir)
            kod = sp.wait()
            # Kural 7: sıfırdan farklı çıkış sessizce "bitti" sayılmaz.
            self._yaz(f"\nÇIKIŞ KODU {kod}"
                      + ("  (temiz)\n" if kod == 0 else "  — HATA\n"))
        except Exception as e:                 # noqa: BLE001
            self._yaz(f"\nHATA: {e!r}\n")

    def _yaz(self, s: str) -> None:
        try:
            self.wfile.write(s.encode("utf-8"))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


def calistir(port: int = PORT, *, tarayici: bool = True) -> None:
    sunucu = ThreadingHTTPServer((ADRES, port), _Islek)
    url = f"http://{ADRES}:{port}/"
    print(f"Portal: {url}   (durdurmak için Ctrl+C)")
    print("Yalnız 127.0.0.1'e bağlı — bu bir yayın sunucusu değil.")
    if tarayici:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\nkapatılıyor…")
    finally:
        sunucu.server_close()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    port = PORT
    tarayici = True
    if "--tarayici-acma" in argv:
        argv.remove("--tarayici-acma")
        tarayici = False
    if argv and argv[0].isdigit():
        port = int(argv[0])
    try:
        calistir(port, tarayici=tarayici)
    except OSError as e:
        print(f"Sunucu başlatılamadı ({ADRES}:{port}): {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
