# BIST Katılım Uygunluk Motoru

KAP'ta yayımlanan Katılım Finans İlkeleri Bilgi Formu (KAFİF) bildirimlerinden
katılım endeksi uygunluk kararı üretir. Kullanım amacı: swing trading sistemine
bağlanacak, look-ahead'sız tarihsel uygunluk paneli.

Detaylar: @BIST_Katilim_Uygunluk_Motoru_Spesifikasyonu_v0.1.md ve @OKUBENI.md

**Dil: tüm çıktılar, yorumlar ve commit mesajları Türkçe.**

## Komutlar

```bash
python3 tests/test_motor.py                              # 22 test, pytest gerektirmez
python3 tests/test_cekici.py                             # 6 test, çekim katmanı (ağa çıkmaz)
python3 -m katilim.cli dogrula veri/ham/DOSYA.html        # ayrıştır + self-check + karar
python3 -m katilim.cli dok veri/ham/DOSYA.html            # tanı: tabloları imzalarıyla dök
python3 -m katilim.cli toplu veri/ham --csv veri/panel/panel.csv
```

## Değiştirilemez kurallar

Bunlar keyfi tercih değil; her biri sessiz veri bozulmasına karşı bir savunma.
Test kırıldığında **kuralı değil kodu düzeltin.**

1. **Self-check her şeyi kapılar.** Alt tablolardan yeniden hesaplanan üç oran,
   formun özet alanlarıyla ±0,01 içinde eşleşmezse kayıt karantinaya alınır.
   `TOLERANS` sabitini testi geçirmek için gevşetmek yasak — sapma varsa ya
   parser bozuk ya şablon değişmiş, ikisi de araştırılmalı.

2. **Eksik beyan ≠ hayır beyanı.** Okunamayan evet/hayır alanı `None` kalır ve
   karar `BELIRSIZ` olur. `None`'ı `False`'a çevirmek en tehlikeli sessiz hata:
   uygunsuz şirketi uygun gösterir.

3. **TOPLAM satırları okunmaz, toplam hesaplanır.** Formun toplam satırını
   parse etmek, formun kendi aritmetiğini doğrulama imkânını yok eder.

4. **Tablolar konuma göre değil içerik imzasına göre tanınır.** 4A tablosu =
   içinde "alkollü içki" geçen tablo. Şablon revizyonlarında satır sayısı
   değişiyor (2024'te 1. bölüm 3 sorudan 2'ye indi), konum bazlı parser kırılır.

5. **Türkçe normalizasyonda `ı` tuzağı.** Noktasız `ı` Unicode'da ayrıştırılamaz;
   sadece NFKD'ye güvenilirse `ortaklarının` → `ortaklar n` olur ve etiket
   eşlemesi **hata vermeden** başarısız olur. `metin._TR_MAP` bunun için var,
   kaldırmayın.

