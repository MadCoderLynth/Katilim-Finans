# Devir Notu — 5 Ağustos 2026

Bu belge, projeyi başlatan sohbetin özetidir. Amacı, **kodda ve spec'te
bulunmayan** bulguları korumak. Kod kararları için `CLAUDE.md`, sistem
tasarımı için spec dosyası birincil kaynaktır; burada onları tekrar etmiyoruz.

---

## 1. Proje neden var

Katılım yatırımcısı olarak, son 2-3 yılda BIST Katılım Endeksi'nden çıkan çok
sayıda hisse gözlendi. Amaç: endeks uygunluğunu kendi başımıza, **tarihsel ve
makine okunabilir** biçimde hesaplamak; hem tarama hem de mevcut swing trading
sistemine bağlanacak look-ahead'sız etiket serisi üretmek.

---

## 2. Alan bulguları (kodda yok, kaybolursa yeniden araştırma gerekir)

### 2.1 Kuralları BIST koymuyor

BIST yalnızca uygulayıcı. Kural koyucu **TKBB Danışma Kurulu** ve belgesi
"Pay Senedi İhracı ve Alım-Satım Standardı" (güncel sürüm 18.07.2024) ile ona
bağlı Rehber. Endeksler yılda iki kez, 6 aylık ve yıllık bilanço dönemlerinde
güncelleniyor.

Kaynaklar:
- Standart ve Rehber: `tkbb.org.tr`
- Dönemsel endeks değişiklikleri: Borsa İstanbul "BIST Katılım Endeksleri
  Dönemsel Değişiklikler" PDF'i — **geriye dönük etiketleme için en temiz
  ikincil kaynak, Faz 4 mutabakatında bu kullanılacak**
- Şablon içeriği/hesaplama soruları: katilimendeksi@borsaistanbul.com

### 2.2 Son dönemdeki sıkılaşma — gerçek gerekçe

Kullanıcının hatırladığı "Katar'a yaklaşma" gerekçesi **doğrulanamadı**; resmî
veya yarı resmî böyle bir çerçeveleme bulunamadı. Belgelenebilir sebep kurumsal:
kural yapıcılığın 2021 sonrasında tamamen TKBB Danışma Kurulu Standardı'na
devredilmesi ve Standart'ın 18.07.2024 revizyonu. AAOIFI (Bahreyn merkezli) ile
uyum tartışması literatürde var; Körfez sermayesi argümanı kamuoyunda dolaşmış
olabilir ama kaynaklarda teyit edilemedi.

Sıkılaşan somut maddeler:

1. **md. 1.4 — iştirak look-through genişlemesi.** Müştereken kontrol edilen
   iştirakler dahil edildi. THY'yi endeksten çıkaran madde bu.
2. **md. 1.5 — insan hakları / açık destek maddesi.** 2023-24 konjonktüründe
   eklendi. Mahkeme/kamu kurumu kararı veya şirketin kendi kamuoyu açıklaması.
3. **md. 3.3 — dolaylı hizmet ve kira geliri.** Uygunsuz faaliyet yürüten
   işletmelere dolaylı hizmet ve onlardan kira geliri %5 sepetine girdi.
   AVM/GYO ve lojistik için belirleyici.
4. **md. 3.5 — tolerans daralması.** Limitin %10'u kadar aşımda bir dönem
   bekleme; sonraki dönemde herhangi bir aşım doğrudan eleme.
5. **md. 1.2 — liste genişlemesi.** Tütünde üretim + toptan + dağıtım, çevreye
   büyük zarar, insan fıtratını değiştirmeye yönelik biyolojik/genetik faaliyet.
6. **KAFİF zorunluluğu.** Beyan vermeyen şirket ihtiyatlılık gereği dışarıda
   kalıyor. Çıkışların sessiz ama önemli bir kısmının kaynağı bu.

### 2.3 Global endekslerle farklar

