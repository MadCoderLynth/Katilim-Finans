# BIST Katılım Uygunluk Motoru — Spesifikasyon v0.1

**Amaç:** KAP'ta yayımlanan Katılım Finans İlkeleri Bilgi Formu (KAFİF) bildirimlerinden, makine okunabilir ve **tarihsel** bir katılım uygunluk paneli üretmek. Çıktı hem anlık tarama tablosu hem de backtest için look-ahead'sız etiket serisi olarak kullanılabilir olacak.

**Durum:** Pre-development. Kaynak şeması THY 2025/Yıllık bildirimi (KAP Bildirim 1566002) üzerinden doğrulandı.

---

## 0. Kaynak Doğrulaması

### 0.1 Formül teyidi

THY 2025/Yıllık bildirimindeki özet alanlar, alt tablolardan yeniden hesaplandığında birebir tutuyor (tutarlar milyon TL):

| Oran | Formül | Hesap | Özet alanı |
|---|---|---|---|
| Uygun olmayan gelir | (4B + 4C − 4D) / 4E | (0 + 113.103 − 60.498) / 1.068.575 | **4,92 %** ✔ |
| Uygun olmayan varlık | (5F − 5G) / 5H | (426.982 − 67.069) / 1.996.745 | **18,02 %** ✔ |
| Uygun olmayan borç | (6I − 6J) / 5H | (783.575 − 638.976) / 1.996.745 | **7,24 %** ✔ |

**Sonuç:** Parser için yerleşik bir doğrulama testimiz var. Her bildirimde yeniden hesaplanan üç oran, özet alanlarıyla ±0,01 içinde eşleşmeli. Eşleşmiyorsa parse hatası veya şablon versiyon farkı vardır — kayıt karantinaya alınır.

### 0.2 Payda meselesi

KAFİF her üç oranda da paydayı **toplam varlıklar (5H)** olarak kullanıyor. BIST'in uygulama rehberinde payda `max(ortalama piyasa değeri, toplam varlıklar)` olarak tarif ediliyor. Daha büyük payda daha küçük oran ürettiği için:

> KAFİF oranı ≥ BIST oranı

Yani **KAFİF oranı %33'ün altındaysa BIST kriteri de kesin sağlanır** (yeterli koşul). KAFİF oranı %33–%36,3 bandındaysa BIST'in PD tabanlı hesabı hisseyi kurtarabilir; bu bantta karar "belirsiz" olarak işaretlenir ve PD verisiyle ikinci bir hesap yapılır.

### 0.3 THY vakası — look-through'un ampirik kanıtı

THY üç finansal oranı da rahat geçiyor. Buna rağmen endeks dışında, çünkü:

```
4A/1  Alkollü içki/gıda üretim ve ticareti (kendisi, tüzel kişi ortakları VEYA iştirakleri) → EVET
```

Rehber madde 3.1'in başlığı zaten *"Şirketi Doğrudan Katılım Finansı İlkelerine Aykırı Hale Getiren Faaliyetler"*. Yani 4A'daki herhangi bir EVET, oranlardan bağımsız kesin elemedir.

**Not:** THY'nin gelir oranı %4,92 — %5 limitine 0,08 puan mesafede. 4A sorunu çözülse bile hisse gelir testinde kılpayı duruyor. Bu, izleme listesinde ayrı bir uyarı seviyesi gerektiriyor.

### 0.4 Kaynağın kapsamı ve sınırları

**KAFİF'ten gelen:** 13 evet/hayır beyanı (look-through dahil), 3 hesaplanmış oran, ~45 kalem düzeyinde tutar, dönem/nitelik/para birimi meta verisi, KAP gönderim zaman damgası.

**KAFİF'ten gelmeyen, ikinci kaynak gerektiren:**

| Eksik | Kaynak | Neden gerekli |
|---|---|---|
| Pazar bilgisi (Yıldız/Ana/Alt) | KAP BIST şirket listesi | XKTUM uygunluğunun ön şartı |
| Ortalama piyasa değeri | Fiyat + sermaye verisi | §0.2'deki belirsiz bant için |
| Önceki dönem tolerans durumu | Kendi panelimiz | Durum makinesi girdisi |
| Mali sektör muafiyeti | Sektör sınıflaması | Muaf şirket "eksik veri" değil, "kapsam dışı" |
| Likidite / halka açık PD sıralaması | BIST verisi | XK30/50/100 alt endeksleri için |

