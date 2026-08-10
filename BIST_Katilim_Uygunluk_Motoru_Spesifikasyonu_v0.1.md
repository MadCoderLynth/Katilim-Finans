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

**Muafiyet listesi (KAFİF doldurmayan):** aracı kurumlar, bankalar, emeklilik şirketleri, finansal kiralama ve faktoring şirketleri, menkul kıymet yatırım ortaklıkları, sigorta şirketleri, varlık yönetim şirketleri, **tasarruf finansman şirketleri**. Holding ve GSYO **dahil** — onlar dolduruyor.

> ### ⚠ MUAF ≠ ELENMİŞ — modelleme boşluğu (1.1b ölçümü, 8 Ağu 2026)
>
> Bu belge örtük olarak "KAFİF vermeyen şirket endeks dışıdır" varsayıyordu. **Yanlışlandı.** XKTUM'un 243 üyesinin 11'i panelimizde hiç yok:
>
> | Ticker | Bizdeki durum | Not |
> |---|---|---|
> | ALBRK, ALK | `KAPSAM_DISI` (banka) | Albaraka — **katılım bankası** |
> | KTLEV | `AYIRT_EDILEMEDI` | Katılımevim — **katılım esaslı tasarruf finansman**; KATILIM 30/50/100/TÜM/TEMETTÜ'nün hepsinde |
> | AAGYO, BETAE, GENKM, GOLDA, LXGYO, MCARD, SOHOE, SSAAT | `BEYAN_YOK` | 8'inin de bildirim sorgusunda **0 KAFİF kaydı**; hepsi doldurması gereken kategoride |
>
> **İlk üç grup çözüldü:** katılım esaslı finans kuruluşları KAFİF doldurmuyor ama endekste. Muafiyet, uygunsuzluk değil kapsam dışılıktır ve endeks uygunluğunu **engellemez**. KTLEV bu gerekçeyle `MUAF` işaretlenir (`BEYAN_YOK` değil — o okuma üyelikle çelişiyor). Tasarruf finansman yukarıdaki listeye eklendi.
>
> **Son sekiz ÇÖZÜLDÜ (4.0 ölçümü, 10 Ağu 2026) — ve üç okumanın hiçbiri değil.**
>
> `/tr/kfif/{id}-{slug}` ikili sondası (8 istek): **8/8 DOLU FORM.** Yani (c) "kural boşluğu" yanlışlandı — bu şirketlerin KAFİF'i var. Ardından üçünde FİLTRESİZ bildirim sorgusu (3 istek): **0 KAFİF.** Bu da (a)'nın iki alt okumasını eledi: DG filtresi suçlu değil, bayatlık da değil.
>
> Geriye **dördüncü bir mekanizma** kalıyor: **KAFİF formu var ama ona karşılık gelen BİLDİRİM yok.** Form yalnız şirketin kfif sayfasında yayımlanmış, bildirim akışına hiç düşmemiş. Destekleyen kanıt: sekizinin de bildirim geçmişi tamamen halka arz evrakı (İzahname, Fiyat Tespit Raporu, Tasarruf Sahiplerine Satış Duyurusu) ve 5'inin slug kimliği evrenin %98–99 diliminde — hepsi **yeni halka açılmış** şirketler.
>
> **Bu bir KAPSAM SINIRIDIR, hipotez hatası değil.** Bildirim tabanlı toplama (1.2 → 1.4a) bu şirketleri yapısal olarak göremiyor; tek alternatif rota (`/tr/kfif/`) zaman damgası vermediği ve 3 beyanı render etmediği için tarihsel panele giremez.
>
> **KARAR (10 Ağu 2026): kapsam sınırı kabul edildi — §3.4 seçenek (a).** Üç kademeli gerekçe:
> 1. **Tarihsel panel için kayıp yok.** Yeni halka açılan şirketin geçmişi yoktur; backtest'e katkısı zaten olamazdı.
> 2. **Boşluk geçici ve kendi kendine kapanıyor.** İlk dönemsel KAFİF bildirim akışına düştüğünde 1.2 onları kendiliğinden toplar (~6 ay).
> 3. **Güncel üyelik sorusu panelin işi değil.** "Bugün XKTUM'da kim var" `veri/evren/endeks_uyeligi.csv`'den, KAP'ın kendi ağzından cevaplanıyor. Panelin kattığı değer tarihsel etiket ve değişim tespitidir.
>
> Seçenek (b) reddedildi: kfif rotasından üretilecek kayıtta 3 beyan `None` kalıp karar `BELIRSIZ` çıkacaktı — olmayan bilgiyi olan bilgi gibi göstermek, kural 2'nin ihlali.
>
> **Durum kodu düzeltilir.** Bu 8 için `BEYAN_YOK` olgusal olarak YANLIŞTIR: beyan var, bildirim yok. Ayrı kod alırlar (`FORM_VAR_BILDIRIM_YOK`) ki (i) "vermesi gerekirdi, vermedi" diye okunmasınlar, (ii) dönemsel beyanları geldiğinde panele geçişleri izlenebilsin. Bu bir izleme listesidir, kalıcı bir sınıf değil.

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
periyot             TEXT          -- '6 Aylık' | 'Yıllık' | '3 Aylık' | '9 Aylık'
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
> **`periyot` alanı ölçümle genişletildi (Faz 1.2, 07.08.2026).** İlk yazımda
> `'6 Aylık' | 'Yıllık'` deniyordu; 1.280 bildirimlik taramada `9 Aylık` (7)
> ve `3 Aylık` (5) da gözlendi. Sebep özel hesap dönemleri — futbol kulüpleri
> (FENER, GSRAY, BJKAS, TSPOR) 31 Mayıs kapanışı yüzünden "2024/Yıllık"
> formunu Ağustos 2025'te veriyor.
>
> **Sonuç: panel kronolojisi dönem etiketine göre sıralanamaz.** Tolerans
> durum makinesi (§2.1) dönemleri sırayla taşıdığı için sıralama
> `gonderim_ts` üzerinden yapılmalı. Ayrıntı: `BILDIRIM_GECMISI_RAPORU.md` §4.

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

