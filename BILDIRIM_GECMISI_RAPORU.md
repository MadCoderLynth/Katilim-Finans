# KAFİF Bildirim Kimlikleri — Toplama Raporu

**Plan adımı:** 1.2 — Bildirim sorguları
**Tarih:** 2026-08-07
**Modüller:** `katilim/bildirim.py`, `katilim/rsc.py` (yeni), `katilim/cli.py`
**Çıktı:** `veri/evren/bildirim_gecmisi.csv` · `veri/evren/sorgu_durumu.csv`
**Bütçe:** onaylanan 800. **Harcanan 651 istek** (596 + 55 ikinci geçiş).
`BütçeAşıldı` tetiklenmedi, bütçe yükseltilmedi.

---

## 0. Özet

643 tüzel kişi sorgulandı, **1.276 benzersiz KAFİF formu** bulundu. 1.4'ün
indirmesi gereken sayı budur: 2.600'lük onaylı bütçenin yarısından az,
~68 dakika.

**Turun en önemli bulgusu, 1.4'ün aciliyetini yeniden tanımlıyor:**
kayan pencere **keşfi** öldürüyor, **erişimi** değil. Pencereden düşmüş bir
bildirim (THY 2025/6 Aylık, 1472632) `/tr/Bildirim/{id}` rotasından bugün
hâlâ indi — 200, self-check GEÇTİ, 13/13 beyan dolu. Yani **kimlik bir kez
kaydedildiyse form sonra da indirilebiliyor** (n=1, §5).

Ayrıca **iki sessiz veri kaybı hatası bulundu ve düzeltildi** (§6). İkisi de
kendi güvenlik ağlarına yakalandı, gözle değil.

---

## 1. Yöntem ve harcanan bütçe

```
Birinci geçiş : 596 istek (20'si DG doğrulaması) · 173 yeniden deneme · 55 şirket alınamadı
İkinci geçiş  :  55 istek (min_aralik 2,0 -> 4,0) · 0 yeniden deneme · 0 hata
TOPLAM        : 651 istek / onaylı 800
```

Birinci geçişte 55 şirkette `3 denemede alınamadı` çıktı; hatalar alfabetik
olarak kümelenmişti (BFREN…BIMAS, EGEGY…EKDMR), yani sunucu tarafında geçici
bir sıkışma. **Bunlar negatif önbelleğe YAZILMADI** — geçici hata kalıcı
"bu şirkette bildirim yok" kaydına dönüşseydi 55 şirket panelden sessizce
düşerdi. İkinci geçiş yalnız bu 55'i ağdan istedi (kalan 588 sayfa
önbellekten geldi) ve **hepsi başarıyla alındı.**

İkinci geçişte `min_aralik` 2,0'dan **4,0'a çıkarıldı**. Yön bilinçli:
sıkışma gördüğümüzde yavaşlanır, hızlanılmaz.

---

## 2. `disclosureClass=DG` doğrulaması — filtre güvenli

1.0'da filtre yalnız 2 şirkette denenmişti. Burada tohumu sabit (20260807)
rastgele 10 şirkette filtreli ve **filtresiz** sayım karşılaştırıldı:

| Şirket | DG kayıt | DG KAFİF | Filtresiz kayıt | Filtresiz KAFİF | DG dışı KAFİF |
|---|---|---|---|---|---|
| ATAGY | 15 | 3 | 69 | 3 | — |
| POLHO | 25 | 3 | 123 | 3 | — |
| VDFAS | 5 | 0 | 49 | 0 | — |
| ONCSM | 19 | 5 | 132 | 5 | — |
| KLSER | 13 | 2 | 83 | 2 | — |
| ODAS | 15 | 2 | 65 | 2 | — |
| SMRTG | 22 | 2 | 206 | 2 | — |
| SEGMN | 12 | 2 | 127 | 2 | — |
| ALGYO | 26 | 2 | 127 | 2 | — |
| EKOS | 21 | 3 | 104 | 3 | — |

**Hiçbirinde DG dışında KAFİF çıkmadı** (n=12 toplam: 1.0'ın 2'si + bu 10).
Filtre korunuyor; sorgu başına gövde ~5-10 kat küçülüyor.

---

## 3. Sonuçlar