6. **Ham HTML her zaman saklanır** (`veri/ham/`, sha256 ile). Şablon değişince
   geçmişi yeniden ayrıştırmanın tek yolu bu.

   Ek: sha256 **idempotanlık anahtarı değildir.** KAP markup'ı istekten isteğe
   değişiyor; aynı bildirimi iki kez çekmek iki farklı sha üretir (rota keşfi
   §4'te ölçüldü). İdempotanlık `bildirim_id` üzerinden kurulur; sha yalnızca
   diskteki dosyanın bütünlük damgasıdır.

7. **Boş sonuç ≠ okunamayan sayfa.** "0 kayıt döndü" ile "sayfayı ayrıştıramadım"
   ayrı durumlardır ve kodda ayrı temsil edilmeleri gerekir. Rota keşfinde iki
   ölçüm hatası da tam bu karışıklıktan çıktı: sunucunun bastığı "Bildirim
   bulunamadı" JS iskeleti sanıldı, yanlış yerde aranan kimlik "0 kayıt" diye
   raporlandı. Ayıklayıcı, beklediği çıpayı (tablo gövdesi, boş-sonuç metni)
   bulamazsa **hata fırlatır** — sessizce boş liste dönmez.

   Bu, kural 2'nin (eksik beyan ≠ hayır beyanı) toplama katmanındaki karşılığı:
   her ikisinde de eksik veri, temiz veri gibi görünerek geçiyor.

## Doğrulanmamış varsayımlar

Karar motorunda kural olarak kodlu ama **kanıtlanmamış** (spec §2.3):

- **H1:** 4A'daki herhangi bir EVET kesin elemedir. → Tek gözlem: THY 2025.
- **H2:** Kâr payı imtiyazı, tasfiye payı imtiyazıyla aynı ağırlıkta eler.
- **H3:** BIST payda olarak max(ort. PD, toplam varlık) kullanıyor.
- **H4:** Tolerans durumu şirket bazında, kriter bazında değil.

Bunlar ancak **Faz 4** (kararlarımız vs. resmi XKTUM bileşen listeleri) ile
sınanabilir. Faz 4 öncesinde üretilen panel araştırma çıktısıdır, karar dayanağı
değildir. Bir hipotez revize edilirse spec ve kod aynı commit'te güncellenir.

## Test katmanları — karıştırmayın

- **Gerçek veri testleri** (THY 2025/Yıllık fixture): kanıttır. Oran formülleri
  ve karar motoru KAP'ın kendi çıktısına karşı doğrulanmıştır.
- **Sentetik HTML testi**: duman testidir. Parser mekaniğinin çalıştığını
  gösterir, gerçek KAP HTML'inin o yapıda olduğunu **kanıtlamaz**.

Sentetik HTML'i, gerçek HTML'e uydurmak için değiştirmek anlamsızdır — gerçek
doğrulama `dogrula` komutunu gerçek bir dosyayla çalıştırmaktır.

## Sıradaki iş

**Faz planı ve her adımın promptu: @PROJE_PLANI.md.** Adım sırası, çıkış
kriterleri ve otomatikleştirilmeyecek karar noktaları orada. Aşağıdaki özet
onunla çelişirse plan değil bu dosya esastır.

### Nerede kaldık (7 Ağu 2026)

Biten: **Faz 0** · **1.0** rota keşfi · **1.1** evren · **2.0** derinlik keşfi.
Testler: 59 geçiyor (22 motor + 6 çekici + 23 evren + 8 derinlik).

Sıradaki: **1.2 → 1.4a, aralıksız.** Bu ikisinin arasına başka adım
sokulmaz — pencere 1 gün/gün kayıyor.

**Sıra 7 Ağustos'ta değişti; iki kural yer değiştirdi:**

1. **1.4 ikiye bölündü.** 1.4a yalnız indirir ve arşivler (parser'a hiç
   dokunmaz), 1.4b ayrıştırır ve paneli üretir.
2. **20/20 parser kapısı (1.3) artık çekimi değil paneli kapılıyor.**
   Eski gerekçe — "2.600 isteği doğrulanmamış parser'a harcamayalım" —
   yanlıştı: çekim parser'ı kullanmıyor, ayrıştırma arşivden tekrar
   tekrar yapılabiliyor (kural 6). Yanlış parser bedava düzeltilir,
   kaçırılan bildirim düzelmez.

Zaman duyarlı olmayan her şey arşivin arkasına alındı:
**1.2 → 1.4a → 1.3 → 1.4b → 1.1b → 2.0b → 4.0.**

**Faz 2.0 bitti — pencere genişletilemiyor ve KAYIYOR.** Ayrıntı:
@DERINLIK_KESFI_RAPORU.md (betik: `arac/derinlik_kesfi.py`, 22 istek).

- **Derinlik geri doldurulamaz, yalnız birikir.** Tarih, sayfalama ve
  sıralama parametrelerinin hiçbiri işlenmiyor; `startDate/endDate`
  sunucuya *ulaşıyor* (RSC'deki `__PAGE__` searchParams'ta görünüyor) ama
  pencere yine `[bugün − 1 yıl, bugün]` kuruluyor. Faz 2.1 atlandı.
- **1.4 zaman duyarlı ve bu artık ölçülmüş.** Pencere 1 gün/gün kayıyor;
  5→7 Ağustos arasında THY'nin 2025/6 Aylık KAFİF'i (1472632) erişilmez
  oldu. 6 Aylık dalgası ağustos-eylülde yayımlanıyor: geciken her hafta
  o dalgadan bir dilim kalıcı olarak gidiyor.
- **`toplayici.py` tek sabit pencere toplayıcısıdır** — sayfalama döngüsü
  yazmayın; sunucu bulduğu kaydın tamamını tek sayfada basıyor (92=92).
- **1.2 için:** `bildirim_id` checkbox kazımaya gerek yok; RSC yükündeki
  `disclosureBasic` nesnesi `disclosureIndex`, `publishDate`,
  `disclosureClass`, `year`, `period`, `title` alanlarını yapılandırılmış
  veriyor. Checkbox yolu yedek katman olarak kalsın.
- **Arka uç servisi (`kapsitebackend.mkk.com.tr`) — plan 2.0b, 1.4a'DAN
  SONRA.** Ölçülmesi onaylandı (bütçe 10), **kullanılması ayrı karar.**
  1 yıl sınırı formun kendi metnine göre bir *aralık genişliği* sınırı
  ("Seçilen Tarih Aralığı 1 Yıldan Fazla Olamaz"), çapa sınırı değil;
  servis keyfi çapa kabul ederse Faz 2 açılır. Belgelenmemiş bir iç
  servise ön yüzden **daha nazik** davranılır: `min_aralik` düşürülmez,
  yükseltilir. Kimlik doğrulama veya imzalı istek gerekiyorsa durulur.

**Evren 795 pay kodu / 746 tüzel kişi.** `stockCode` virgüllü çoklu kod
taşıyabiliyor (`"ALBRK, ALK"`, 45 tüzel kişide). Bunun iki sonucu var ve
ikisi de aşağı akışı bağlıyor:

1. **Sorgu ekseni uuid, panel ekseni ticker.** Bildirim sorgusu ve form
   çekimi tüzel kişi başına (746); panel satırı pay kodu başına (795).
2. **Karar tüzel kişi düzeyinde, endeks üyeliği pay kodu düzeyinde.** Aynı
   uuid'in bir kodu XKTUM'da olup diğeri olmayabilir (likidite ve fiili
   dolaşım şartları kod bazında). Mutabakatta bu **sahte uyuşmazlıktır** ve
   H1–H4'ün reddi sayılmaz — ayrı sınıflandırın.

**Faz 0 bitti — parser gerçek KAP HTML'inde doğrulandı.**
`veri/ham/THYAO_2025_yillik.html` üzerinde `dogrula`: `SELF-CHECK: GEÇTİ`
(üç oranda da fark 0,00) + `KARAR: UYGUN_DEGIL [G4_DOGRUDAN_AYKIRI]`.
Tespit edilen şablon imzası: `4A|4B|4C|4D|4E|5F|5G|5H|6I|6J|OZET|S1|S2|S3`.
Yani `TABLO_IMZALARI` / `BEYAN_IMZALARI` haritaları gerçek şablona uyuyor —
artık sentetik HTML'e değil, bu dosyaya karşı regresyon bakılır.

**Faz 1.0 bitti — rotalar ölçüldü.** Ayrıntı: @ROTA_KESFI_RAPORU.md
(betik: `arac/rota_kesfi.py`, 16 istek, bütçe 50'nin en fazla 5'i kullanıldı).

Karara bağlananlar:

- **`requests` yeter, `playwright` gerekmez.** Sayfalar Next.js ama veri
  sunucu tarafında basılıyor.
- **Evren tek istekte geliyor:** `/tr/bist-sirketler` → 746 tüzel kişi (= 795
  pay kodu, yukarı bakın), gömülü RSC yükünde yapılandırılmış JSON
  (`stockCode`, `kapMemberTitle`, `mkkMemberOid`). DOM kazımaya gerek yok.
- **Spec §1.1'in "iki ayrı kimlik" sorunu yok.** `mkkMemberOid` RSC yükünde,
  `{sayısal_id}-{slug}` aynı satırın href'inde. Ayrı bir eşleme adımı gerekmez.
- **`bildirim_id`, satırın checkbox `id` niteliğinde** — `/tr/Bildirim/{id}`
  linki yok. `disclosureClass=DG` gerçek bir filtre: 98 → 12 kayıt, KAFİF
  satırlarının hepsi korunuyor (n=2, doğrulanmalı).

Üç şey Faz 1'in şeklini değiştirdi:

1. **`/tr/kfif/{id}-{slug}` rotası yasak.** Şirket başına tek istek olduğu için
   cazip ve self-check geçiyor; ama gönderim zaman damgası yok (look-ahead
   disiplini çöker) ve 4A'nın son üç satırını render etmiyor → `b4_5/6/7` hep
   `None` → her karar `BELIRSIZ`. Oranlar tuttuğu için "çalışıyor" görünmesi
   tam da tehlikeli olan yanı: self-check tutarları kapılıyor, beyanların
   eksiksizliğini değil.

2. **Sorgu penceresi 1 yıl ve kayıyor.** `fromDate/toDate`, `year`,
   `startDate/endDate` üçü de yok sayıldı. İki şirkette de en eski kayıt günü
   gününe bir yıl öncesi. Sonuç: **çekilmeyen her gün kalıcı kayıp**;
   `veri/ham/` bir önbellek değil, telafisi olmayan arşivin kendisi. Asla
   temizlenmez. Faz 2 için ayrı bir keşif adımı açıldı (plan 2.0).

3. **Pazar bilgisi bu rotada yok** (şehir ve denetim firması var). XKTUM'un ön
   şartı olduğu için (spec §0.4) ikinci kaynak gerekiyor — henüz bulunmadı.

**Bütçe hâlâ karar noktasıdır.** Ölçülen maliyet ~3,2 sn/istek. Onaylanmış
bütçeler: 1.1 → 5, 1.1b → 800, 1.2 → 800, 1.3 → 30, 2.0 → 30 (bitti, 22
kullanıldı), 1.4 → 2.600. Bunlar plan adımı başına ayrı ayrı verilir;
`BütçeAşıldı` bir arıza değil, sorulacak bir sorudur — kodun içinden otomatik
büyütmeyin.

1.4 tahmini 2.0 sonrası aşağı çekildi: pencerede şirket başına ~3 değil **~2**
KAFİF görünüyor (THY'de 3'tü, biri düştü) → 746 sorgu + ~1.500 form ≈ **2.250**,
onaylanmış 2.600'ün altında.