**Muafiyet listesi (KAFİF doldurmayan):** aracı kurumlar, bankalar, emeklilik şirketleri, finansal kiralama ve faktoring şirketleri, menkul kıymet yatırım ortaklıkları, sigorta şirketleri, varlık yönetim şirketleri. Holding ve GSYO **dahil** — onlar dolduruyor. (Doğrulandı: KTLEV bir tasarruf finansman şirketi ve KAFİF sayfası "Bilgi Mevcut Değil" dönüyor.)

---

## 1. Veri Modeli

### 1.1 `sirket`
```
ticker              TEXT PK
unvan               TEXT
kap_member_uuid     TEXT      -- örn. 4028e4a140f2ed720140f376bebb01a7
kap_kfif_slug       TEXT      -- örn. 5763-katilimevim-tasarruf-finansman-a-s
pazar               TEXT
sektor              TEXT
mali_sektor_muaf    BOOLEAN
```
> **Dikkat:** KAP'ta iki ayrı kimlik var. `/tr/kfif/{sayısal_id}-{slug}` ile `/tr/bildirim-sorgu-sonuc?member={uuid}` farklı anahtarlar kullanıyor. İkisinin eşlemesi ayrı bir adım.

### 1.2 `kafif_bildirim` (ham kayıt)
```
bildirim_id         INTEGER PK    -- KAP bildirim no
ticker              TEXT FK
gonderim_ts         TIMESTAMP     -- 04.03.2026 18:57:54 formatı
yil                 INTEGER
periyot             TEXT          -- '6 Aylık' | 'Yıllık'
finansal_tablo_nit  TEXT          -- 'Konsolide' | 'Solo'
para_birimi_carpani INTEGER       -- 1.000.000 TL → 1000000
is_duzeltme         BOOLEAN
sablon_versiyon     TEXT          -- tespit edilen şema imzası
raw_html_sha256     TEXT
```

### 1.3 `kafif_beyan` (13 bayrak, hepsi BOOLEAN)
```
bildirim_id FK
b1_1  esas_sozlesme_12_faaliyet
b1_2  esas_sozlesme_12_ortaklik
b2_1  imtiyaz_kar_payi
b2_2  imtiyaz_tasfiye_payi
b3_1  md15_kamuoyu_aciklamasi
b3_2  md15_mahkeme_karari
b4_1  alkol
b4_2  domuz
b4_3  tutun_uretim_toptan
b4_4  kumar
b4_5  finans_sektoru_gayri_katilim
b4_6  yayincilik
b4_7  otel_turizm_eglence
```
Her bayrağın yanına, formda varsa `ilgili_esas_sozlesme_maddesi` metin alanı taşınır.

### 1.4 `kafif_kalem` (uzun format)
```
bildirim_id, tablo, kalem_no, kalem_adi, tutar_ham, tutar_tl
tablo ∈ {4B, 4C, 4D, 4E, 5F, 5G, 5H, 6I, 6J}
```
Serbest metin açıklamalar (4D/16, 5G/7, 6J/4) ayrı `kafif_aciklama` tablosuna. Bunlar denetim izi olarak değerli — THY örneğinde 5G/7'nin katılım bankalarındaki vadeli mevduatı içerdiği buradan anlaşılıyor.

### 1.5 `uygunluk_karar` (türetilmiş)
```
ticker, yil, periyot
gecerlilik_baslangic  TIMESTAMP  -- = gonderim_ts
karar                 TEXT       -- UYGUN | TOLERANSTA | UYGUN_DEGIL | KAPSAM_DISI | BELIRSIZ
red_kodlari           TEXT[]     -- örn. ['G4_ALKOL']
gelir_orani, varlik_orani, borc_orani   NUMERIC
onceki_donem_tolerans BOOLEAN
```

---

## 2. Karar Motoru

Kapılar sırayla, ilk eşleşmede durur:

| Kapı | Koşul | Sonuç |
|---|---|---|
| **G0** | `mali_sektor_muaf` | KAPSAM_DISI |
| **G1** | `b1_1` veya `b1_2` = EVET | UYGUN_DEGIL — esas sözleşme |
| **G2** | `b2_1` veya `b2_2` = EVET | UYGUN_DEGIL — imtiyaz (Standart md. 1.8) |
| **G3** | `b3_1` veya `b3_2` = EVET | UYGUN_DEGIL — madde 1.5 |
| **G4** | `b4_*` içinde herhangi biri EVET | UYGUN_DEGIL — doğrudan aykırı faaliyet |
| **G5** | gelir oranı > %5 | tolerans kontrolü (§2.1) |
| **G6** | varlık oranı > %33 | tolerans kontrolü |
| **G7** | borç oranı > %33 | tolerans kontrolü |
| — | hiçbiri | UYGUN |

### 2.1 Tolerans durum makinesi

```
aşım_yok                          → UYGUN
aşım var, ≤ limitin %10'u fazlası,
  ve önceki dönem TOLERANSTA değil → TOLERANSTA
aşım var, > limitin %10'u fazlası → UYGUN_DEGIL
aşım var (herhangi bir miktarda),
  ve önceki dönem TOLERANSTA      → UYGUN_DEGIL
```

Bant sınırları: gelir %5 → **%5,5** | varlık ve borç %33 → **%36,3**

> Kritik: ikinci dönemde tolerans sıfırlanıyor. Üç kriterden **herhangi birinde** aşım varsa yeterli — aynı kriter olmak zorunda değil. Bu yüzden durum makinesi kriter bazında değil, şirket bazında tutulur.

### 2.2 Belirsiz bant
Varlık/borç oranı %33–%36,3 arasındaysa ve BIST'in PD tabanlı hesabı devreye giriyorsa, karar `BELIRSIZ` işaretlenip ortalama PD ile ikinci hesap yapılır. Bu kural §0.2'ye dayanıyor ve Faz 4 mutabakatında test edilecek.

### 2.3 Test edilecek hipotezler
Aşağıdakiler kural olarak kodlanacak ama **doğrulanmamış** kabul edilecek, Faz 4'te resmi XKTUM listesiyle sınanacak:

- **H1:** 4A'daki herhangi bir EVET kesin elemedir (THY vakası destekliyor, n=1).
- **H2:** Kâr payı imtiyazı, tasfiye payı imtiyazı ile aynı ağırlıkta eleme sebebidir.
- **H3:** BIST payda olarak gerçekten max(PD, TV) kullanıyor.
- **H4:** Tolerans durumu şirket bazında, kriter bazında değil.

---

## 3. Toplama Katmanı

### 3.1 Rotalar
| İhtiyaç | Rota | Not |
|---|---|---|
| Evren | `/tr/bist-sirketler` | ticker, unvan, pazar, uuid |
| Son KAFİF | `/tr/kfif/{id}-{slug}` | yalnız en güncel dönem |
| Bildirim geçmişi | `/tr/bildirim-sorgu-sonuc?member={uuid}` | bildirim_id listesi |
| Tekil bildirim | `/tr/Bildirim/{id}` | tam içerik, ek dosya yok |

Ham içerik doğrudan HTML gövdesinde; PDF/ek indirmesi gerekmiyor.

### 3.2 Tasarım kuralları
- **Fetch katmanı pluggable:** önce `requests`, sunucu tarafı render yetersizse `playwright`. Hangisinin gerektiği ilk pilotta ölçülür.
- **Ham HTML her zaman saklanır** (sha256 ile). Şablon değişince geçmişi yeniden parse edebilmek için tek yol bu.
- **İdempotent:** aynı bildirim_id ikinci kez çekilmez.
- **Nazik davran:** istekler arası gecikme, tek thread, User-Agent belirt. KAP'ın resmi public API'si yok; kırılganlık ve kullanım koşulları riski var.
- **Düzeltme mantığı:** aynı (ticker, yıl, periyot) için birden fazla bildirim olabilir. En geç `gonderim_ts` kazanır, ama eskisi silinmez — düzeltme olayının kendisi bir sinyal.

---

## 4. Fazlar

