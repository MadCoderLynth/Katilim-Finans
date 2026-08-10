# BIST Katılım Uygunluk Motoru

KAP'ta yayımlanan Katılım Finans İlkeleri Bilgi Formu (KAFİF) bildirimlerinden
katılım endeksi uygunluk kararı üretir. Kullanım amacı: swing trading sistemine
bağlanacak, look-ahead'sız tarihsel uygunluk paneli.

Detaylar: @BIST_Katilim_Uygunluk_Motoru_Spesifikasyonu_v0.1.md ve @OKUBENI.md

**Dil: tüm çıktılar, yorumlar ve commit mesajları Türkçe.**

## Komutlar

```bash
python3 tests/test_motor.py                              # 22 test, pytest gerektirmez
python3 tests/test_cekici.py                             # 9 test, çekim katmanı (ağa çıkmaz)
python3 tests/test_pilot.py                              # 9 test, 20 gerçek KAP belgesi (kanıt katmanı)
python3 -m katilim.cli bildirimler --butce 800            # KAFİF kimlikleri (Faz 1.2)
python3 -m katilim.cli indir --butce 2600                 # formları arşivle (Faz 1.4a)
python3 -m katilim.cli panel                              # snapshot paneli (Faz 1.4b)
python3 -m katilim.cli ozet --butce 800                   # pazar/sektör/endeks (Faz 1.1b)
python3 -m katilim.cli mutabakat                          # ön mutabakat (Faz 4.0)
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

Biten: **Faz 0** · **1.0** rota keşfi · **1.1** evren · **2.0** derinlik
keşfi · **1.2** bildirim sorguları · **1.4a** form arşivi · **1.3** parser
kapısı · **1.4b** snapshot paneli · **1.1b** özet sayfaları · **4.0** ön
mutabakat · **3.1** tolerans zinciri.
Testler: 162 geçiyor (24 motor + 9 çekici + 24 evren + 8 derinlik +
15 bildirim + 7 rsc + 13 toplayıcı + 9 pilot + 21 panel + 20 özet +
12 mutabakat).

Sıradaki: **3.2** (belirsiz bant / PD paydası — PD kaynağı sorusu açık),
**2.2** (şablon versiyonlama) veya **2.0b**. Hiçbiri aciliyetli değil.

**Faz 3.1 bitti — tolerans zinciri panele bağlandı.** Ayrıntı:
`katilim/panel.py::panel_uret`, çıktı `veri/panel/panel.csv` (1.280 satır).

- **Sıralama hatası düzeltildi** (yukarıdaki bölüm). 
- **Zincir 5 satır çevirdi** (TOLERANSTA → UYGUN_DEGIL): ALVES, DCTTR,
  DOGUB, KLMSN, KONTR. Karar dağılımı 660 UYGUN_DEGIL / 582 UYGUN /
  38 TOLERANSTA (snapshot: 655 / 582 / 43).
- **Mutabakata etkisi SIFIR — ve bu bir H4 bulgusu.** 4.0'ın öngördüğü
  aynen gerçekleşti: KLMSN'in uyuşmazlığı kapandı ama DCTTR'de yenisi
  açıldı (XKTUM üyesi olduğu hâlde eliyoruz). Gerçek uyuşmazlık 2 → 2.
  **H4 revize EDİLMEDİ**; zincir spec §2.1'e sadık kodlandı, ama
  nokta-zaman kanıtı onu desteklemiyor. Karar 4.3'ün.
- **Panel `karar`ı ÖZET alanından** (H5 varsayılanı). İlk yazımda
  `seri_degerlendir` oranları kalemlerden hesaplıyordu ve tarihsel panel
  ile snapshot, zincirle ilgisi olmayan bir sebeple ayrışıyordu;
  `oranlar_fn` parametresiyle düzeltildi.
- **ZİNCİR BOŞLUĞU: 0 satır** ve bu doğru bir sıfır. Boşluk ölçütü
  şirketin kendi serisindeki sessizlik (>280 gün ≈ 1,5 kadans); ölçülen
  ardışık aralık medyanı 185 gün, en uzunu 259. **1 yıllık pencere zaten
  bir boşluğu barındıramıyor.**

**AÇIK KARAR — zincir boşluğunda tolerans durumu.** Spec tanımlamıyor.
Geçici davranış: **durum taşınır**, satır `ZINCIR_BOSLUGU` ile işaretlenir.
Bu pencerede hiç tetiklenmiyor ama panel derinleştikçe tetiklenecek.

**Faz 4.0 bitti — ön mutabakat koştu.** Ayrıntı: @ON_MUTABAKAT_20260810.md
(`katilim/mutabakat.py`, `python3 -m katilim.cli mutabakat`, 11 istek).

- **Gerçek uyuşmazlık 2/518 = %0,39** (spec §4 eşiği <%5). Sınıf dağılımı:
  516 UYUMLU · 259 KAPSAM · 11 PANELDE_YOK · 7 DÖNEM · **2 GERÇEK**.
  Bu bir NOKTA-ZAMAN ölçümdür; H1–H4'ü sınamaz, panel hâlâ araştırma çıktısı.
- **KAPSAM denetimi uyum denetiminden ÖNCE gelmeli.** İlk yazımda
  `BEYAN_YOK` bir şirketin XKTUM dışında olması "kararımız tuttu" sayılıp
  UYUMLU'ya yazılıyordu; bu oranı sahte iyileştiriyordu. Düzeltmeden sonra
  UYUMLU 761 → 516. Görüşümüz olmayan kayıt ne uyumlu ne uyumsuzdur.
- **8 açık isim ÇÖZÜLDÜ ve üç okumanın hiçbiri değil.** kfif ikili sondası
  8/8 **dolu form**; filtresiz bildirim sorgusu (3 örnek) 0 KAFİF. Yani
  **form var, bildirim yok** — hepsi yeni halka açılmış şirketler.
  **Bu bir KAPSAM SINIRI**: bildirim tabanlı toplama onları yapısal olarak
  göremiyor. Karar noktası açık (@ON_MUTABAKAT_20260810.md §3.4).
- **İki gerçek uyuşmazlık, ikisi de yanlış pozitif:** KLMSN (tolerans
  zinciri uygulansa çözülür) ve PEKGY (H3 adayı veya modellenmemiş
  yeniden giriş kuralı).
- **Tolerans zinciri ölçüldü:** uygulansa 5 kayıt çevrilir, 2'si en güncel
  kayıt — KLMSN'i düzeltir ama **DCTTR'de yeni uyuşmazlık açar**. H4 bu
  veriyle onaylanmış sayılmaz.
- **`tasarruf finansman` muafiyete taşındı** (spec §0.4 + `evren.py` +
  test, aynı commit). KTLEV `AYIRT_EDILEMEDI` → `KAPSAM_DISI`;
  belirsiz muafiyet 27 → 26.
- **H5 sınanmadı ve sınanamaz** (ayırt edici örneklem n=0). Onun yerine
  ölçüldü: ayrışan 22 kaydın 5'i düzeltme (%22,7 ↔ panel geneli %14,8) —
  **zayıf sinyal, n=22 ile kanıt değil.**

**Faz 1.1b bitti — pazar, sektör, endeks üyeliği evrende.** Ayrıntı:
@OZET_RAPORU.md (`katilim/ozet.py`, `python3 -m katilim.cli ozet`).

- **746/746 özet sayfası çekildi.** pazar 793/795 pay kodunda dolu, sektör
  643/795. `endeks_uyeligi.csv`: 5.161 satır / 605 pay kodu, **`olcum_tarihi`
  her satırda dolu** (bu tablo bugünün fotoğrafı, tarihsel DEĞİL).
- **BIST KATILIM TÜM üyesi 243 pay kodu** — 4.0'ın referans tarafı.
  Panelle join tutuyor (232 ortak); mutabakat 4.0'ın işi.
- **Pazar sözlüğü spec §0.4'ün varsaydığından geniş:** Yıldız/Ana/Alt
  dışında nitelikli yatırımcı pazarı, piyasa öncesi platform, yakın izleme,
  gözaltı, emtia da var (25 değer/kombinasyon) ve **bir kod birden çok
  pazarda** olabiliyor. XKTUM ön şartını sağlayan: 605 pay kodu.
- **Belirsiz muafiyet 33 → 27.** 6 menkul kıymet yatırım ortaklığı kapandı
  (§0.4'te birebir yazılı; altısının da KAFİF'i yok, veri düşmedi).
  Kalan 26 varlık kiralama (sukuk SPV, sektör alanı boş) + KTLEV **MUAF
  İŞARETLENMEDİ**.
- **`BütçeAşıldı` tetiklendi ve karar noktası olarak işletildi:** 800 doldu,
  400 ek bütçe onayla alındı. Yeniden denemeler de bütçeden düşüyor
  (604 çekim + 196 deneme = 800).

**AÇIK KARAR — KTLEV.** Sektörü `MALİ KURULUŞLAR / FİNANSMAN ŞİRKETLERİ`;
spec §0.4'ün muafiyet listesinde tasarruf finansman yok ama KTLEV hiç KAFİF
vermemiş. Ya §0.4'e madde eklenecek ya da "muaf değil ama beyan vermiyor"
(mevcut `BEYAN_YOK`) durumuna alınacak. Önerim ikincisi; seçilmedi.

**Faz 1.4b bitti — snapshot paneli üretildi.** Ayrıntı: @TOPLAMA_RAPORU.md
(`katilim/panel.py`, `python3 -m katilim.cli panel`, 0 istek).

- **1.280 panel satırı** (1.276 bildirim × ticker ekseni), 539 pay kodu.
  Ayrıştırma hatası 0, dosyası eksik 0.
- **Karar iki sütun:** `karar` ÖZET alanından (H5 varsayılanı),
  `karar_kalem_bazli` kalemlerden. Dağılım özet: 655 UYGUN_DEGIL /
  582 UYGUN / 43 TOLERANSTA; kalem: 655 / 583 / 42.
- **H5'in fiili sınama örneklemi n=1.** `h5_ayirt_edici` 19 satırda EVET
  ama kararı çeviren tek kayıt var: **PNLSN 2025/6 Aylık** (özet %5,30
  TOLERANSTA ↔ kalem %4,67 UYGUN). 4.0 bu satıra bakacak; tek gözlemle
  H5 doğrulanmış sayılmayacak.
- **Karantina silmez, işaretler:** 22 kayıt `karantina=EVET` ile panelde
  duruyor. Silmek 22 şirketi sessizce düşürmek olurdu.
- **Dönem anahtarı meta veriden**; formun kendi etiketi
  `form_donem_etiketi` sütununda (20 satırda ayrışıyor, yıl hiç ayrışmıyor).
- **Ticker artık dosya adından tahmin edilmiyor** — OKUBENI açığı kapandı.
- **Tolerans zinciri YOK** (snapshot). Dönemler arası taşıma ve
  `karar.py:187`'deki bozuk sıralama anahtarı 3.1'in işi.

**Faz 1.3 bitti — parser 1.276 gerçek belgede doğrulandı.** Ayrıntı:
@PILOT_20_RAPORU.md (betik: `arac/pilot_20.py`, 0 istek).

- **Ayrıştırma hatası 0/1.276.** Self-check 1.254 GEÇTİ / 22 KALDI (%98,3);
  **22'sinin 22'si teşhis edildi**, açıklanmamış karantina yok.
- **KALAN kayıtların sebebi parser DEĞİL.** 19'unda formun kendi 4E TOPLAM
  satırı kendi kalemleriyle tutmuyor (özet oran o TOPLAM'dan hesaplanmış);
  3'ünde 4E=0, yani oran tanımsız ama form 0 basıyor. **Kural 3'ün var
  olma sebebi tam olarak bu** — TOPLAM satırını parse etseydik 19 form
  sessizce "tutarlı" görünecekti.
- **Tek şablon imzası** (1.276/1.276): `4A|4B|4C|4D|4E|5F|5G|5H|6I|6J|OZET|S1|S2|S3`.
  2.2 bu veriyle tek etiket üretecek. **2024 öncesi şablon SINANMADI** —
  bu pencereden çekilemiyor, "sınandı" sayılmıyor.
- **Her formda 55 kalem ve 13/13 beyan dolu.** Yani "tabloları kısmen boş
  küçük şirket" ölçütü satır sayısıyla ölçülemez; vekil ölçüt *dolu (sıfır
  olmayan) kalem sayısı* (en uç: ISGYO, 55'in 1'i dolu).
- **`is_duzeltme` DOĞRULANDI**, OKUBENI açığı kapandı: 181/181 yakalandı,
  kaçırma yok. KAP sayfaya "Düzeltilmiş Bildirim" + "Düzeltme Nedeni: …"
  basıyor; ikincisi 2.3 için değerli, modelde alanı yok.
- **Formun dönem etiketi meta veriden farklı olabiliyor** (20/1.276):
  "Yıllık" → "4. 3 Aylık Bildirim" (13), "6 Aylık" → "2. 3 Aylık Bildirim" (7).
  Yıl hiç ayrışmıyor. **Panel dönem anahtarı meta veriden alınmalı.**

**AÇIK KARAR — hangi oran karara girer.** 19 kayıtta iki oran var: bizim
kalemlerden hesapladığımız ve formun özetindeki. En az birinde fark kararı
çeviriyor (PNLSN 2025/6 Aylık: 4,67 % → UYGUN, form 5,30 % → aşım). BIST
beyan esaslı çalıştığı için özet alanı kullanıyor olabilir. Kod içinde
seçilmedi; panelde her iki oranın da taşınması önerildi (1.4b).

**Faz 1.4a bitti — arşiv tam.** 1.276/1.276 form indi, eksik yok, kalıcı
hata yok. 239 MB, `veri/ham/{TICKER}_{YIL}_{PERIYOT}_{bildirim_id}.html`.
İndeks: `veri/ham/arsiv_indeksi.csv` (sha256 dahil).

- **Pencere dışı erişim ufku BULUNAMADI (n=15).** Bugünkü keşif
  penceresinde olmayan 15 kimliğin **15'i de indi**, 404 yok; üçü
  `dogrula` ile açıldı, üçünde de self-check GEÇTİ. Yani asıl yedeklenmesi
  gereken şey **kimlik listesi** (`bildirim_gecmisi.csv`, ~90 KB) — 239
  MB'lık HTML ondan yeniden kurulabilir. **Ama HTML arşivi yine silinmez:**
  ölçüm bugünün davranışı, KAP yarın bu rotaya da ufuk koyabilir.
  → **Karar: `veri/evren/*.csv` git'e alındı** (~420 KB). Yan fayda: her
  commit o günün keşif penceresinin fotoğrafı; pencerenin nasıl kaydığının
  kaydı kendiliğinden birikiyor. `veri/ham/` git dışı, ayrı yedek ister.
- **Erişim ufkunun derinliği ÖLÇÜLEMEDİ.** En eski kimliğimiz 05.08.2025;
  daha eskisine ait kimlik olmadığı için "1 yıldan derine iniyor mu"
  sorusu bu veriyle cevaplanamaz.
- **114 geçici hata üç geçişte kapatıldı** (aralık 2 → 5 → 6 sn).
  Hiçbiri negatif önbelleğe yazılmadı; yazılsaydı 114 form kalıcı olarak
  "yok" sayılacaktı.
- **Beyan durumu** (`veri/evren/beyan_durumu.csv`, 795 pay kodu):
  539 BEYAN_VAR · 150 KAPSAM_DISI · 73 BEYAN_YOK · **33 AYIRT_EDILEMEDI**.
  Sonuncusu bilinçli olarak `MUAF` değil — muaf olan ile beyan vermeyen
  bu rotadan ayırt edilemiyor.
- **`Çekici.getir(onbellekle=False)`** eklendi: arşivi kendi adlandırmasıyla
  başka yere yazan çağıran için. Okuma yine önbellekten.

**Sıra 7 Ağustos'ta değişti; iki kural yer değiştirdi:**

1. **1.4 ikiye bölündü.** 1.4a yalnız indirir ve arşivler (parser'a hiç
   dokunmaz), 1.4b ayrıştırır ve paneli üretir.
2. **20/20 parser kapısı (1.3) artık çekimi değil paneli kapılıyor.**
   Eski gerekçe — "2.600 isteği doğrulanmamış parser'a harcamayalım" —
   yanlıştı: çekim parser'ı kullanmıyor, ayrıştırma arşivden tekrar
   tekrar yapılabiliyor (kural 6). Yanlış parser bedava düzeltilir,
   kaçırılan bildirim düzelmez.

Zaman duyarlı olmayan her şey arşivin arkasına alındı:
**1.2 ✔ → 1.4a ✔ → 1.3 ✔ → 1.4b ✔ → 1.1b ✔ → 4.0 ✔ → 3.1 ✔ → 2.2 → 3.2.**

**Faz 1.2 bitti — ve zaman duyarlılığının yerini değiştirdi.**
@BILDIRIM_GECMISI_RAPORU.md (651 istek / onaylı 800).

- **Kayan pencere KEŞFİ öldürüyor, ERİŞİMİ değil (n=1).** Pencereden düşmüş
  1472632, `/tr/Bildirim/{id}`'den bugün indi: 200, 13/13 beyan, self-check
  GEÇTİ. Kimlik `veri/evren/bildirim_gecmisi.csv`'ye yazıldıysa form sonra
  da inebiliyor. Yani **asıl zaman duyarlı adım 1.2'ydi.** Düzenli 1.2
  koşusu artık en kritik bakım işi. *Gözlem tek bildirime dayanıyor;*
  1.4a'yı ertelemek için gerekçe sayılmadan birkaç kimlikle daha sınanmalı.
- **1.276 benzersiz form** (2.0'ın tahmini ~1.500'dü) → 1.4 maliyeti
  ~1.276 istek, ~68 dk, onaylı 2.600'ün %49'u.
- **`periyot` yalnız 6 Aylık/Yıllık değil:** `9 Aylık` (7) ve `3 Aylık` (5)
  de var; futbol kulüpleri 31 Mayıs kapanışı yüzünden "2024/Yıllık"ı Ağustos
  2025'te veriyor. **Panel kronolojisi dönem etiketiyle değil `gonderim_ts`
  ile sıralanır.** Spec §1.2 aynı commit'te güncellendi.
- **Düzeltme sinyali bulundu:** RSC'deki `isChanged` alanı `DUZENLENEN` /
  `DUZELTILEN` değerlerini taşıyor. 163 tekrar eden (ticker, yıl, periyot)
  grubu var, 135 şirkette. OKUBENI'deki "is_duzeltme doğrulanmadı" açığının
  gerçek kaynağı bu — 2.3 metin araması yapmasın.
- **`disclosureClass=DG` artık n=12'de doğrulandı**, KAFİF kaybettirmiyor.
- **33 belirsiz muafiyetin hepsi KAFİF vermemiş.** Tutarlı ama kanıt değil:
  muaf olan da beyansız olan da vermez. 1.4'te `AYIRT_EDILEMEDI`, `MUAF` değil.

**Negatif önbellek eklendi** (`veri/onbellek/negatif.tsv`): kalıcı hata (404)
bir kez alınır. **Geçici hata (429/5xx/bağlantı) YAZILMAZ** — 1.2'nin ilk
geçişinde 55 şirket geçici olarak alınamadı, ikinci geçişte hepsi geldi;
geçici hata negatif önbelleğe yazılsaydı o 55 şirket panelden sessizce
düşerdi.

**`katilim/rsc.py` açıldı — iki sessiz veri kaybı hatası burada kapatıldı.**
RSC yükü JS dize literalidir; `replace('\"','"')` ile çözmek JSON'un kendi
kaçışlarını bozuyor ve **özetinde tırnak geçen bildirimler sessizce
düşüyordu**. İkinci hata düzeltmenin kendisindeydi: açılış parantezi
eşleşmenin sonundan aranınca `{"alan":` kalıbı iç nesneyi buluyor (746
şirketin 30'u kayboldu). İkisi de kendi denetimlerine yakalandı —
`Ayiklama.bozuk` sayacı ve evren çıktısının satır satır karşılaştırılması.
**Yeni ayrıştırıcı yazarken bu iki tuzağı varsayın.**

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
bütçeler: 1.1 → 5, 1.1b → 800 + 400 ek (bitti, ~956 deneme), 1.2 → 800, 1.3 → 30, 2.0 → 30 (bitti, 22
kullanıldı), 1.4 → 2.600. Bunlar plan adımı başına ayrı ayrı verilir;
`BütçeAşıldı` bir arıza değil, sorulacak bir sorudur — kodun içinden otomatik
büyütmeyin.

1.4 tahmini 2.0 sonrası aşağı çekildi: pencerede şirket başına ~3 değil **~2**
KAFİF görünüyor (THY'de 3'tü, biri düştü) → 746 sorgu + ~1.500 form ≈ **2.250**,
onaylanmış 2.600'ün altında.