```
tüzel kişi            : 746   (sorgulanan 643, muaf 103 sorgulanmadı)
durum dağılımı        : KAFIF_VAR 537 · KAFIF_YOK 101 · BOS_SONUC 5
                        SAYFA_OKUNAMADI 0 · CEKIM_HATASI 0
KAFİF/şirket dağılımı : 0 form 106 · 1 form 28 · 2 form 337 · 3+ form 172
ticker satırı         : 1.280
BENZERSİZ form        : 1.276      <- 1.4'ün indireceği
gönderim aralığı      : 05.08.2025 19:16 .. 07.08.2026 18:32
```

Ticker satırı ile benzersiz form farkı (4) çoklu kodlu şirketlerden: iki
bildirim (1572643, 1477904) üçer pay koduna dağıtıldı. **Sorgu ekseni uuid,
panel ekseni ticker** ayrımı burada işini yaptı — bu 4 satır 4 ayrı indirme
değil, 2 indirme.

### Dönem dağılımı

| Dönem | Form |
|---|---|
| 2025/6 Aylık | 571 |
| 2025/Yıllık | 610 |
| 2026/6 Aylık | 81 |
| 2025/9 Aylık | 7 |
| 2024/Yıllık | 6 |
| 2026/3 Aylık | 4 |
| 2025/3 Aylık | 1 |

### KAFİF'i olmayan 106 pay kodu

| Grup | Sayı | Yorum |
|---|---|---|
| muafiyeti **belirsiz** (1.1'in 33'ü) | **33** | **hepsi** KAFİF vermemiş |
| muaf değil, beyan yok | 73 | ihtiyatlılık gereği dışarıda (spec §0.4) |

**33 belirsizin tamamının KAFİF vermemiş olması 1.1b'nin karar noktasına
doğrudan girdi.** Ama bu bir kanıt değil, tutarlılık: muaf olan da beyan
vermez, beyan vermeyen muaf olmayan da vermez — ikisi bu rotadan ayırt
edilemiyor. 1.4 bunları `AYIRT_EDILEMEDI` olarak işaretlemeli, `MUAF`
olarak değil.

`BOS_SONUC` (sunucu "bildirim bulunamadı" bastı): DIMES, DOCO, MBFTR,
TRKNT, UMPAS — bir yıl boyunca **hiçbir** DG bildirimi yok. "Sayfa
okunamadı" ile aynı şey değil; ikisi kodda ve CSV'de ayrı temsil ediliyor.

---

## 4. Bulgu — spec §1.2'nin `periyot` alanı eksik

Spec `periyot`u `'6 Aylık' | 'Yıllık'` diye tanımlıyor. **Gözlem daha geniş:**

```
6 Aylık 652 · Yıllık 616 · 9 Aylık 7 · 3 Aylık 5
```

Sebep özel hesap dönemleri. En temiz örnek futbol kulüpleri: FENER, GSRAY,
BJKAS, TSPOR hesap dönemlerini 31 Mayıs'ta kapattıkları için **"2024/Yıllık"
formlarını Ağustos 2025'te** veriyor. BIMAS, TOASO, FMIZP, IZINV gibi
şirketlerde de 3/9 Aylık KAFİF var.

Aşağı akışa iki sonucu var:

1. **Panel kronolojisi (yıl, periyot) etiketine göre sıralanamaz.** Tolerans
   durum makinesi (3.1) dönemleri sırayla taşıyor; sıralama `gonderim_ts`
   üzerinden yapılmalı, dönem etiketi üzerinden değil. Aksi halde
   "2024/Yıllık" 2025/6 Aylık'tan önce sanılır — oysa 2 ay sonra yayımlanmış.
2. **Dönem eşlemesi (4.1) bu şirketlerde birebir değil.** Endeks dönemi
   (1 May / 1 Eki) ile hesap dönemi kayıyor.