| Faz | İçerik | Çıkış kriteri |
|---|---|---|
| **0** | 20 şirketlik pilot. Parser + formül self-check. | 20/20 bildirimde yeniden hesaplanan oranlar özet alanlarıyla eşleşiyor |
| **1** | Tam evren, son dönem snapshot | Muaf olmayan tüm şirketler için kayıt var veya "beyan yok" olarak işaretli |
| **2** | Tarihsel geri doldurma | KAFİF'in başlangıcından bugüne panel dolu; şablon versiyonları ayrıştırılmış |
| **3** | Karar motoru + tolerans durum makinesi | Her (ticker, dönem) için karar + gerekçe kodu üretiliyor |
| **4** | **Mutabakat** — kararlarımız vs. resmi XKTUM bileşen listeleri | Uyuşmazlık oranı < %5, her uyuşmazlık ya parser hatası ya H1–H4 revizyonu olarak açıklanmış |
| **5** | Momentum sistemine olay akışı | KAFİF gönderim tarihi bir katalizör olayı olarak sisteme bağlanmış |

**Faz 4 pazarlık konusu değil.** Kendi kararlarımızı BIST'in fiilen yaptığı seçimlerle karşılaştırmadan bu motorun doğru olduğunu bilemeyiz. Uyuşmazlıklar hata değil, bilgidir — modellenmemiş bir kriteri ortaya çıkarır.

---

## 5. Backtest ve Sinyal Kullanımı

### 5.1 Look-ahead disiplini
Uygunluk etiketinin geçerli olduğu ilk an = **KAFİF'in KAP gönderim zaman damgası**. Bilanço dönemi değil, endeks yürürlük tarihi değil. Bu alan bildirimde saniye hassasiyetinde mevcut.

### 5.2 Bilgi öncüllüğü
KAFİF, finansal tablolar ilan edildikten en geç 1 işlem günü sonra yayımlanmak zorunda. Endeks revizyonu ise dönem başında (1 Mayıs / 1 Ekim) yürürlüğe giriyor. Arada haftalarca süren bir pencere var:

```
KAFİF yayını  ──────► [bilgi kamuya açık, endeks henüz değişmedi] ──────►  endeks yürürlük
                                    ~4-8 hafta
```

Bu pencerede uygunluk kaybı hesaplanabiliyor ama katılım fonlarının zorunlu satışı henüz gerçekleşmemiş oluyor.

### 5.3 Ölçülecek
- XKTUM'dan çıkan hisselerin, (a) KAFİF yayın tarihi ve (b) endeks yürürlük tarihi etrafındaki getiri dağılımı
- Endekse **giren** hisselerde simetrik etki var mı
- Etkinin hissenin katılım fonu sahipliği yoğunluğuyla ilişkisi
- Bu olayın momentum sinyalleriyle çakıştığında pozisyon boyutuna etkisi

**Beklenti değil hipotez:** çıkış etkisinin var olduğunu varsaymıyoruz, ölçüyoruz. Etki bulunamazsa bu modül sinyal değil yalnızca risk filtresi olarak kalır.

---

## 6. Riskler

| Risk | Etki | Azaltma |
|---|---|---|
| Şablon değişikliği (2024'te oldu) | Parser sessizce yanlış alan okur | Şema imzası + formül self-check; uyuşmazlıkta karantina |
| Beyan esaslı veri | Şirket hatalı/eksik beyan edebilir | Faz 4 mutabakatı; Rehber "gerçeğe aykırı beyan" durumunu ayrıca ele alıyor |
| KAP scraping kırılganlığı | Toplama durur | Ham HTML arşivi; fetch katmanı izole |
| Tarihsel derinlik sınırı | Backtest penceresi kısa | Erken dönemler için BIST'in dönemsel değişiklik PDF'lerini ikincil kaynak yap |
| Madde 1.5 takdire dayalı | Kural motoru yakalayamaz | Manuel override katmanı; beyan alanı zaten formda var, en azından beyan edileni yakalıyoruz |
| İştirak beyanı ikili | Orantısal etki bilinmiyor | Kabul: bu standardın kendi tasarımı, modelleme hatası değil |

---

## 7. Sıradaki Adım

**Faz 0.** Tek bir bildirim HTML'i üzerinde çalışan parser + formül doğrulama testi. Girdi olarak THY 1566002 kullanılacak (beklenen çıktı §0.1'de sabit). Ardından 19 şirketlik pilot kümesiyle genişletme.

Parser'ın yazılacağı ortamda ağ erişimi gerekiyor; kod lokalde çalıştırılmak üzere teslim edilecek.