**Zincir dönem bazında yürür, bildirim bazında değil.** Aynı dönemin düzeltilmiş bildirimi yeni bir değerleme dönemi değildir. Look-ahead korunarak: P(n) değerlendirilirken "önceki dönem durumu", P(n−1)'in **P(n)'in gönderim anında yayımlanmış en son** kaydından gelir.

**KARAR — zincir boşluğunda durum TAŞINIR (10 Ağu 2026).** Şirketin kendi serisinde >280 gün (≈1,5 kadans; ölçülen ardışık aralık medyanı 185, en uzunu 259) sessizlik varsa tolerans durumu sıfırlanmaz, taşınır ve satır `ZINCIR_BOSLUGU` ile işaretlenir. Üç gerekçe:

1. **Hata maliyeti asimetrisi.** Taşıyıp yanılmak gereksiz eleme (kaçırılan fırsat, ucuz); sıfırlayıp yanılmak aşımı olan şirketi temiz göstermek (yanlış pozitif, pahalı).
2. **`BELIRSIZ` davranışıyla tutarlı.** Veri eksikliği toleransı zaten sıfırlamıyor.
3. **Belirleyici olan:** boşluklarımız çoğu zaman şirketin sessizliği değil **bizim körlüğümüz** — kayan sorgu penceresi ve §0.4'teki "form var, bildirim yok" vakası. Sıfırlamak, bir toplama boşluğunun bir şirketin sicilini sessizce temizlemesine izin vermek olurdu; kural 2'nin ihlali.

`ZINCIR_BOSLUGU` yalnız etiket değil **tetikleyicidir**: o şirketin bildirim geçmişi yeniden sorgulanır, kimlik bu arada görünür olmuş olabilir.

> Kritik: ikinci dönemde tolerans sıfırlanıyor. Üç kriterden **herhangi birinde** aşım varsa yeterli — aynı kriter olmak zorunda değil. Bu yüzden durum makinesi kriter bazında değil, şirket bazında tutulur.

### 2.2 Belirsiz bant
Varlık/borç oranı %33–%36,3 arasındaysa ve BIST'in PD tabanlı hesabı devreye giriyorsa, karar `BELIRSIZ` işaretlenip ortalama PD ile ikinci hesap yapılır. Bu kural §0.2'ye dayanıyor ve Faz 4 mutabakatında test edilecek.

### 2.3 Test edilecek hipotezler
Aşağıdakiler kural olarak kodlanacak ama **doğrulanmamış** kabul edilecek, Faz 4'te resmi XKTUM listesiyle sınanacak:

- **H1:** 4A'daki herhangi bir EVET kesin elemedir (THY vakası destekliyor, n=1).
- **H2:** Kâr payı imtiyazı, tasfiye payı imtiyazı ile aynı ağırlıkta eleme sebebidir.
- **H3:** BIST payda olarak gerçekten max(PD, TV) kullanıyor.
- **H4:** Tolerans durumu şirket bazında, kriter bazında değil. → **4.0'ın "DCTTR'de yeni uyuşmazlık açılıyor" bulgusu GEÇERSİZ (3.1 sonrası inceleme, 10 Ağu).** DCTTR'nin elenmesi zincirden değil, düzeltmelerin çözülmemiş olmasından kaynaklanıyordu: zincir bildirim bazında yürüyor ve *aynı dönemin* önceki düzeltmesini "önceki dönem" sanıyor. Zincirin çevirdiği 5 satırın 4'ü (ALVES, DCTTR, DOGUB, KONTR) bu artefakt; yalnız KLMSN gerçek bir dönemler arası etki. H4 hâlâ onaylanmış değil (n=1) ama karşı kanıtı kalmadı.