| Standart | Payda | Borç | Nakit/faizli | Alacak | Uygunsuz gelir |
|---|---|---|---|---|---|
| Dow Jones Islamic | 24 ay ort. PD | %33 | %33 | %33 | %5 |
| S&P Shariah | 36 ay ort. PD | %33 | %33 | %49 | %5 |
| MSCI Islamic | Toplam varlık | %33,33 | %33,33 | %33,33 | %5 |
| FTSE Shariah | Toplam varlık | %33 | %33 | var | %5 |
| AAOIFI Std. 21 | PD (ihtilaflı) | %30 | %30 | — | %5 |
| **TKBB / BIST** | Toplam varlık | %33 | %33 | **yok** | %5 |

İki not: DJIM ve S&P 2023'te finansal filtrelerini sadeleştirdi (alacak ve nakit
oranları kaldırıldı). AAOIFI'nin %30 eşiğinin PD'ye mi toplam varlığa mı
uygulanacağı tarama servisleri arasında ihtilaflı.

**En büyük yapısal fark oranlarda değil:** TKBB'nin iştirak look-through'u
global endekslerin hiçbirinde yok. Onlarda konsolide gelirin %5'i yeterli.

### 2.4 Look-through değerlendirmesi

Standart iki yönde birden çalışıyor ve iki yönün savunulabilirliği farklı:

**Aşağı doğru (iştirakler) — savunulabilir.** Uygunsuz iş özkaynak yöntemiyle
değerlenen bir iş ortaklığına park edilirse geliri konsolide gelir tablosuna
hiç girmez; sadece net kâr payı tek satırda görünür. %5'lik gelir testi bu
yapıyı tanım gereği göremez. Look-through bu kaçış yolunu kapatıyor.

**Yukarı doğru (tüzel kişi ortaklar) — ekonomik olarak zayıf.** Temiz bir bağlı
ortaklığın azınlık hissedarının, ana holdingin diğer işlerinde ekonomik payı
yok; nakit akışı yukarı gider, aşağı gelmez. Gerekçe töhmet ve sedd-i zerâi,
yani itibar; nakit akışı değil.

**Asıl tasarım kusuru look-through değil, eşiksiz olması.** Şirketin kendi
tütün perakende geliri %4,9 olabilir, sorun yok; ama %20'lik bir iştirakin esas
sözleşmesinde ilgili faaliyet yazıyorsa — fiilen yapmasa bile — ikili eleme.
Oransal bir eşik hem kaçışı kapatır hem orantısızlığı giderirdi.

### 2.5 Trading açısından sonuç — ölçülecek hipotez

Katılım uygunluk kaybı büyük ölçüde **temel-dışı, dışsal bir şok**. Hissenin
bilançosu, momentumu, hikâyesi değişmeden endeksten düşebiliyor; arkasından
katılım fonlarının zorunlu satışı geliyor.

Bilgi öncüllüğü penceresi:

```
KAFİF yayını ──► [bilgi açık, endeks değişmedi] ──► endeks yürürlük (1 May / 1 Eki)
                        ~4-8 hafta
```

KAFİF, finansal tablolar ilan edildikten en geç 1 işlem günü sonra yayımlanmak
zorunda. Endeks revizyonu ise dönem başında yürürlüğe giriyor.

**Ölçülecek (Faz 5, hipotez — varsayım değil):**
- XKTUM'dan çıkan hisselerin, KAFİF yayın tarihi ve endeks yürürlük tarihi
  etrafındaki getiri dağılımı
- Endekse girenlerde simetrik etki var mı
- Etkinin katılım fonu sahiplik yoğunluğuyla ilişkisi

Etki bulunamazsa modül sinyal değil, yalnız risk filtresi olarak kalır.

### 2.6 Mevcut ücretsiz çözümler (neden kendimiz yapıyoruz)

- **helalfinans.net** — tüm BIST hisseleri, uygunluk + arındırma, 1-5 yıldız
  hassasiyet derecelendirmesi. Veri kaynağı KAFİF. Ücretsiz.
