# KAP Rota Keşfi — Ölçüm Raporu

**Plan adımı:** 1.0 — Rota keşfi (ölçüm turu)
**Tarih:** 2026-08-05
**Betik:** `arac/rota_kesfi.py` (tek seferlik; üretim kodu değil)
**Ölçüm ham çıktısı:** `veri/onbellek/rota_kesfi_olcum.json`
**Bütçe:** `HızSınırlayıcı(min_aralik=2.0, jitter=1.0, oturum_butcesi=50)` — **aşılmadı, yükseltilmedi.**

---

## 0. Özet

| Rota | Durum | requests yetiyor mu | Kritik bulgu |
|---|---|---|---|
| 1 — `/tr/bist-sirketler` | 200 | **EVET** | 746 şirket **tek istekte**, gömülü JSON olarak. Pazar bilgisi **yok**. |
| 2 — `/tr/bildirim-sorgu-sonuc?member=` | 200 | **EVET** | Tamamen SSR. Pencere **sabit 1 yıl**; tarih parametreleri yok sayılıyor. |
| 3 — `/tr/Bildirim/{id}` | 200 | **EVET** | Canlı gövde diskteki fixture ile **ayrıştırma düzeyinde birebir**. |
| ek — `/tr/kfif/{id}-{slug}` | 200 | EVET ama **kullanmayın** | Zaman damgası yok, 13 beyanın 3'ü okunamıyor. |

**playwright gerekiyor mu: HAYIR.** Gerekçe §7'de.

**Üç rota da `requests` ile yeterli.** Faz 1 toplama katmanı mevcut
`katilim/cekici.py` üstüne, ek bir tarayıcı bağımlılığı olmadan kurulabilir.

**Faz 2 (tarihsel geri doldurma) bu rotalarla yapılamaz** — bildirim sorgusu
1 yıldan geriye gitmiyor ve pencereyi genişleten bir parametre bulunamadı (§5).

---

## 1. Yöntem ve harcanan bütçe

Önbellek açık çalışıldı; betik beş kez koştu ama zaten çekilmiş URL için ağa
çıkılmadı. Bu yüzden "harcanan istek" için süreç sayacı değil önbellek indeksi
esas alındı. Son koşu tamamen önbellekten servis edildi (`ag: 0`) — yani rapor
tek satır ağ trafiği üretmeden yeniden doğrulanabiliyor.

```
Çekici.istatistik (son koşu)      : {'onbellek': 11, 'ag': 0, 'yeniden_deneme': 0}
Benzersiz başarılı çekim (200)    : 11 URL   → veri/onbellek/index.tsv
Başarısız (404 robots.txt)        : 5 deneme (her koşuda tekrarlandı, önbelleklenmiyor)
TOPLAM HTTP İSTEĞİ                : 16
Tek koşudaki en yüksek sayaç      : 5 / 50
BütçeAşıldı                       : hayır
Yeniden deneme / geri çekilme     : hiç tetiklenmedi (429/5xx görülmedi)
Ölçülen yanıt süreleri            : 0,39 – 1,08 sn (medyan ≈ 0,7)
```

Çekilen 11 URL'in tamamı `veri/onbellek/` altında duruyor; rapor yeniden
üretilebilir, tekrar ağa çıkmadan.

**robots.txt:** `https://kap.org.tr/robots.txt` → 307 → `/tr/robots.txt` → **404**.
KAP yayımlanmış bir robots kuralı sunmuyor; kısıt bulunamadı diye "serbest"
sayılmamalı, nazik davranma gerekçesi (§3.2) aynen geçerli.

---

## 2. Rota 1 — Şirket listesi

```
URL      : https://kap.org.tr/tr/bist-sirketler
Durum    : 200 (yönlendirme yok)   Süre: 0,88 sn
Gövde    : 1.495.849 karakter (1,53 MB)
Görünür metin: 77.452 karakter (%5,2)
```

**requests yetiyor.** Sayfa Next.js (App Router, turbopack) ama liste
sunucuda render ediliyor: HTML'de 837 satırlık gerçek bir `<table>` var.

**Asıl bulgu — veri iki kez mevcut.** DOM tablosunun yanında sayfa, gömülü
RSC (flight) yükünde aynı listeyi **yapılandırılmış JSON** olarak taşıyor.
DOM kazımaya gerek yok:

```json
{"mkkMemberOid":"4028e4a140f2ed720140f376bebb01a7",
 "kapMemberTitle":"TÜRK HAVA YOLLARI A.O.",
 "relatedMemberTitle":"PwC BAĞIMSIZ DENETİM VE SERBEST MUHASEBECİ MALİ MÜŞAVİRLİK A.Ş",
 "stockCode":"THYAO","cityName":"İSTANBUL",
 "relatedMemberOid":"33E5FED7242300EAE0530A4A622B2AEA","kapMemberType":"IGS"}
```

```
Kayıt sayısı        : 746 tüzel kişi
Pay kodu            : 795   (stockCode virgüllü olabilir: "ALBRK, ALK")
kapMemberType       : tamamı 'IGS'
Alanlar             : mkkMemberOid, kapMemberTitle, relatedMemberTitle,
                      stockCode, cityName, relatedMemberOid, kapMemberType
```

**Alan karşılaştırması (Spec §1.1 istekleri):**

| İstenen | Var mı | Nerede |
|---|---|---|
| ticker | ✔ | `stockCode` |
| unvan | ✔ | `kapMemberTitle` |
| member uuid | ✔ | `mkkMemberOid` |
| **pazar (Yıldız/Ana/Alt)** | **✘** | Sayfada hiç yok — `Yıldız Pazar` metni gövdede geçmiyor |

Tabloda pazar yerine **şehir** ve **bağımsız denetim kuruluşu** sütunları var.
Pazar bilgisi XKTUM uygunluğunun ön şartı (Spec §0.4), yani **ikinci bir kaynak
gerekiyor**; bu rota onu vermiyor.

**Sayfalama:** yok. 746 kaydın tamamı tek istekte geliyor. Sayfalama parametresi
izi bulunamadı.

