# BIST Katılım Uygunluk Motoru

KAP'ta yayımlanan Katılım Finans İlkeleri Bilgi Formu (KAFİF) bildirimlerinden
katılım endeksi uygunluk kararı üretir. Kullanım amacı: swing trading sistemine
bağlanacak, look-ahead'sız tarihsel uygunluk paneli.

Detaylar: @BIST_Katilim_Uygunluk_Motoru_Spesifikasyonu_v0.1.md ve @OKUBENI.md

**Dil: tüm çıktılar, yorumlar ve commit mesajları Türkçe.**

## Komutlar

```bash
python3 tests/test_motor.py                              # 24 test, pytest gerektirmez
python3 tests/test_cekici.py                             # 9 test, çekim katmanı (ağa çıkmaz)
python3 tests/test_pilot.py                              # 9 test, 20 gerçek KAP belgesi (kanıt katmanı)
python3 -m katilim.cli bildirimler --butce 800            # KAFİF kimlikleri (Faz 1.2)
python3 -m katilim.cli indir --butce 2600                 # formları arşivle (Faz 1.4a)
python3 -m katilim.cli panel                              # snapshot paneli (Faz 1.4b)
python3 -m katilim.cli ozet --butce 800                   # pazar/sektör/endeks (Faz 1.1b)
python3 -m katilim.cli mutabakat                          # ön mutabakat (Faz 4.0)
python3 arac/xktum_referans.py --indir --ayristir --kur    # XKTUM referansı (Faz 4.1)
python3 -m katilim.cli mutabakat --donem 2026-05          # değişim mutabakatı (Faz 4.2)
python3 -m katilim.cli olaylar                            # olay serisi (Faz 5.1)
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

## Tolerans zinciri — TEK UYGULAMA (11 Ağu 2026)

Zincir yalnız **`karar.zincirle_degerlendir`**'de. `panel.panel_uret` ve
`karar.seri_degerlendir` ikisi de ona delege eder; `panel.py` zincir
adlarını (`ZINCIR_BOSLUGU`, `ZINCIR_BOSLUK_GUN`, `ZINCIR_TEMIZ`) geriye
uyumluluk için yeniden dışa veriyor. **İkinci bir kopya açmayın.**

Neden: 2.3 zinciri dönem bazına çevirdi ama yalnız `panel_uret`'te.
`seri_degerlendir` bildirim bazında kaldı ve iki uygulama ayrıştı —
`panel.csv` doğruydu, `cli toplu` aynı dönemin düzeltmesini "önceki
dönem" sanıp **sahte eleme** üretiyordu. Gerçek vaka DCTTR: üç formunda
`toplu` `UYGUN / TOLERANSTA / UYGUN_DEGIL` diyordu, doğrusu üçüncüde de
`TOLERANSTA`. Testler: `test_ayni_donem_duzeltmesi_zinciri_ilerletmiyor`,
`test_zincir_tek_uygulama_panel_delege_ediyor`.

Delegasyon doğrulandı: `panel.csv` ve `snapshot_*.csv` yeniden üretildi,
**ikisi de birebir aynı** kaldı.

`panel_uret`'in zincire eklediği tek şey **dönem anahtarının meta
veriden** gelmesi (`ArsivKayit.yil/periyot`), formun kendi etiketinden
değil. `cli toplu`'nun meta verisi yok, form etiketini kullanıyor —
ölçüldü, mevcut arşivde **0 grupta** fark üretiyor (163 düzeltme
grubunun hepsinde form etiketi grup içinde tutarlı).

## Bilinen hata — DÜZELTİLDİ (3.1, 10 Ağu 2026)

~~`karar.py:187` sıralama anahtarı bozuk.~~ `seri_degerlendir` artık
**yalnız `gonderim_ts` ile** sıralıyor. Dönem etiketi kronoloji taşımıyor:
`3 Aylık`/`9 Aylık`/`Yıllık` eski anahtarda aynı kovaya düşüyordu ve
futbol kulüpleri "2024/Yıllık"ı Ağustos 2025'te veriyor. Zaman damgası
olmayan kayıt **en sona** konuyor — bilinmeyen tarihi geçmişe koymak
sonraki dönemlerin tolerans durumunu sessizce değiştirirdi.
Testler: `test_siralama_yalniz_gonderim_ts_ile`,
`test_zaman_damgasiz_kayit_sona_gidiyor`.

## Doğrulanmamış varsayımlar

Karar motorunda kural olarak kodlu ama **kanıtlanmamış** (spec §2.3):

- **H1:** 4A'daki herhangi bir EVET kesin elemedir. → Tek gözlem: THY 2025.
- **H2:** Kâr payı imtiyazı, tasfiye payı imtiyazıyla aynı ağırlıkta eler.
- **H3:** BIST payda olarak max(ort. PD, toplam varlık) kullanıyor.
- **H4:** Tolerans durumu şirket bazında, kriter bazında değil.
- **H5:** BIST formun **özet alanındaki** oranı kullanıyor, kalemlerden
  yeniden hesaplananı değil. **Varsayılan: özet alanı** — aritmetik
  doğruluk yüzünden değil, hata maliyeti asimetrisi yüzünden (özeti
  kullanan BIST + kalemi kullanan biz = yanlış pozitif, pahalı olan hata).
  ⚠ **H5 mevcut veriyle SINANAMIYOR.** 22 ayrışan kayıt → 3'ü tanımsız
  (4E=0) → 19 aday → yalnız 1'i farklı *karar* veriyor (PNLSN 2025/6
  Aylık) → o da geçersiz kılınmış düzeltme, 2.3 sonrası **n=0**.
  Yani H5 desteklenmiş değil, yalnızca yanlışlanamamış. 4.0 onu sınamaya
  çalışmasın; örneklem panel derinleştikçe birikir.

**4.2 kapsaması eşitsiz ve bu bir bulgudur:** H3 33 olay · H4 8 · H1 2 ·
**H2 SIFIR** · H5 ayırt edici örneklem yok. "Uyuşmazlık yok" yalnızca
sınanan hipotezleri destekler; H2 ve H5 sınanmadı.

**H3 uygulanmamalı** (plan 3.2): PD paydası kararları gevşetir, yanlış
negatifimiz zaten sıfır — gevşetmek yalnız yanlış pozitif üretebilir.

**H6 (gecikmeli yeniden giriş) kanıtlı ama kodlanmadı:** KLSER, PNSUT,
PEKGY. TKBB Standardı md. 3.5'in giriş yönünde simetrik hüküm içerip
içermediğine bakılmadan kodlanmayacak.

Bir hipotez revize edilirse spec ve kod aynı commit'te güncellenir.

## Test katmanları — karıştırmayın

- **Gerçek veri testleri** (THY 2025/Yıllık fixture): kanıttır. Oran formülleri
  ve karar motoru KAP'ın kendi çıktısına karşı doğrulanmıştır.
- **Sentetik HTML testi**: duman testidir. Parser mekaniğinin çalıştığını
  gösterir, gerçek KAP HTML'inin o yapıda olduğunu **kanıtlamaz**.

Sentetik HTML'i, gerçek HTML'e uydurmak için değiştirmek anlamsızdır — gerçek
doğrulama `dogrula` komutunu gerçek bir dosyayla çalıştırmaktır.

**Dış çapraz doğrulama** (11 Ağu 2026, n=1, tekrarlanmayacak): Fintables'ın
bağımsız KAFİF parser'ı RYGYO 2025/Yıllık'ta aynı üç oranı üretiyor
(12,81 / 5,26 / 13,10). Kayıt amaçlı; rutin kontrol değil.

## Sıradaki iş

**Faz planı ve her adımın promptu: @PROJE_PLANI.md.** Adım sırası, çıkış
kriterleri ve otomatikleştirilmeyecek karar noktaları orada. Aşağıdaki özet
onunla çelişirse plan değil bu dosya esastır.

### Nerede kaldık (10 Ağu 2026)

Biten: **Faz 0** · **1.0** rota keşfi · **1.1** evren · **2.0** derinlik
keşfi · **1.2** bildirim sorguları · **1.4a** form arşivi · **1.3** parser
kapısı · **1.4b** snapshot paneli · **1.1b** özet sayfaları · **4.0** ön
mutabakat · **2.3** düzeltme çözümü · **3.1** tolerans zinciri ·
**4.1** XKTUM tarihsel referansı · **4.2** değişim mutabakatı ·
**5.1** olay serisi.
Testler: 238 geçiyor (27 motor + 9 çekici + 24 evren + 8 derinlik +
16 bildirim + 7 rsc + 13 toplayıcı + 9 pilot + 28 panel + 20 özet +
16 mutabakat + 13 xktum + 23 değişim + 25 olay).

**DOĞRULAMA KAPISI GEÇİLDİ.** 4.2'de 95/95 olay uyuştu, uyuşmazlık sıfır;
testin gücü ölçüldü (taban %47/%53, şansla olma olasılığı ≈10⁻²⁹).
Spec §4'ün "Faz 4 öncesi panel araştırma çıktısıdır" kaydı artık geçmişte.

**Faz 5.1 bitti — 206 olay / 137 pay kodu.** Ayrıntı:
@OLAY_SERISI_RAPORU.md (`katilim/olay.py`, 0 istek).

- **Karşı olayların temiz penceresi NEGATİF.** Öncüllük medyanı ilk
  bildirimde 56 gün (p95 sonrası **+18**), karşı olayda 28 gün (p95
  sonrası **−10**). Düzeltmeden gelen bilgi ancak hızlı işlem edilirse
  kullanılabilir — ki düzeltme riskinin en yüksek olduğu rejim odur.
  5.2'nin ölçeceği ödünleşmenin sayısal çekirdeği bu.
- **Olgunluk ETİKET değil TARİH olarak saklanıyor** (`olgunlasma_ts` =
  olay+38g, `kesinlesme_ts` = sonraki dönemin yayını). Etiketi dosyaya
  gömmek backtest'i hesaplandığı ana kilitlerdi; `Olay.kesinlik(t)`
  çağıranın kendi saatiyle karşılaştırıyor.
- **Düzeltme İPTAL etmiyor, KARŞI OLAY üretiyor** (84/206). Silmek
  look-ahead'a davetiye: o sinyal gerçekten yayımlanmıştı.
- **`g1_teyitsiz` 68 olayda açık** — 2.3'ün G1 bulgusu koda girdi.
- **Look-ahead denetimi üç katmanlı ve MUTASYONLA kanıtlandı.** Üç
  kasıtlı hata enjekte edildi, üçü de yakalandı. En sinsi olan
  `gecerli_kayit=EVET` süzgeci — karşı olayları tümüyle siliyor ve
  seriyi olduğundan temiz gösteriyor; nokta-zaman replay yakaladı.
- **Gözden geçirmede açık bulundu ve kapatıldı:** replay testi paneli
  kırpıyordu ama TAKVİMİ kırpmıyordu, dolayısıyla `sonraki_yururluk`'un
  duyuru filtresi kaldırılsa yakalayamazdı. Ayrı test eklendi.
- **`endeks_yururluk_ts` duyurusu geçmiş revizyondan türetiliyor** —
  28.09.2025'te yayımlanan form doğru biçimde 01.05.2026'ya bağlanıyor.

Sıradaki: **5.2** (fiyat etkisi — **KAYNAK SEÇİLMEDİ, açık karar**) →
**5.3** (`katilim.api`). 5.3 ağa çıkmıyor.
Ertelenen/düşürülenler ve gerekçeleri @PROJE_PLANI.md'de.

Her tamamlanmış adımın ölçümü kendi raporunda; **bu dosya onları
tekrarlamaz.** Anlatı arşivi: @PLAN_ARSIV.md (otomatik yüklenmez).

| Adım | Rapor |
|---|---|
| 1.0 rota keşfi | @ROTA_KESFI_RAPORU.md |
| 1.1b özet sayfaları | @OZET_RAPORU.md |
| 1.2 bildirim sorguları | @BILDIRIM_GECMISI_RAPORU.md |
| 1.3 parser kapısı | @PILOT_20_RAPORU.md |
| 1.4a arşiv çekimi | @INDIRME_RAPORU.md |
| 1.4b snapshot paneli | @TOPLAMA_RAPORU.md |
| 2.0 derinlik keşfi | @DERINLIK_KESFI_RAPORU.md |
| 2.3 düzeltme çözümü | @DUZELTME_RAPORU.md |
| 4.0 ön mutabakat | @ON_MUTABAKAT_20260810.md |
| 4.1 XKTUM referansı | @XKTUM_REFERANS_RAPORU.md |
| 4.2 değişim mutabakatı | @MUTABAKAT_2025-10.md · @MUTABAKAT_2026-05.md |
| 5.1 olay serisi | @OLAY_SERISI_RAPORU.md |

### Kalıcı olarak taşınan bulgular

Aşağıdakiler rapora değil buraya ait: sonraki her adımı bağlıyorlar.

- **Evren 795 pay kodu / 746 tüzel kişi.** `stockCode` virgüllü çoklu kod
  taşıyabiliyor. **Sorgu ekseni uuid, panel ekseni ticker.** Karar tüzel
  kişi düzeyinde, endeks üyeliği pay kodu düzeyinde — aynı uuid'in bir
  kodu XKTUM'da olup diğeri olmayabilir. Mutabakatta bu sahte
  uyuşmazlıktır.
- **`/tr/kfif/{id}-{slug}` rotası veri kaynağı olarak YASAK.** Gönderim
  zaman damgası yok, 4A'nın son üç satırı render edilmiyor. Oranlar
  tuttuğu için "çalışıyor" görünür; self-check tutarları kapılıyor,
  beyanların eksiksizliğini değil.
- **Sorgu penceresi 1 yıl ve 1 gün/gün kayıyor** — ama kayan şey
  **keşif**, erişim değil (n=15). Kimlik `bildirim_gecmisi.csv`'ye
  yazıldıysa form sonra da inebiliyor. **Bu yüzden düzenli 1.2 koşusu en
  kritik bakım işidir.** `veri/evren/*.csv` git'te; her commit o günün
  keşif penceresinin fotoğrafı.
- **Kalıcı hata (404) negatif önbelleğe yazılır, geçici hata (429/5xx)
  YAZILMAZ.** 1.2'de 55, 1.4a'da 114 form bu ayrım sayesinde kurtarıldı.
- **`toplayici.py` tek sabit pencere toplayıcısıdır** — sayfalama döngüsü
  yazmayın (92=92).
- **Tolerans zinciri TEK uygulama: `karar.zincirle_degerlendir`.**
  `seri_degerlendir` ve `panel.panel_uret` ona delege eder; ikinci bir
  kopya açmayın (aynı hata iki kez buradan çıktı, yapısal test var).
  Mutabakatın girdisi **zincirli panel** (`panel.csv`) — snapshot zincirsiz
  olduğu için BIST'in md. 3.5 uygulayan kararıyla kıyaslanamaz.
- **Düzeltme sinyali `isChanged` alanından gelir**, metin aramasından
  değil. `DUZENLENEN` / `DUZELTILEN` ayrı taşınır, fark belgelenmemiş.
- **Revizyon takvimi düzenli DEĞİL:** 01.07.2024 → 01.12.2024 →
  01.05.2025 → 01.10.2025 → 01.05.2026. Takvim CSV'den okunur, ay
  sabitinden türetilmez. **Kesim noktası yürürlük değil DUYURU tarihi**
  (4–7 gün önce).
- **Düzeltme penceresi ölçüldü** (n=181): medyan 21 gün, p95 38, max 55.
  Karar çeviren 14 düzeltmenin hepsi ≤31 gün. Bilgi avantajı penceresi
  bu yüzden 4-8 hafta değil **2-3 hafta** (spec §5.2).
- **G1 kapısı en güvenilmez.** Karar çeviren 14 düzeltmenin 9'u
  `b1_1`/`b1_2` ve 7'si False→True: ilk bildirim esas sözleşme
  beyanlarını eksik veriyor.
- **Muaf ≠ elenmiş.** Katılım esaslı finans kuruluşları (ALBRK, KTLEV)
  KAFİF vermiyor ama XKTUM'da. `KAPSAM_DISI`'yı "elenmiş" gibi işlemeyin.
- **Kapsam sınırı: form var, bildirim yok.** Yeni halka açılan 8 şirketin
  KAFİF'i kfif sayfasında var, bildirim akışında yok. Geçici — ilk
  dönemsel beyanla kapanır.

### Açık kararlar

- **H2 sınanmadı** (4.2'de 0 olay). "Uyuşmazlık yok" onu desteklemiyor.
- **H6 kanıtlı ama kodlanmadı** — gecikmeli yeniden giriş (KLSER, PNSUT,
  PEKGY). TKBB Standardı md. 3.5'in giriş yönünde simetrik hüküm içerip
  içermediğine bakılmadan kodlanmayacak.
- **KTLEV çözüldü** (muaf), ama **26 varlık kiralama** hâlâ belirsiz
  muafiyette — sektör alanları boş.
- **5.2 fiyat verisi kaynağı** seçilmedi.