- **helalendeks.tr** — uygunluk raporu + pay başına arındırma hesaplayıcı.
- **Kuveyt Türk ve diğer katılım bankaları** — arındırma oranı listeleri.
- **Borsa İstanbul** — XKTUM bileşen listeleri, dönemsel değişiklik PDF'leri.

Hiçbiri **tarihsel, makine okunabilir panel** vermiyor; hepsi "bugün itibarıyla"
fotoğraf. Backtest için "2024-Q3'te X uygun muydu, hangi kritere takıldı"
sorusu cevapsız kalıyor. Projenin varlık sebebi bu.

---

## 3. Teknik durum (5 Ağustos 2026)

**Faz 0 — tek örnekte doğrulandı, 20/20 kapısı Faz 1'e devredildi.**

Doğrulanan: THY 2025/Yıllık (KAP Bildirim 1566002) gerçek HTML'i üzerinde
parser ilk denemede çalıştı. 14 tablonun hepsi tanındı.

```
Şablon imzası : 4A|4B|4C|4D|4E|5F|5G|5H|6I|6J|OZET|S1|S2|S3
SELF-CHECK    : GEÇTİ  (gelir 4.92 / varlık 18.02 / borç 7.24, fark 0.00)
KARAR         : UYGUN_DEGIL [G4_DOGRUDAN_AYKIRI]
```

THY üç oranı da geçiyor ama 4A/1 (alkollü içki, iştirak kaynaklı) EVET →
kesin eleme. Look-through analizinin ampirik kanıtı bu.

Testler: 22/22 motor, 6/6 çekici.

**Doğrulanmayan:** n=1. Sınanmamış olanlar — solo tablo düzenleyen şirketler,
boş kalan tablolar, farklı kalem sayıları, eski şablon versiyonuyla verilmiş
geçmiş dönem bildirimleri. Spec §4'teki 20/20 kriteri hâlâ karşılanmadı.

**Doğrulanmamış hipotezler (spec §2.3):** H1 (4A'da herhangi bir EVET kesin
eleme — tek gözlem), H2 (kâr payı imtiyazı tasfiye payıyla aynı ağırlıkta),
H3 (BIST paydası max(ort. PD, toplam varlık)), H4 (tolerans şirket bazında).
Faz 4 mutabakatı olmadan panel araştırma çıktısıdır, karar dayanağı değildir.

---

## 4. Sıradaki iş

**Faz 1 — toplama katmanı.** `katilim/cekici.py` hazır ve test edilmiş; üstüne
rotalar kurulacak:

| İhtiyaç | Rota |
|---|---|
| Evren | `/tr/bist-sirketler` |
| Son KAFİF | `/tr/kfif/{id}-{slug}` (yalnız en güncel dönem) |
| Bildirim geçmişi | `/tr/bildirim-sorgu-sonuc?member={uuid}` |
| Tekil bildirim | `/tr/Bildirim/{id}` — **doğrulandı, tüketilebiliyor** |

Bilinen engel: KAP'ta iki ayrı kimlik var (`kfif` slug'ındaki sayısal id ile
sorgudaki member uuid). Eşleme ayrı bir adım, rota keşfiyle karıştırılmamalı.

İlk tur `oturum_butcesi=50` ile, amacı evren doldurmak değil **ölçmek**: sayfa
başına kaç kayıt, `requests` yetiyor mu yoksa `playwright` mi, sorgu sayfalanıyor
mu. Ölçüm yazıldıktan sonra bilinçli yükseltme; `BütçeAşıldı` kod içinden
otomatik büyütülmemeli.

---

## 5. Ortam

- Konum: `C:\Users\anakl\Kodlama\katilim_motor` (OneDrive'dan taşındı — senkron
  git deposunu kilitliyordu)
- Windows / PowerShell, `.venv`, VS Code + Claude Code eklentisi
- Git deposu var, `origin/main` remote bağlı
- Windows konsolu cp1254; `cli.py` stdout'u utf-8'e sabitliyor, CSV `utf-8-sig`