> **ZİNCİR DÖNEM BAZINDA YÜRÜR, BİLDİRİM BAZINDA DEĞİL.** Md. 3.5 ardışık *değerleme dönemlerini* düzenliyor; aynı dönemin düzeltilmiş bir bildirimi yeni bir dönem değildir. Panelde bu kalıptan 15 satır var (`onceki_donem_tolerans=EVET` iken "önceki" aynı dönemin eski kaydı).
>
> Doğru semantik, look-ahead korunarak: P(n) değerlendirilirken "önceki dönem durumu", P(n−1)'in **P(n)'in gönderim anında geçerli olan** kaydından gelir. Panel satırı her bildirim için ayrı kalır (o kayıt kendi penceresinde canlı etiketti) ama **zinciri ilerletmez.** Bu yüzden 2.3 (düzeltme çözümü) 3.1'in ön koşuludur; sıra ters işletildi, panel 2.3 sonrası yeniden üretilecek.
- **H6 (aday, KODLANMADI):** Endeksten çıkan şirketin geri girişi gecikmeli — bir dönem temiz olmak yetmiyor. → PEKGY: 6 aylık formda borç %36,73 (bant üstü), yıllıkta %20,88 (temiz), ama 01.05.2026 revizyonunda geri girmemiş. Alternatif açıklama H3 (payda). Standart md. 3.5 tolerans için asimetrik bir bekleme tanımlıyor; girişte de simetrik bir hüküm olup olmadığı **TKBB metninden doğrulanmalı** — kodlamadan önce kaynağa bakılacak.
- **H5:** BIST, formun **özet alanındaki** oranı kullanıyor; alt kalemlerden yeniden hesaplanan oranı değil. (Faz 1.3 ölçümü: 1.276 formun 19'unda formun kendi 4E TOPLAM satırı kendi kalemleriyle tutmuyor, ikisi farklı oran üretiyor. Standart beyan esaslı işlediği için BIST'in beyan edilen özeti kullanması muhtemel — ama doğrulanmadı.)

**H5 şu anki veriyle SINANAMIYOR (1.4b ölçümü, 8 Ağu 2026).** Sıkılaşan üç kademe:

1. 1.276 formun 22'sinde iki oran ayrışıyor; 3'ünde kalem oranı tanımsız (4E=0) → ayırt edici aday **19**.
2. Bu 19'un yalnız **1'inde** iki oran farklı *karar* üretiyor: PNLSN 2025/6 Aylık (özet 5,30 % → TOLERANSTA, kalem 4,67 % → UYGUN).
3. O tek kayıt da **geçersiz kılınmış bir düzeltmedir.** PNLSN aynı dönemi üç kez vermiş (08.08 → 13.08 → 04.09.2025); §3.2 gereği geçerli olan en geç kayıt ve onda iki oran aynı kararı veriyor. Düzeltmeler çözüldükten sonra ayırt edici örneklem **n=0**.

Sonuç: H5 kanıtla desteklenmiş değil, **yanlışlanamamış bir yargı çağrısıdır.** Faz 4 onu sınayamaz; panel derinleştikçe (her yeni KAFİF dalgası) yeni ayırt edici kayıt birikmesi beklenir. O zamana kadar varsayılan gerekçesi ampirik değil, aşağıdaki maliyet argümanıdır.

*Kayıt için:* geçersiz kılınmış kayıt 08–13 Ağustos 2025 arasında beş gün boyunca kamuya açık olan durumdu. Endeks revizyonları 1 Mayıs / 1 Ekim'de yürürlüğe girdiği için bu pencere hiçbir revizyonla kesişmiyor — yani teorik olarak bile gözlemlenebilir bir sonuç doğurmuyor.

**Varsayılan seçim ve gerekçesi.** Karar sütunu **özet alanından** üretilir (H5 kabul edilmiş gibi), kalem bazlı oran ikinci sütunda taşınır. Gerekçe aritmetik değil hata maliyeti asimetrisi: BIST özeti kullanıyorsa ve biz kalemi kullanırsak PNLSN gibi vakalarda "UYGUN" deriz, BIST elemiştir → **yanlış pozitif**, uygunsuz hisseyi uygun göstermek. Tersi durumda gereksiz eleme yaparız → kaçırılan fırsat, ucuz olan hata.

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