Kod bu değerleri zaten olduğu gibi taşıyor (`donem` alanı dizeden okunuyor,
sayısal `period`'dan etiket türetilmiyor), yani **kod değişikliği gerekmedi**;
spec §1.2'nin alan tanımı güncellendi.

---

## 5. Bulgu — pencere keşfi öldürüyor, erişimi değil (n=1)

2.0 pencerenin 1 gün/gün kaydığını ölçmüş ve THY'nin 2025/6 Aylık KAFİF'inin
(1472632) 5→7 Ağustos arasında sorgu sonucundan düştüğünü göstermişti.
Bu turda o kimlik **doğrudan** istendi:

```
https://kap.org.tr/tr/Bildirim/1472632   ->  200, 186.578 karakter
  şablon imzası : 4A|4B|4C|4D|4E|5F|5G|5H|6I|6J|OZET|S1|S2|S3
  gönderim_ts   : 2025-08-05 19:16:18
  dolu beyan    : 13/13
  self-check    : GEÇTİ   (gelir 3,55 / varlık 16,19 / borç 5,07)
```

**Kimlik elimizdeyse form hâlâ iniyor.** Kaybedilen şey formun kendisi değil,
"böyle bir form var" bilgisi.

Bunun üç sonucu:

1. **Asıl zaman duyarlı adım 1.2'ydi, 1.4 değil.** Kimlikler artık
   `bildirim_gecmisi.csv`'de; 1.4 birkaç gün gecikse de bu 1.276 form
   indirilebilir. Plan "1.2 biter bitmez 1.4a, araya 1.1b sokma" diyordu —
   **bu kısıt gevşedi.** Sıralama kararı sizin.
2. **Önbellek fiilen pencere genişletti.** THYAO ve ASELS sorgu sayfaları
   5 Ağustos'tan kalma olduğu için bu iki şirkette panel 2 gün daha derin:
   1472632 ve 1472641 bugünkü pencerede yok ama listemizde var. Yani
   **veri kümesinin penceresi şirketler arasında tekdüze değil** — küçük
   ama dürüstçe kaydedilmesi gereken bir asimetri.
3. **Düzenli 1.2 koşusu artık en kritik bakım işi.** Her koşu o günün
   penceresindeki kimlikleri kalıcılaştırıyor.

**Uyarı: n=1.** Tek bildirim, tek şirket. Buna dayanıp 1.4 ertelenecekse
önce birkaç kimlikle daha sınanmalı.

**Yan kazanç:** parser ikinci bir gerçek KAP belgesinde daha doğrulandı
(THY 2025/6 Aylık, farklı oranlar, self-check GEÇTİ). 1.3'ün 20/20 kapısına
sayılacak ilk fazladan gözlem.

---

## 6. Bulgu — iki sessiz veri kaybı hatası (bulundu, düzeltildi)

İkisi de **kodun kendi denetimlerine** yakalandı; gözle bakarak fark
edilmezdi. Ortak modül `katilim/rsc.py` bu yüzden açıldı.

### 6.1 RSC kaçış çözme

Yük, JS dize literaline gömülü JSON. Eski yol `html.replace('\\"', '"')`
ile çözüyordu; bu JSON'un **kendi** kaçışlarını bozuyor:

```
JSON            : {"summary":"yönelik \"Pay Alım Teklifi\" süreci"}
JS literalinde  : {\"summary\":\"yönelik \\\"Pay Alım Teklifi\\\" süreci\"}
naif replace    : {"summary":"yönelik \\"Pay Alım Teklifi\\" süreci"}   BOZUK
```

Sonuç: **özetinde tırnak geçen her bildirim `json.loads`'ta sessizce
düşüyordu.** Yakalayan denetim: sunucunun ilan ettiği kayıt sayısı ile
ayıklanan sayının karşılaştırılması — DITAS 26 dedi, 24 ayıklandı; DOHOL
17 dedi, 16 ayıklandı. Doğru yol: JS literalini `json.loads` ile çözmek.

### 6.2 Açılış parantezi konumu

Düzeltirken **yeni bir konum varsayımı** yapıldı: nesnenin açılış parantezi
regex eşleşmesinin *sonundan* aranıyordu. `{"alan":` kalıbında bu bir
sonraki (iç) parantezi buluyor. Sonuç: 746 şirket kaydının 30'u iç nesneye
kayıyor, evren 716 görünüyordu. Yakalayan denetim: yeni ayrıştırmanın
`sirketler.csv` ile **satır satır** karşılaştırılması.

Düzeltmeden sonra evren yeniden ayrıştırıldı: **795 satır, tıpatıp aynı.**
1.1'in çıktısı etkilenmedi.

`Ayiklama.bozuk` sayacı artık her iki çağrı yerinde de sıfır olmalı;
sıfır değilse `SorguSonucu.eksik_ayiklama` uyarı üretiyor ve `evren`
`EvrenOkunamadi` fırlatıyor.

---

## 7. Bulgu — düzeltme bildirimleri yapılandırılmış geliyor

**163 (ticker, yıl, periyot) grubu, 135 şirkette birden çok bildirim
taşıyor.** Yani şirketlerin ~%21'i aynı dönemi pencerede birden fazla kez
vermiş.

RSC yükündeki `isChanged` alanı bunu **ayırt ediyor**:

```
DUZENLENEN  = düzelten (yeni) bildirim
DUZELTILEN  = düzeltilen (eski) bildirim
None        = düzeltme ilişkisi yok
```

Örnek (AHSGY 2025/Yıllık): 1566120 `DUZELTILEN` (04.03.2026) →
1583013 `DUZENLENEN` (02.04.2026).

Bu, OKUBENI'deki açığı kapatıyor: `is_duzeltme` tespiti şu an sayfa
metninde "düzeltme" arıyor ve hiç doğrulanmadı. **Gerçek kaynak bu alan.**
2.3 (düzeltme mantığı) ve 1.3'ün "en az 1 düzeltme bildirimi" örneklem
şartı için 163 aday hazır.

`isChanged` **CSV'ye yazılmadı** — şema promptta sabitlenmişti. Kimlikler
kayıtlı olduğu için ilişki her an yeniden türetilebilir; kalıcılaştırmak
isterseniz `bildirim_gecmisi.csv`'ye `duzeltme_izi` sütunu eklemek tek
satırlık iş. Karar sizin.

---

## 8. 1.4 için maliyet

```
benzersiz form           : 1.276
istek karşılığı          : 1.276  (form başına 1)
tahmini süre (3,2 sn)    : ~68 dakika
onaylanmış bütçe         : 2.600     -> %49'u
```

2.0'ın tahmini ~1.500 formdu; gerçek **1.276**. Fark, KAFİF'i olmayan 106
pay kodundan ve muafların sorgulanmamasından geliyor.

`bildirim_gecmisi.csv`'deki `indirildi_mi` sütunu 1.4 tarafından
işaretlenecek; 1.2 yeniden koşarsa bu işaretler korunuyor
(`indirilenleri_koru`), yani arşivde duran form "indirilmedi" görünmüyor.

---

## 9. Kodda kalan davranış

- **Kural 7 kodda.** `ayikla` üç durumu ayırıyor: DOLU / BOS / `SayfaOkunamadi`
  (istisna). Beklenen çıpaların (RSC kaydı, checkbox satırı, sunucu sayısı,
  tablo içi boş-sonuç metni) hiçbiri yoksa **hata fırlatılıyor**, boş liste
  dönmüyor. Bu turda 0 kez tetiklendi.
- **Negatif önbellek** (`veri/onbellek/negatif.tsv`): kalıcı hata (404 gibi)
  bir kez alınır, sonraki koşularda ağa çıkılmaz. **Geçici hata (429/5xx,
  bağlantı) yazılmaz** — 55 şirketlik kesinti kalıcı bir "bildirim yok"
  kaydına dönüşmedi. Bu turda hiç kalıcı hata olmadı, dosya boş.
- **İçerik imzası, konum değil.** KAFİF satırı `title` metninden tanınıyor
  ve karşılaştırma `metin.normalize` üzerinden — noktasız `ı` tuzağı iki
  tarafta da eleniyor.
- **Sayfalama döngüsü yok.** 2.0'ın ölçümüne güvenildi; ayrıca her sayfada
  sunucu sayısı = ayıklanan kayıt kontrolü var, sayfalama devreye girerse
  bu denetim uyarır.

**Testler: 84 geçiyor** (22 motor + 9 çekici + 23 evren + 8 derinlik +
15 bildirim + 7 rsc). Yeni dosyalar: `tests/test_bildirim.py` (kural 7,
uuid ekseni, muafiyet, kod uyuşmazlığı, CSV gidiş-dönüş) ve
`tests/test_rsc.py` (§6'daki iki hatanın regresyonu). `tests/test_cekici.py`
negatif önbelleğin üç davranışıyla genişledi.