**Bonus — Spec §1.1'in "iki ayrı kimlik" sorunu bu sayfada çözülüyor.**
Satırın `<a href>`'i sayısal id + slug taşıyor:
`/tr/sirket-bilgileri/ozet/1107-turk-hava-yollari-a-o`. Yani `mkkMemberOid`
(RSC yükünden) ile `{sayısal_id}-{slug}` (link'ten) **aynı satırda** eşleşiyor.
Spec bunu ayrı bir adım sayıyordu; ayrı adım değil, tek istekten çıkıyor.

---

## 3. Rota 2 — Bildirim geçmişi

```
URL      : https://kap.org.tr/tr/bildirim-sorgu-sonuc?member=4028e4a140f2ed720140f376bebb01a7
Durum    : 200      Süre: ~0,7 sn
Gövde    : 364.104 karakter    Görünür metin: 23.079
Kayıt    : 98 satır (tek sayfa)
```

**requests yetiyor — sayfa tamamen sunucuda render ediliyor.** Tablo başlıkları:

```
checkbox | # | Tarih | Kod | Fon | Tip | Konu | Özet Bilgi | İlgili Şirketler | Yıl | Periyot | İşlemler
```

**`bildirim_id` nerede:** sayfada `/tr/Bildirim/{id}` linki **yok**. Kimlik,
satırdaki checkbox'ın `id` niteliğinde:
`<input name="notification-checkbox" id="1643242">`. Faz 1 ayıklayıcısı bunu
kullanmalı.

**KAFİF satırları doğrudan ayıklanabiliyor.** Konu metni sabit ("Katılım
Finansı İlkeleri Bilgi Formu"), Yıl ve Periyot ayrı sütunlarda:

| bildirim_id | Tarih | Yıl | Periyot |
|---|---|---|---|
| 1643241 | Bugün 08:01 (05.08.2026) | 2026 | 6 Aylık |
| **1566002** | 04.03.2026 18:57 | 2025 | Yıllık |
| 1472632 | 05.08.2025 19:16 | 2025 | 6 Aylık |

**1566002 listede çıktı** — yani elimizdeki fixture'ın bu rotadan bulunabildiği
uçtan uca doğrulanmış oldu (liste → id → form → ayrıştırıcı).

**Zaman penceresi sabit 1 yıl.** Dönen en eski kayıt `05.08.2025 19:15`, en yeni
`05.08.2026 08:01`. İkinci şirkette (ASELS) de en eski kayıt `05.08.2025 19:34` —
aynı sınır. Bu, kayıt sayısı sınırı değil **tarih sınırı** gibi davranıyor.

**Genelleme kontrolü (n=2):** ASELS (`4028e4a1413b7ef401413bc2251e0047`) aynı
yapıyı verdi: 22 DG kaydı, 3 KAFİF satırı (`1643144`, `1561061`, `1472641`).
Rota THY'ye özel değil.

---

## 4. Rota 3 — Tekil bildirim (canlı vs. disk)

```
URL      : https://kap.org.tr/tr/Bildirim/1566002
Durum    : 200      Süre: 1,08 sn      Gövde: 186.579 karakter
```

Canlı gövde ile `veri/ham/THYAO_2025_yillik.html` ayrıştırılıp karşılaştırıldı:

| Ölçüt | Canlı | Disk |
|---|---|---|
| şablon imzası | `4A\|4B\|4C\|4D\|4E\|5F\|5G\|5H\|6I\|6J\|OZET\|S1\|S2\|S3` | **aynı** |
| kalem sayısı | 55 | **aynı** |
| dolu beyan | 13/13 | **aynı** |
| EVET beyanlar | `b4_1` | **aynı** |
| gönderim_ts | 2026-03-04 18:57:54 | **aynı** |
| self-check | GEÇTİ (sapma 0,00/0,00/0,00) | **aynı** |
| oranlar | 4,92 / 18,02 / 7,24 | **aynı** |
| raw sha256 | `f548dc8cea7f9860…` | `cb86a41e63d11788…` |

**sha256 farkı beklenen ve zararsız:** sayfa markup'ı derleme/oturum kimlikleri
yüzünden istekten isteğe değişiyor, ama **ayrıştırma sonucu birebir aynı.**
Not: `raw_html_sha256` (Spec §1.2) bu yüzden içerik değişikliğinin göstergesi
değil; aynı bildirimi iki kez çekmek iki farklı sha üretir. İdempotanlık
`bildirim_id` üzerinden kurulmalı, sha üzerinden değil.

---

## 5. Parametre sondası — sorgu penceresi genişletilebiliyor mu?

Bildirim sorgusu sayfasında tarih alanı yok; parametreler ampirik denendi.
Temel küme: THYAO, 98 kayıt.

| Denenen parametre | Kayıt | Tarih aralığı | Sonuç |
|---|---|---|---|
| `&fromDate=01.01.2024&toDate=31.12.2024` | 98 | değişmedi | **yok sayıldı** |
| `&year=2024` | 98 | değişmedi | **yok sayıldı** |
| `&startDate=…&endDate=…` | 98 | değişmedi | **yok sayıldı** |
| `&disclosureClass=DG` | **12** | aynı pencere | **ÇALIŞIYOR** — alt küme |

**`disclosureClass=DG` gerçek bir filtre.** KAFİF bildirimleri "DG" (Diğer
Bildirimler) sınıfında; 98 → 12 kayıt, yani şirket başına indirilecek liste
~8 kat küçülüyor ve KAFİF satırlarının hepsi korunuyor (THY 3/3, ASELS 3/3).
Faz 1'de bu parametre kullanılmalı. **Uyarı:** ölçüm n=2; her şirkette KAFİF'in
DG sınıfında olduğu varsayım olarak işaretlenmeli.

**Tarihsel derinlik açık soru.** Üç tarih parametresi de yok sayıldı. 1 yıldan
geriye gitmenin yolu bu turda bulunamadı (§8).

---

## 6. Ek bulgu — `/tr/kfif/{id}-{slug}` rotası kullanılmamalı

Rota 1'den çıkan sayısal id ile denendi: `https://kap.org.tr/tr/kfif/1107-turk-hava-yollari-a-o`
→ 200, en güncel dönemi (2026/6 Aylık) gösteriyor ve ayrıştırıcı **çalışıyor**
(imza aynı, 55 kalem, self-check GEÇTİ). Cazip görünüyor: şirket başına
**tek istek**, bildirim sorgusuna hiç gerek yok.

**Ama iki şeyi kaybediyor.** Aynı dönem `/tr/Bildirim/1643241` ile de çekilip
karşılaştırıldı:

| | `/tr/kfif/…` | `/tr/Bildirim/1643241` |
|---|---|---|
| gönderim_ts | **None** | 2026-08-05 08:01:05 |
| dolu beyan | **10/13** | 13/13 |
| okunamayan | **b4_5, b4_6, b4_7** | — |
| oranlar | 5,84 / 18,72 / 8,65 | aynı |
| self-check | GEÇTİ | GEÇTİ |

Aynı dönem olduğu için bu bir şablon değişikliği değil: `/tr/kfif/` sayfası
4A tablosunun son üç satırını render etmiyor.

**İki ayrı gerekçeyle eleniyor:**

1. **Zaman damgası yok.** Look-ahead disiplini (Spec §5.1) uygunluk etiketinin
   geçerlilik anını KAP gönderim zaman damgasına bağlıyor. Bu sayfada o alan
   yok → tarihsel panel üretilemez.
2. **Üç beyan okunamıyor.** Değiştirilemez kural 2 gereği bunlar `None` kalır ve
   karar `BELIRSIZ` olur. Yani bu rotadan üretilen her karar belirsiz çıkar.

İkincisi daha sinsi: oranlar tuttuğu ve self-check geçtiği için sayfa
"çalışıyor" gibi görünüyor. Self-check tutarların doğruluğunu kapılıyor,
**beyanların eksiksizliğini değil.**

---

## 7. playwright gerekiyor mu — **HAYIR**

Her üç rotada da ihtiyaç duyulan veri `requests` ile gelen ilk gövdede mevcut:

- **Rota 1:** 837 satırlık gerçek tablo + gömülü RSC JSON (746 kayıt). Görünür
  metin oranı %5,2 düşük görünüyor ama bu, sayfanın büyük bir JSON yükü
  taşımasından; iskelet olduğundan değil.
- **Rota 2:** 98 kayıt sunucuda render edilmiş; `<thead>`/`<tbody>` dolu.
- **Rota 3:** ayrıştırıcı canlı gövdede diskteki fixture ile birebir aynı
  sonucu üretti.

Sayfalar Next.js olsa da veri **sunucu tarafında** basılıyor. Tarayıcı
otomasyonu ne ek veri getirir ne de gereklidir; getireceği tek şey kırılganlık
ve istek başına maliyettir.

**Bu kararın ömrü:** ölçüm 2026-08-05 tarihli tek bir turda alındı. KAP
istemci-taraflı render'a geçerse rota 2 sessizce boşalır — bu yüzden Faz 1
ayıklayıcısı "0 kayıt" durumunu **başarı değil hata** saymalı.

---

## 8. İstek bütçesi tahmini

Ölçülen gerçek istek maliyeti: `min_aralik` 2,0 + jitter ort. 0,5 + yanıt ort.
0,7 ≈ **3,2 sn/istek**.

**Faz 1 — tam evren, yalnız en güncel KAFİF:**

| Adım | İstek |
|---|---|
| Evren (rota 1) | 1 |
| Bildirim sorgusu, `disclosureClass=DG`, şirket başına | 746 |
| En güncel KAFİF formu, şirket başına (muaflar hariç, üst sınır) | ≤ 746 |
| **Toplam** | **≈ 1.500** |

→ 1.500 × 3,2 sn ≈ **1 saat 20 dakika**

**Faz 1 — 1 yıllık pencerede ne varsa (şirket başına ~2-3 KAFİF):**

| Adım | İstek |
|---|---|
| Evren + bildirim sorguları | 747 |
| KAFİF formları (≈746 × 2,5) | ≈ 1.870 |
| **Toplam** | **≈ 2.600** |

→ 2.600 × 3,2 sn ≈ **2 saat 20 dakika**

**Sonraki koşular (idempotent):** formlar önbellekte kalacağı için yalnız 746
sorgu sayfası + o dönemde yeni yayımlanan formlar → **≈ 40 dakika**.

**Önerilen bütçeler** (her biri bilinçli, ayrı ayrı yükseltilecek):

| Plan adımı | `oturum_butcesi` |
|---|---|
| 1.1 evren çekimi | 5 |
| 1.2 bildirim sorguları | 800 |
| 1.3 form çekimi | 2.000 |

Bu turda kullanılan 50'lik bütçe **hiç zorlanmadı** (en yüksek koşu: 5/50) —
yükseltme kararı ölçüme değil, yukarıdaki iş hacmine dayanıyor.

---

## 9. Açık kalan / kararsız noktalar

1. ~~**Pazar bilgisi kaynağı yok.**~~ **ÇÖZÜLDÜ (Faz 1.1 sondası, 3 istek).**
   Şirket özet sayfası `/tr/sirket-bilgileri/ozet/{id}-{slug}` sunucu tarafında
   şunları veriyor: `Sermaye Piyasası Aracının İşlem Gördüğü Pazar`
   (YILDIZ PAZAR / ANA PAZAR), `Şirketin Sektörü` ve **`Dahil Olduğu Endeksler`**
   — sonuncusu BIST KATILIM 30/50/100/TÜM üyeliğini içeriyor, yani Faz 4
   mutabakatının resmî tarafı. Maliyet: tüzel kişi başına 1 istek = **+746**
   (795 değil; çoklu pay kodlu şirketler tek sayfa paylaşıyor) ≈ 40 dk.
   **Henüz çekilmedi** — karar bekliyor.
2. **1 yıldan geriye gidilemiyor.** Üç tarih parametresi de yok sayıldı. Faz 2
   bu haliyle bloke. Denenmemiş yollar: "Detaylı Sorgulama" sayfasının POST
   gövdesi, `disclosureClass` dışındaki filtre adları, BIST'in dönemsel
   değişiklik PDF'leri (Spec §6'da ikincil kaynak olarak zaten geçiyor).
3. **`disclosureClass=DG` varsayımı n=2.** KAFİF'in her şirkette DG sınıfında
   olduğu iki şirkette doğrulandı. Yanlışsa sessizce **kayıp bildirim** üretir —
   Faz 1'de en az bir kez filtresiz sayımla karşılaştırılmalı.
4. **Muafiyet tespiti ölçülmedi.** Muaf şirketin (banka, aracı kurum…) bildirim
   sorgusunda KAFİF satırı hiç çıkmayacak; bunun "muaf" mı "beyan yok" mu
   olduğunu ayırt eden bir sinyal bu turda aranmadı. `/tr/kfif/` sayfasının
   "Bilgi Mevcut Değil" döndürmesi (Spec §0.4, KTLEV) aday bir sinyal ama
   muaf bir şirkette test edilmedi.
5. **`kapMemberType` tek değerli.** 746 kaydın tamamı `IGS`. Ayırt edici bilgi
   taşımıyor; muafiyet sınıflaması buradan çıkmaz.
6. **404 önbelleklenmiyor.** `robots.txt` her koşuda yeniden istendi. Zararsız
   ama Faz 1'de 404'lerin de (negatif kayıt olarak) önbelleklenmesi gerekir,
   yoksa muaf şirketler her koşuda yeniden sorgulanır.

---

## 10. İlk turda düzeltilen iki ölçüm hatası

Rapor edilen sayılar bu iki düzeltmeden **sonraki** ölçümlerdir:

1. **Yanlış uuid.** Betik ilk turda member oid'i diskteki THY bildiriminden,
   "ilk 32-hex dize" diye almıştı (`4028328c9c81f4…`) — o bir bildirim kimliği.
   Sorgu boş döndü ve bu ilk bakışta "JS iskeleti" gibi görünüyordu. Sayfanın
   `<tbody>` içine **sunucu tarafında** "Bildirim bulunamadı" basmış olması
   ayrımı verdi: iskelet değil, boş sonuç. Doğru oid (`4028e4a140f2ed72…`)
   rota 1'den ticker ile çözülüyor.
2. **Yanlış id ayıklama.** Bildirim kimliği `/tr/Bildirim/{id}` linkinde
   sanılmıştı; öyle bir link yok, kimlik checkbox'ın `id` niteliğinde. İlk
   ölçüm "0 kayıt" diyordu, gerçek 98.

İkisi de aynı sınıf hata: **boş sonucu teknik yetersizlik sanmak.** Faz 1
ayıklayıcısında bu ayrımın kodda karşılığı olmalı — "0 kayıt" ile "sayfa
okunamadı" farklı durumlar.