> ### ⚠ REVİZYON TAKVİMİ DÜZENLİ DEĞİL — VARSAYMAYIN, OKUYUN (4.1 ölçümü, 10 Ağu 2026)
>
> Aşağıdaki "1 Mayıs / 1 Ekim" tarifi **yanlışlandı.** Borsa İstanbul'un kendi dönemsel değişiklik PDF'lerinin başlıkları:
>
> ```
> 01.07.2024 ─5 ay─▶ 01.12.2024 ─5 ay─▶ 01.05.2025 ─5 ay─▶ 01.10.2025 ─7 AY─▶ 01.05.2026
> ```
>
> 2024'te takvim **Temmuz/Aralık**tı; Mayıs/Ekim ritmi 01.05.2025'te başlıyor ve 01.10.2025–30.04.2026 **7 ay** sürüyor. Takvim `veri/referans/xktum_bilesenler.csv`'nin `donem_baslangic`/`donem_bitis` sütunlarından **okunur**, ay sabitinden türetilmez. `katilim/mutabakat.py`'deki `REVIZYON_AYLARI = (5, 10)` bugünkü nokta-zaman ölçümü için doğru sonuç veriyor ama tarihsel mutabakatta yanlış — 4.2 düzeltecek.
>
> **Ayrıca: gerçek veri kesim noktası yürürlük tarihi değil DUYURU tarihidir.** BIST listeyi yürürlükten **4–7 gün önce** duyuruyor (ölçüldü, n=5; 01.05.2026 için 27.04.2026 duyuru sayfasından bağımsız doğrulandı). Duyurudan sonra yayımlanan KAFİF o revizyonu etkileyemez.
>
> **Ölçülmüş dönem eşlemesi:** 6 Aylık dalgası → o yılın Ekim revizyonu; Yıllık dalgası → ertesi yılın Mayıs revizyonu. Medyan öncüllük 6–8 hafta. Ayrıntı ve sayım: `XKTUM_REFERANS_RAPORU.md` §5.

KAFİF, finansal tablolar ilan edildikten en geç 1 işlem günü sonra yayımlanmak zorunda. Endeks revizyonu ise dönem başında (yukarıdaki uyarıya bakın — güncel ritim 1 Mayıs / 1 Ekim, ama takvim tarihsel olarak kaymış) yürürlüğe giriyor. Arada haftalarca süren bir pencere var:

```
KAFİF yayını  ──────► [bilgi kamuya açık, endeks henüz değişmedi] ──────►  endeks yürürlük
                                    ~4-8 hafta
```

Bu pencerede uygunluk kaybı hesaplanabiliyor ama katılım fonlarının zorunlu satışı henüz gerçekleşmemiş oluyor.

> ### ⚠ PENCERE YUKARIDAKİ ŞEMADAN DAR — iki ölçüm onu kırpıyor
>
> Yukarıdaki 4-8 hafta **ham** penceredir. İki ölçüm onu iki ucundan kesiyor:
>
> - **Baştan: düzeltme penceresi** (2.3, n=181) — medyan 21 gün, p95 **38 gün**, max 55. Karar çeviren 14 düzeltmenin hepsi ≤31 gün. Bu süre geçmeden KAFİF'in gösterdiği aşım güvenilir değil; DOGUB 2025/6 Aylık'ı %8,09 ile verip beş hafta sonra %0,92'ye düzeltti.
> - **Sondan: duyuru tarihi** (4.1, n=5) — endeks kararı yürürlükten değil **duyurudan** itibaren kamuya mal olur, o da yürürlükten 4-7 gün önce.
>
> ```
> KAFİF        +21g (medyan)   +38g (p95)              duyuru      yürürlük
>   │             │               │                      │            │
>   ▼             ▼               ▼                      ▼            ▼
>   ├─ düzeltme riski ───────────┤                       │            │
>   │                            ├── BİLGİ AVANTAJI ─────┤            │
>   │                                                    ├─ herkes ───┤
>   └──────────────── ham pencere (4-8 hafta) ────────────────────────┘
> ```
>
> Somut hesap: DOGUB 2026/6 Aylık 30.07.2026'da yayımlandı; 01.10.2026 yürürlüğü ~25.09'da duyurulacak → karar penceresi 57 gün. p95 düzeltme penceresi çıkınca **~19 gün** kalıyor.
>
> **Sonuç: bilgi avantajı penceresi 2-3 hafta, 4-8 hafta değil.** Hız/kesinlik ödünleşmesi bu yüzden gerçek bir ödünleşme: medyanda (21 gün) işlem etmek pencereyi genişletir ama düzeltme riskini üstlenir. Faz 5.2 iki rejimi ayrı ölçecek; etkinin varlığı değil, bu dar pencerede işlem maliyetini aşacak kadar büyük olup olmadığı sorusu belirleyici.

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
