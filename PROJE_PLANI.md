# Proje Planı — Faz Promptları

Bu belge, her fazın Claude Code'a verilecek promptlarını içerir. Kaynaklar:
`CLAUDE.md` (değiştirilemez kurallar), spec v0.1 (§4 faz tanımları),
`DEVIR_NOTU_2026-08-05.md` (alan bulguları ve teknik durum).

**Durum (5 Ağu 2026):** Faz 0 tek örnekte doğrulandı (THY 2025/Yıllık,
self-check GEÇTİ). Faz 1.0 (rota keşfi) bitti — `ROTA_KESFI_RAPORU.md`.
Sıradaki: **Faz 2.0** (sıra değişti — gerekçe "Faz bağımlılıkları"nda).

**Rota keşfinin plana getirdiği üç değişiklik:** eski 1.2 (kimlik eşlemesi)
iptal — iki kimlik aynı istekten çıkıyor; eski 2.1 (bildirim geçmişi) 1.2'ye
taşındı — pencere 1 yıl olduğu için güncel ile geçmiş aynı istek; Faz 2 bloke,
önüne 2.0 derinlik keşfi eklendi.

---

## Kullanım

Her prompt tek bir Claude Code oturumunda bitirilebilir boyutta ve **kendi
çıkış kriteri** var. Kriter sağlanmadan bir sonrakine geçilmez.

### Ortak önek — her promptun başına yapıştırılır

```
Bağlam: CLAUDE.md, BIST_Katilim_Uygunluk_Motoru_Spesifikasyonu_v0.1.md ve
DEVIR_NOTU_2026-08-05.md dosyalarını oku. CLAUDE.md'deki "Değiştirilemez
kurallar" bölümü bu görevde de geçerli; test kırılırsa kuralı değil kodu
düzelt.

Dil: kod yorumları, çıktılar, commit mesajları Türkçe.
Bitirmeden önce: python3 tests/test_motor.py ve python3 tests/test_cekici.py
tamamı geçmeli. Yeni davranış eklediysen testini de ekle.
```

### Ortak sonek — her promptun sonuna yapıştırılır

```
Yapma:
- TOLERANS sabitini gevşetme.
- None beyanı False'a çevirme (BELIRSIZ kararı doğru davranıştır).
- HızSınırlayıcı.oturum_butcesi'ni kod içinden otomatik büyütme;
  BütçeAşıldı bir arıza değil, bana getirilecek bir karar noktasıdır.
- Tabloyu konumdan tanıma; içerik imzası kullan.
- Spec'te yazılı bir hipotezi (H1-H4) kod içinde sessizce değiştirme;
  revizyon gerekiyorsa spec ve kodu aynı commit'te güncelle ve bana söyle.

Bitirince: ne yaptığını, hangi çıkış kriterini karşıladığını ve
karşılamadığın varsa nedenini kısaca yaz.
```

---

# FAZ 1 — Toplama Katmanı

**Spec çıkış kriteri:** Muaf olmayan tüm şirketler için ya kayıt var ya
"beyan yok" olarak işaretli.

> **Numaralandırma değişti (5 Ağu 2026).** Rota keşfi eski 1.2'yi (kimlik
> eşlemesi) gereksiz kıldı ve tarihsel derinliği bloke etti. Yeni sıra:
> 1.1 evren → 1.2 bildirim sorguları → 1.3 20/20 kapısı → 1.4 form çekimi.
> Eski 2.1 (bildirim geçmişi) 1.2'ye taşındı: pencere 1 yıl olduğu için
> "güncel" ile "geçmiş" aynı istek.

## 1.0 — Rota keşfi ✔ **BİTTİ (5 Ağu 2026)**

Çıktı: `ROTA_KESFI_RAPORU.md`, betik `arac/rota_kesfi.py`. 16 istek, bütçe
50'nin en fazla 5'i kullanıldı, `BütçeAşıldı` tetiklenmedi.

Aşağıdaki adımları bağlayan sonuçlar:

| Bulgu | Etkisi |
|---|---|
| `requests` üç rotada da yetiyor | `playwright` bağımlılığı yok |
| Evren tek istekte, RSC JSON'unda 746 kayıt | 1.1 ucuz (bütçe 5) |
| `mkkMemberOid` + `{id}-{slug}` aynı satırda | **eski 1.2 iptal** |
| Pazar bilgisi yok | 1.1'e sonda bir sonda eklendi |
| `bildirim_id` checkbox `id`'sinde | 1.2 ayıklayıcısının çıpası |
| `disclosureClass=DG` → 98'den 12'ye | 1.2 maliyeti ~8 kat düşük |
| Pencere sabit 1 yıl, kayıyor | **Faz 2 bloke → 2.0 açıldı** |
| `/tr/kfif/` zaman damgası ve 3 beyanı kaybediyor | rota yasak |
| sha256 istekten isteğe değişiyor | idempotanlık `bildirim_id` ile |

*Aşağıdaki 1.0 promptu arşiv olarak duruyor; yeniden koşulmaz.*

<details>
<summary>1.0 promptu (arşiv)</summary>

> Amaç evreni doldurmak değil, ölçmek. Bu adımın çıktısı kod değil, bir rapor.

```
Görev: KAP rotalarını düşük bütçeyle keşfet ve ölç.

Yeni dosya: arac/rota_kesfi.py (tek seferlik keşif betiği; katilim/ paketine
girmez, üretim kodu değildir).

katilim.cekici.Çekici'yi HızSınırlayıcı(min_aralik=2.0, jitter=1.0,
oturum_butcesi=50) ile kur. Önbellek dizini: veri/onbellek/.

Şu üç rotayı sırayla dene ve her biri için ölç:

1. https://kap.org.tr/tr/bist-sirketler
   - Sunucu tarafı render requests ile yetiyor mu, yoksa gövde boş bir
     JS iskeleti mi geliyor?
   - Sayfada kaç şirket satırı var? Tek sayfa mı, sayfalanıyor mu?
   - Ticker, unvan, pazar ve member uuid alanlarının hepsi HTML'de var mı?
   - Arka planda bir JSON/XHR ucu var mı (sayfanın kendi script'lerinde
     veya gömülü __NEXT_DATA__ benzeri bir bloğunda arayabilirsin)?

2. https://kap.org.tr/tr/bildirim-sorgu-sonuc?member={uuid}
   - Elimizdeki THY bildirimi (1566002) üzerinden bir uuid çıkarabiliyor
     musun? Çıkaramıyorsan bu rotayı 1. adımdan gelen herhangi bir uuid
     ile dene.
   - Kaç kayıt dönüyor, sayfalama parametresi var mı, KAFİF bildirimlerini
     filtrelemek için bir parametre görünüyor mu?

3. https://kap.org.tr/tr/Bildirim/1566002
   - Zaten çalıştığı biliniyor; yalnızca canlı sayfanın diskteki
     veri/ham/THYAO_2025_yillik.html ile aynı yapıda geldiğini doğrula
     (ayrıştırıcıyı canlı gövdeye karşı bir kez çalıştır).

Çıktı: ROTA_KESFI_RAPORU.md
Rapor şunları içermeli:
- Her rota için: istenen URL, HTTP durum, gövde uzunluğu, requests yetti mi
- Sayfa başına kaç kayıt, sayfalama parametreleri (bulunduysa)
- Toplam kaç istek harcandı (Çekici.istatistik'i yazdır)
- Tam evren için tahmini istek sayısı ve bu bütçeyle süre tahmini
- playwright gerekiyor mu: EVET/HAYIR + gerekçe
- Bulunamayan/kararsız kalan noktalar

BütçeAşıldı alırsan bütçeyi yükseltme; ne kadarını ölçebildiysen onu raporla.
```

**Çıkış kriteri:** ✔ karşılandı.

</details>

---

## 1.1 — Evren çekimi · bütçe **5**

```
Görev: 746 şirketlik evreni kalıcı hale getir.

Bağlam: ROTA_KESFI_RAPORU.md §2. Rota, alan adları ve RSC yükünün yapısı
orada ölçülmüş durumda; yeniden keşfetme.

Yeni modül: katilim/evren.py
- sirketleri_getir(cekici) -> list[Sirket]
- Kaynak DOM tablosu DEĞİL, gömülü RSC yükündeki JSON:
  stockCode, kapMemberTitle, mkkMemberOid, cityName, relatedMemberTitle
- Sayısal id + slug, aynı satırın <a href>'inden:
  /tr/sirket-bilgileri/ozet/{id}-{slug}

DİKKAT — eşlemeyi konuma göre yapma. RSC yükü ile DOM tablosu iki ayrı
yapı; "ikisi de 746 kayıt, sırayla eşleşir" varsayımı CLAUDE.md kural 4'ün
ihlalidir. stockCode gibi içerikten gelen bir anahtar üzerinden eşle.
Eşleşmeyen satır varsa say ve raporla, sessizce düşürme.

- Sirket alanları: ticker, unvan, kap_member_uuid, kap_kfif_slug,
  sehir, pazar (şimdilik None), sektor (şimdilik None), mali_sektor_muaf
- mali_sektor_muaf, spec §0.4 listesinden unvan üzerinden türetilir:
  banka, aracı kurum, emeklilik, finansal kiralama, faktoring, menkul
  kıymet yatırım ortaklığı, sigorta, varlık yönetim. Holding ve GSYO
  MUAF DEĞİL. Belirsizse muaf işaretleme — None bırak ve el ile bakılacak
  listesine yaz. Yanlış muafiyet, şirketi sessizce panelden düşürür.

Kalıcılık: veri/evren/sirketler.csv (utf-8-sig). Önceki sürüm
veri/evren/arsiv/sirketler_{YYYYMMDD}.csv olarak saklanır — evren değişimi
(halka arz, kotasyon iptali) kendi başına sinyaldir.

CLI: python3 -m katilim.cli evren --yenile

Ek sonda (bütçe içinde, 2-3 istek): pazar bilgisi.
/tr/sirket-bilgileri/ozet/{id}-{slug} sayfasını 2-3 şirket için çek ve
"Yıldız Pazar / Ana Pazar / Alt Pazar" bilgisi orada mı bak. VARSA maliyeti
söyle (şirket başına 1 istek = +746) ama ÇEKME, bana getir. YOKSA alternatif
kaynak öner (BIST günlük bülten, endeks bileşen dosyaları) ve orada bırak.

Test: tests/test_evren.py — ağa çıkmaz, kaydedilmiş gövde parçası fixture
olur. En az: RSC ayrıştırma, stockCode ile href eşleme, eşleşmeyen satır,
muafiyet sınıflaması (banka=muaf, holding=muaf değil, belirsiz=None).
```

**Çıkış kriteri:** `sirketler.csv`'de 746 satır; her satırda ticker + uuid +
slug; muafiyeti belirsiz olanlar ayrı listede; pazar sondasının sonucu yazılı.

---

## 1.2 — Bildirim sorguları · bütçe **800**

> Eski 2.1 buraya taşındı. Pencere 1 yıl olduğu için "güncel" ve "geçmiş"
> aynı istekten çıkıyor; ayrı faz tutmanın anlamı kalmadı.

```
Görev: Her şirket için KAFİF bildirim kimliklerini topla.

Rota: /tr/bildirim-sorgu-sonuc?member={mkkMemberOid}&disclosureClass=DG
bildirim_id, satırın checkbox id niteliğinde (<input name="notification-
checkbox" id="1643242">). /tr/Bildirim/{id} linki YOK, onu arama.
KAFİF satırı: konu metni "Katılım Finansı İlkeleri Bilgi Formu";
Yıl ve Periyot ayrı sütunlarda.

Bu adım HTML formu İNDİRMEZ, yalnız kimlik listesi çıkarır. Sebep: kaç
form indireceğimizi bilmeden 1.4'ün bütçesini konuşamayız.

ÜÇ ZORUNLU DAVRANIŞ:

1. Boş sonuç ≠ okunamayan sayfa (CLAUDE.md kural 7). Ayıklayıcı üç durumu
   ayırt etsin: (a) tablo dolu, (b) sunucunun bastığı "Bildirim bulunamadı",
   (c) beklenen çıpaların hiçbiri yok. (c) HATA FIRLATIR, boş liste dönmez.
   Rota keşfindeki iki ölçüm hatası da tam buradan çıktı.

2. disclosureClass=DG doğrulaması. Filtrenin KAFİF kaybettirmediği yalnız
   2 şirkette görüldü. Rastgele 10 şirkette filtreli ve filtresiz sayımı
   karşılaştır; DG dışında KAFİF satırı çıkarsa filtreyi bırak ve bana söyle.
   (Bu 10 ekstra istek bütçeye dahil.)

3. 404 ve boş sonuç da önbelleklenir (negatif önbellek). Yoksa muaf ve
   beyansız şirketler her koşuda yeniden sorgulanır.

Kalıcılık: veri/evren/bildirim_gecmisi.csv
(ticker, bildirim_id, yil, periyot, gonderim_ts, konu, indirildi_mi)

Çıktı raporu: kaç şirket × kaç KAFİF, dağılım (0/1/2/3+ form), en eski ve
en yeni gonderim_ts, KAFİF'i hiç olmayan şirket sayısı, 1.4 için gereken
form sayısı ve istek karşılığı.
```

**Çıkış kriteri:** `bildirim_gecmisi.csv` dolu; DG filtresi 10 şirkette
doğrulanmış; hata ile boş sonuç kodda ayrı; 1.4'ün gerçek maliyeti ölçülmüş.

---

## 1.3 — 20/20 parser kapısı · bütçe **30**

> Faz 0'ın devredilen çıkış kriteri. Bu kapı geçilmeden 1.4 koşulmaz;
> 2.600 isteği doğrulanmamış bir parser'a harcamak pahalı bir hata olur.

```
Görev: Parser'ı 20 farklı gerçek bildirimde doğrula.

Örneklem 1.2'nin çıktısından seçilir ve kolay olanı değil zoru kapsar:
- en az 3 solo (konsolide olmayan) finansal tablo
- en az 3 farklı sektör (sanayi, GYO, perakende)
- en az 2 küçük şirket (kalem sayısı az, tablolar kısmen boş)
- en az 2 tanesi 2025/6 Aylık (pencerenin en eski ucu — şablon farkı
  çıkacaksa orada çıkar)
- en az 1 düzeltme bildirimi varsa; is_duzeltme tespiti hiç doğrulanmadı

NOT: 2024 öncesi dönem bu pencereden çekilemiyor. Eski şablon (CLAUDE.md
kural 4'teki 3 soru -> 2 soru değişikliği) bu turda sınanamaz; kapsam
dışı olduğunu rapora yaz, "sınandı" sayma.

Her bildirim için: indir (önbellek öncelikli) -> veri/ham/ -> dogrula.

Kalıcı çıktı: tests/fixtures/pilot/ altına ayrıştırılmış JSON + beklenen
üç oran. tests/test_pilot.py bunları ağa çıkmadan regresyon olarak koşar.

Rapor: PILOT_20_RAPORU.md
- tablo: ticker | dönem | nitelik | şablon imzası | self-check | karar
- görülen farklı şablon imzalarının listesi
- self-check kalan her kayıt için TEŞHİS: parser mı bozuk, şablon mu farklı

Self-check kalırsa TOLERANS'ı gevşetme. `dok` ile sapmanın kaynağını bul.
Teşhis edemediğin sapmayı karantinada bırak ve raporla — bu bir bulgudur.
```

**Çıkış kriteri:** 20/20 self-check GEÇTİ, veya geçmeyen her kayıt için
gerekçe yazılı ve karantinada. `tests/test_pilot.py` yeşil.

---

## 1.4 — Tam evren form çekimi · bütçe **2.600**

> **Zaman duyarlı.** Sorgu penceresi kayıyor: bugün erişilebilen en eski
> bildirim yarın erişilemez. Bu adım ertelendikçe panel derinliği kalıcı
> olarak kaybediliyor.

```
Görev: 1 yıllık pencerede bulunan TÜM KAFİF formlarını indir ve panele bas.

Ön koşul: 1.3 geçti (20/20). Geçmediyse başlama.

Kapsam kararı verildi: en güncel form değil, PENCEREDEKİ HER ŞEY.
Gerekçe: Faz 2 bloke; bu pencere şu an sahip olabileceğimiz tüm tarih.
Şirket başına ~2-3 form, ~2.600 istek, ~2 sa 20 dk.

Yeni modül: katilim/toplayici.py
- formlari_topla(bildirim_gecmisi, cekici) -> list[KafifBildirim]
- İdempotanlık bildirim_id üzerinden (sha256 ÜZERİNDEN DEĞİL — markup
  istekten isteğe değişiyor, rota keşfi §4)
- KAFİF'i olmayan şirket sessizce atlanmaz: durum='BEYAN_YOK'.
  Muaf olan ile beyan vermeyen ayrı kayıtlanır; ayırt edilemiyorsa
  'AYIRT_EDILEMEDI' olarak işaretle, ikisinden birini varsayma.
- Ticker artık dosya adından tahmin edilmiyor, evren tablosundan geliyor
  (OKUBENI.md "bilinen açıklar" maddesi kapanır)

ARŞİV KURALI: veri/ham/ ve veri/onbellek/ bu adımdan sonra bir önbellek
değil, tek kopyası olan tarihsel arşivdir. Temizleme komutu YAZMA,
--zorla ile toplu yeniden çekme YAPMA.

Uzun koşu disiplini: ilerlemeyi her 50 istekte diske yaz. Koşu yarıda
kesilirse kaldığı yerden devam etsin, baştan başlamasın.

Çıktı:
- veri/panel/snapshot_{YYYYMMDD}.csv — ticker, yıl, periyot, üç oran,
  karar, red kodları, self-check, bildirim_id, gonderim_ts
- TOPLAMA_RAPORU.md — şirket/bildirim sayıları, BEYAN_YOK, karantina,
  harcanan istek, karar dağılımı, şablon imzası dağılımı
```

**Çıkış kriteri:** Muaf olmayan her şirket için ya en az bir kayıt ya
`BEYAN_YOK`/`AYIRT_EDILEMEDI` işareti var. Karantina oranı raporlanmış.
Arşiv bütünlüğü: `bildirim_gecmisi.csv`'deki her `indirildi_mi=True` satırın
karşılığı diskte mevcut.

---

# FAZ 2 — Tarihsel Derinlik

**Spec çıkış kriteri:** KAFİF başlangıcından bugüne panel dolu; şablon
versiyonları ayrıştırılmış.

> **Bu faz bloke (5 Ağu 2026).** KAP bildirim sorgusu 1 yıldan geriye
> gitmiyor; `fromDate/toDate`, `year`, `startDate/endDate` üçü de yok
> sayılıyor (rota keşfi §5). Faz 1.4 pencerenin tamamını topluyor — yani
> Faz 2'nin görevi artık "geri doldurmak" değil, **pencereyi genişletecek
> bir yol olup olmadığını sınamak.**

## 2.0 — Tarihsel derinlik keşfi · bütçe **30**

> Ölçüm turu. Çıktısı kod değil, bir karar.

```
Görev: 1 yıllık pencerenin ötesine geçen bir yol var mı, sistematik dene.

Betik: arac/derinlik_kesfi.py (tek seferlik, üretim kodu değil).
HızSınırlayıcı(min_aralik=2.0, jitter=1.0, oturum_butcesi=30).
Referans şirket: THYAO (4028e4a140f2ed720140f376bebb01a7). Bilinen taban:
filtresiz 98 kayıt, DG ile 12, en eski 05.08.2025 19:15 — ölçüm 05.08.2026.

ÖNCE BUNU YAP — tek istek, en yüksek bilgi değeri:

0. Pencere kayıyor mu? THYAO sorgusunu BUGÜN yeniden çek (--zorla, önbelleği
   atla) ve en eski kaydın tarihine bak.
   - Hâlâ 05.08.2025 ise pencere SABİT bir arşiv sınırı; aciliyet yok.
   - 05.08.2025 kaydı düşmüş, en eskisi ileri kaymışsa pencere KAYIYOR:
     her gün bir gün kaybediyoruz, 1.4 zaman duyarlı demektir.
   Sonucu tek cümleyle bana söyle; kalan sondalara ondan sonra geç.

Sonra denenecekler — her biri için "kayıt sayısı ve en eski tarih değişti mi":

1. "Detaylı Sorgulama" sayfasının FORM GÖVDESİ. Sayfayı çek, formun
   action'ını, method'unu ve gerçek alan adlarını oku. GET parametresi
   tahmin etmek yerine formun kendi söylediği adları kullan — önceki turda
   üç tarih parametresi tahmin edilmişti ve üçü de yok sayıldı.
2. Sayfalama: page, pageNumber, index, offset, size, rowCount.
   Sayfalama varsa pencere sınırı aslında KAYIT sınırı olabilir.
3. Sıralama tersine çevrilebiliyor mu (sort/order/direction)? Ters sıra
   pencerenin öbür ucunu açabilir.
4. Şirket özet sayfasının bildirim sekmesi: /tr/sirket-bilgileri/ozet/
   {id}-{slug} — ayrı bir bildirim listesi sunuyor mu?
5. /tr/kfif/{id}-{slug} sayfasında dönem seçici var mı? (Sayfanın kendisi
   veri kaynağı olarak YASAK — kural değişmedi. Burada yalnız geçmiş
   bildirim KİMLİKLERİNE link veriyor mu diye bakılıyor. Kimlik verirse
   formlar /tr/Bildirim/{id} rotasından çekilir.)
6. bildirim_id kaba kuvvet DENENMEZ. Bilinen id'lerin (1472632, 1566002,
   1643241) aralığından bir dizi tahmin etmek KAP'a rastgele yük bindirir
   ve nazik davranma ilkesini (spec §3.2) ihlal eder.

Çıktı: DERINLIK_KESFI_RAPORU.md
- sonda 0'ın sonucu: pencere sabit mi kayıyor mu (ve 1.4 acil mi)
- her deneme: URL/gövde, kayıt sayısı, en eski tarih, sonuç
- pencere sabit mi kayıyor mu
- BULUNDU ise: rota, maliyet tahmini, ulaşılabilen en eski tarih
- BULUNAMADI ise: bunu açıkça yaz. Negatif sonuç da sonuçtur; Faz 2
  kapanır ve derinlik zamanla birikir.
```

**Çıkış kriteri:** Altı yolun her biri denenmiş ve sonucu yazılı; "pencere
genişletilebiliyor / genişletilemiyor" kararı verilmiş; kayma ölçülmüş.

---

## 2.1 — Geri doldurma *(koşullu)*

> **Yalnızca 2.0 bir yol bulduysa koşulur.** Bulunamadıysa bu adım atlanır,
> 2.2'ye geçilir.

```
Görev: 2.0'da bulunan rotayla pencere öncesi bildirimleri indir.

Ön koşul: 2.0 raporu + bütçe onayım. Maliyet 1.4'ün üstüne binecek;
çalıştırmadan önce toplam istek sayısını bana söyle.

Kurallar 1.4 ile aynı: bildirim_id ile idempotanlık, negatif önbellek,
50 istekte bir ilerleme kaydı, arşiv silinmez.

Yeni risk: pencere öncesi bildirimler ESKİ ŞABLONLA verilmiş olabilir
(2024 revizyonu). Ayrıştırıcıyı bunlara uydurmak için gevşetme; tanınmayan
imza karantinaya gider ve 2.2'de ele alınır.
```

**Çıkış kriteri:** Erişilebilen en eski tarihe kadar panel dolu; yeni şablon
imzaları listelenmiş.

---

## 2.2 — Şablon versiyonlama

```
Görev: Elimizdeki tüm bildirimleri şablon versiyonlarına ayır.

Girdi: 1.4'ün (ve varsa 2.1'in) topladığı her şey.

Şablon versiyonlama — bu adımın asıl işi:
- Her bildirimin şablon imzası zaten çıkarılıyor (4A|4B|...|S3 formatı).
- Farklı imzaları grupla, her gruba bir versiyon etiketi ver
  (SABLON_2023, SABLON_2024_07, ...). Etiketleri gözlemden türet,
  tahmin etme.
- Bilinen imzaya uymayan bildirim ayrıştırılmaya ZORLANMAZ: karantinaya
  alınır ve yeni imza olarak raporlanır. Ayrıştırıcıyı "çalışsın diye"
  gevşetmek, sessiz veri bozulmasının tam da kendisidir.
- Her yeni imza için: hangi tablolar var/yok, kalem sayıları nasıl değişmiş.

Tek imza çıkarsa bu da bir sonuçtur: 1 yıllık pencere tek şablon
revizyonuna denk geliyor demektir. "Şablon versiyonlama gerekmedi" diye
yazılır — modül yine de kalır, çünkü sonraki revizyonda devreye girecek.

Çıktı:
- veri/panel/tarihsel_ham.csv — tüm dönemlerin ayrıştırılmış kayıtları
- SABLON_VERSIYONLARI.md — imza -> etiket -> ilk/son görülme tarihi ->
  hangi alanlar farklı
- Karantina listesi: bildirim_id, imza, sebep
```

**Çıkış kriteri:** Her bildirim bir şablon versiyonuna atanmış; karantina
oranı <%5 veya her karantina kaydı gerekçeli. Panelin fiili derinliği
(en eski dönem) raporda yazılı.

---

## 2.3 — Düzeltme mantığı

```
Görev: Aynı (ticker, yıl, periyot) için birden fazla bildirim durumunu çöz.

Spec §3.2: en geç gonderim_ts kazanır, ama eskisi SİLİNMEZ — düzeltme
olayının kendisi bir sinyaldir.

katilim/toplayici.py'ye ekle:
- duzeltmeleri_coz(kayitlar) -> (gecerli_kayitlar, duzeltme_olaylari)
- Düzeltme olayı: ticker, dönem, ilk_gonderim_ts, duzeltme_gonderim_ts,
  değişen alanlar (özellikle: üç oran ve 13 beyandan hangileri değişti)
- Bir beyanın HAYIR'dan EVET'e (veya tersi) döndüğü düzeltme özellikle
  işaretlensin; bu, uygunluk kararını doğrudan çevirir.

is_duzeltme tespiti şu an sayfa metninde "düzeltme" araması yapıyor ve
hiç doğrulanmadı (OKUBENI.md bilinen açıklar). 1.3'te bulduğun gerçek
düzeltme bildirimiyle bu tespiti doğrula veya düzelt.

Look-ahead disiplini (spec §5.1): düzeltilmiş kaydın geçerlilik başlangıcı
DÜZELTMENİN gonderim_ts'i, orijinalinki değil. Panelde her ikisi de
kendi zaman damgasıyla durur.

Çıktı: veri/panel/duzeltme_olaylari.csv + kısa bulgu notu
(kaç düzeltme, kaçı kararı çevirmiş).
```

**Çıkış kriteri:** Her (ticker, dönem) için tek geçerli kayıt seçilmiş;
düzeltme olayları ayrı tabloda; karar çeviren düzeltmeler sayılmış.

---

# FAZ 3 — Karar Motoru ve Panel

**Spec çıkış kriteri:** Her (ticker, dönem) için karar + gerekçe kodu.

## 3.1 — Tolerans durum makinesini panele bağla

```
Görev: seri_degerlendir()'i tarihsel panele uygula.

karar.py'de seri_degerlendir() var ve şirket bazında tolerans taşıyor (H4).
Şimdi gerçek tarihsel veriye bağlanacak.

Yeni modül: katilim/panel.py
- panel_uret(kayitlar, evren) -> her (ticker, yıl, periyot) için
  uygunluk_karar satırı (spec §1.5 şeması)
- Şirket bazında kronolojik sıra; tolerans durumu dönemler arasında taşınır
- BELIRSIZ kararı tolerans durumunu SIFIRLAMAZ (karar.py:203 mevcut
  davranışı; panelde de korunmalı)
- Zincirde boşluk varsa (bir dönem BEYAN_YOK): tolerans durumu ne olacak?
  Bu spec'te tanımlı değil. Kararı bana getir, kendi başına seçme.
  Geçici davranış: durum taşınır, satır 'ZINCIR_BOSLUGU' ile işaretlenir.

Çıktı: veri/panel/panel.csv (utf-8-sig)
Sütunlar: ticker, yil, periyot, gecerlilik_baslangic, karar, red_kodlari,
gelir_orani, varlik_orani, borc_orani, onceki_donem_tolerans,
sablon_versiyon, self_check, bildirim_id

Test: tests/test_panel.py — sentetik bir 4 dönemlik zincir kur:
temiz -> toleransta -> temiz -> toleransta. Ve: toleransta -> farklı
kriterde aşım -> UYGUN_DEGIL olduğunu doğrula (H4'ün kod içindeki hali).
```

**Çıkış kriteri:** `panel.csv` her (ticker, dönem) için karar içeriyor;
tolerans zinciri testlerle doğrulanmış; zincir boşluğu politikası
belgelenmiş.

---

## 3.2 — Belirsiz bant ve piyasa değeri paydası

```
Görev: %33-36,3 bandındaki kararlar için ikinci hesap (spec §0.2, §2.2).

Sorun: KAFİF paydayı toplam varlık (5H) alıyor; BIST rehberi
max(ort. PD, toplam varlık) diyor. Daha büyük payda daha küçük oran
üretir, yani KAFİF oranı ≥ BIST oranı.

Sonuç: KAFİF oranı %33 altındaysa BIST kriteri kesin sağlanır (güvenli).
%33-36,3 bandında karar BELIRSIZ ve PD ile ikinci hesap gerekir.

Bu H3 hipotezine dayanıyor ve DOĞRULANMADI. Kodla ama şöyle kodla:
- Hipoteze bağlı her hesap, kaynağında 'H3' etiketiyle işaretlensin
- Panelde ayrı bir sütun: pd_ile_hesaplandi (BOOLEAN)
- Faz 4'te H3 yanlış çıkarsa hangi satırların etkilendiği tek sorguyla
  bulunabilsin

Ortalama PD verisi: kaynağı henüz seçilmedi. Önce kaynak seçeneklerini
listele (BIST günlük bülten, yfinance, mevcut swing trading sistemimin
veri katmanı) ve bana sor. Kaynak seçmeden hesabı yazma; hangi tarih
aralığının ortalaması alınacağı da (24 ay? dönem sonu?) belirsiz —
bu iki soruyu birlikte getir.

Bu adımın kod çıktısı: bant tespiti + BELIRSIZ işaretleme + boş bırakılmış
pd hesabı arayüzü. PD verisi bağlanınca doldurulacak.
```

**Çıkış kriteri:** Bant içine düşen kayıtlar `BELIRSIZ` + `H3` etiketli;
PD kaynağı sorusu bana sorulmuş; panelde `pd_ile_hesaplandi` sütunu var.

---

## 3.3 — Manuel override katmanı

```
Görev: Kural motorunun yakalayamayacağı vakalar için denetlenebilir bir
elle müdahale mekanizması.

Gerekçe (spec §6): md. 1.5 (insan hakları / kamuoyu açıklaması) takdire
dayalı; ayrıca beyan hatası ihtimali var.

Tasarım:
- veri/override.csv — ticker, yil, periyot, yeni_karar, gerekce, kaynak_url,
  ekleyen, tarih
- panel_uret() override'ı UYGULAR ama ASLA gizlemez: panelde
  karar_kaynagi sütunu (MOTOR | OVERRIDE) ve orijinal motor kararı
  ayrı sütunda korunur
- Gerekçesi veya kaynak_url'i boş override kabul edilmez, hata verir

Bu katman Faz 4 mutabakatında da kullanılacak: uyuşmazlık bulunduğunda
önce override ile mi kapatılacak yoksa kural mı revize edilecek — bu ayrım
kaydedilmiş olmalı.

Test: override'lı ve override'sız aynı kaydın panelde nasıl göründüğü.
```

**Çıkış kriteri:** Override uygulanıyor, izlenebilir, gerekçesiz override
reddediliyor.

---

# FAZ 4 — Mutabakat

> **Spec §4: "Faz 4 pazarlık konusu değil."** Bu fazdan önce üretilen panel
> araştırma çıktısıdır, karar dayanağı değildir.

**Spec çıkış kriteri:** Uyuşmazlık oranı <%5; her uyuşmazlık ya parser
hatası ya H1-H4 revizyonu olarak açıklanmış.

## 4.1 — Resmî referans verisini topla

```
Görev: XKTUM bileşen listelerini tarihsel olarak topla.

Kaynaklar (DEVIR_NOTU §2.1):
- Borsa İstanbul "BIST Katılım Endeksleri Dönemsel Değişiklikler" PDF'leri
  — geriye dönük etiketleme için en temiz ikincil kaynak
- XKTUM güncel bileşen listesi

PDF ayrıştırma için pdf becerisini kullanabilirsin.

Çıktı: veri/referans/xktum_bilesenler.csv
(ticker, donem_baslangic, donem_bitis, endekste_mi, kaynak_dosya)

Dönem eşlemesi kritik: endeks yürürlük tarihi 1 Mayıs / 1 Ekim; KAFİF
dönemi ise 6 Aylık / Yıllık bilanço. Hangi KAFİF döneminin hangi endeks
dönemine denk geldiğini AÇIKÇA belgele — mutabakatın tamamı bu eşlemeye
dayanıyor ve yanlış eşleme sahte uyuşmazlık üretir.

Ham PDF'leri veri/referans/ham/ altında sakla.
```

**Çıkış kriteri:** En az 4 endeks dönemi için bileşen listesi var; KAFİF
dönemi ↔ endeks dönemi eşlemesi yazılı.

---

## 4.2 — Mutabakat koşumu

```
Görev: Kendi kararlarımızı resmî listeyle karşılaştır.

Yeni modül: katilim/mutabakat.py
- karsilastir(panel, referans, donem) -> uyusmazlik listesi
- Dört hücre: biz UYGUN + BIST içeride (doğru), biz UYGUN_DEGIL + BIST
  dışarıda (doğru), biz UYGUN + BIST dışarıda (YANLIŞ POZİTİF —
  en tehlikelisi), biz UYGUN_DEGIL + BIST içeride (yanlış negatif)

Yanlış pozitifler ayrı ele alınır: uygunsuz bir şirketi uygun göstermek,
uygun bir şirketi kaçırmaktan pahalıdır.

Her uyuşmazlık için otomatik ön teşhis:
- self-check kalmış mı? -> parser şüphesi
- karar hangi kapıda verilmiş? -> ilgili hipotez şüphesi (G4 -> H1,
  G2 -> H2, G5-G7 -> H3, tolerans zinciri -> H4)
- BEYAN_YOK mu? -> kapsam sorunu
- BELIRSIZ mi? -> veri eksikliği

CLI: python3 -m katilim.cli mutabakat --donem 2025-10

Çıktı: MUTABAKAT_{donem}.md
- karışıklık matrisi + uyuşmazlık oranı
- her uyuşmazlık: ticker, bizim karar, bizim gerekçe, BIST durumu, ön teşhis
- hipotez bazında gruplandırılmış özet
```

**Çıkış kriteri:** En az bir dönem için mutabakat raporu üretildi;
uyuşmazlık oranı ölçüldü.

---

## 4.3 — Hipotez revizyonu

```
Görev: 4.2'nin bulgularıyla H1-H4'ü karara bağla.

Her hipotez için üç sonuçtan biri:
1. DESTEKLENDİ — kaç gözlemle, hangi dönemde
2. REDDEDİLDİ — karşı örnek(ler), yerine geçecek kural
3. KARARSIZ — neden yeterli gözlem yok

Reddedilen her hipotez için:
- spec §2.3 güncellenir
- karar.py'deki ilgili kural güncellenir
- CLAUDE.md'nin "Doğrulanmamış varsayımlar" bölümü güncellenir
- panel yeniden üretilir, mutabakat yeniden koşulur
- HEPSİ AYNI COMMIT'TE (CLAUDE.md kuralı)

Uyuşmazlık oranı hâlâ >%5 ise: modellenmemiş bir kriter var demektir.
Uyuşmazlıkların ortak özelliğini ara (sektör? pazar? şirket büyüklüğü?
belirli bir beyan alanı?) ve bulgunu H5 olarak spec'e ekle — kod
değişikliğine geçmeden önce bana getir.

Çıktı: HIPOTEZ_KARARLARI.md + güncellenmiş spec/CLAUDE.md/karar.py
```

**Çıkış kriteri:** Her hipotez için karar yazılı; uyuşmazlık <%5 veya
kalan uyuşmazlığın kaynağı isimlendirilmiş.

---

# FAZ 5 — Olay Akışı ve Ölçüm

**Spec çıkış kriteri:** KAFİF gönderim tarihi bir katalizör olayı olarak
sisteme bağlanmış.

> **Beklenti değil hipotez.** Çıkış etkisinin var olduğunu varsaymıyoruz,
> ölçüyoruz. Etki bulunamazsa modül sinyal değil yalnız risk filtresi kalır.

## 5.1 — Olay serisi üretimi

```
Görev: Panelden look-ahead'sız olay serisi çıkar.

Ön koşul: Faz 4 tamamlandı. Öncesinde bu seriyi trading sistemine bağlama.

katilim/olay.py
- Olay tipleri: UYGUNLUK_KAYBI, UYGUNLUK_KAZANIMI, TOLERANSA_DUSUS,
  TOLERANSTAN_CIKIS, KILPAYI_UYARI (limite 0,5 puandan yakın — THY'nin
  %4,92'si bu kategorinin gerekçesi)
- Her olayın zamanı = KAFİF gonderim_ts (spec §5.1). Bilanço dönemi DEĞİL,
  endeks yürürlük tarihi DEĞİL.
- Ayrıca ikinci bir zaman sütunu: endeks_yurutluk_tarihi (1 May / 1 Eki).
  İkisi arasındaki pencere ölçümün konusu.

Look-ahead denetimi bu modülün testinin ASIL konusu:
tests/test_olay.py içinde, her olay satırı için üretiminde kullanılan
tüm girdilerin zaman damgasının olay zamanından küçük veya eşit olduğunu
doğrulayan bir kontrol yaz. Bu testi gözden geçirmeden geçme.

Çıktı: veri/panel/olaylar.csv
(ticker, olay_tipi, olay_ts, endeks_yururluk_ts, onceki_karar, yeni_karar,
red_kodlari, bildirim_id)
```

**Çıkış kriteri:** `olaylar.csv` üretildi; look-ahead denetim testi yeşil.

---

## 5.2 — Getiri dağılımı çalışması

```
Görev: Olayların fiyat etkisini ÖLÇ (spec §5.3, DEVIR_NOTU §2.5).

Ölçülecek üç soru:
1. XKTUM'dan çıkan hisselerin getiri dağılımı — (a) KAFİF yayın tarihi
   ve (b) endeks yürürlük tarihi etrafında. Pencere: -20/+20 işlem günü.
2. Endekse GİRENLERDE simetrik etki var mı?
3. Etkinin katılım fonu sahiplik yoğunluğuyla ilişkisi var mı?

Fiyat verisi: mevcut swing trading sistemimin veri katmanından mı gelecek,
ayrı mı çekilecek? Bunu bana sor, varsayma.

Yöntem disiplini:
- Piyasa/endeks getirisine göre düzeltilmiş getiri (ham getiri değil)
- Örneklem büyüklüğünü her tabloda yaz; n<10 ise sonuç YORUMLANMAZ,
  yalnız raporlanır
- Etki bulunamazsa bunu açıkça yaz. Negatif sonuç da sonuçtur ve
  bu modülün risk filtresine indirgenmesi demektir.

Çıktı: OLAY_CALISMASI.md — dağılım tabloları, örneklem sayıları,
ve tek cümlelik sonuç: "etki var / yok / veri yetersiz".
```

**Çıkış kriteri:** Üç sorunun her biri için ölçüm sonucu ve örneklem
büyüklüğü yazılı; sonuç cümlesi net.

---

## 5.3 — Trading sistemine bağlama

```
Görev: Uygunluk modülünü swing trading sistemine bağla.

Ön koşul: 5.2'nin sonucu. Sonuca göre iki farklı entegrasyon:

Etki BULUNDUYSA: olay akışı katalizör sinyali olarak bağlanır;
pozisyon boyutuna etkisi 5.2'deki etki büyüklüğünden türetilir.

Etki BULUNMADIYSA: yalnız risk filtresi. Katılım uygunluğu kaybı olan
hisse tarama evreninden çıkarılır veya uyarı etiketi alır; sinyal
üretmez. Bu daha muhtemel sonuç; öyleyse basit tut.

Her iki durumda da arayüz aynı olsun:
- katilim.api.uygunluk_durumu(ticker, tarih) -> Karar
  Verilen tarihte BİLİNEN en güncel karar (look-ahead yok:
  gecerlilik_baslangic <= tarih olan en geç kayıt)
- katilim.api.olaylar(ticker, baslangic, bitis) -> list[Olay]

Bu iki fonksiyon dışında trading sistemi panelin iç yapısına bağlanmasın.
```

**Çıkış kriteri:** `katilim.api` iki fonksiyonu sağlıyor; look-ahead'sizlik
test edilmiş; entegrasyon biçimi 5.2 sonucuyla tutarlı.

---

## Faz bağımlılıkları

```
1.0 ✔ ─► 2.0 ─► 1.1 ─► 1.2 ─► 1.3 ─► 1.4 ─► 2.2 ─► 2.3 ─► 3.1 ─► 3.2 ─► 3.3
           └──► 2.1 (koşullu) ──────────────►┘                            │
                                                                          ▼
                                      4.1 ─► 4.2 ─► 4.3 ─► 5.1 ─► 5.2 ─► 5.3
```

**2.0 öne alındı (6 Ağu 2026).** Planda başta 1.3'ten sonraydı; sıra
değişti çünkü 2.0'ın cevabı `toplayici.py`'nin tasarımını belirliyor —
"tek sabit pencere" ile "keyfi derinlik + sayfalama" aynı modül değil.
Modülü iki kez yazmak, 30 isteği harcamaktan pahalı. 1.1 (5 istek) 2.0'dan
bağımsız, sırası önemsiz.

2.1 yalnız 2.0 bir yol bulursa devreye girer. 4.1 (XKTUM referans verisi)
Faz 3 ile paralel başlatılabilir.

**Kritik yol 1.4'ten geçiyor ve zaman duyarlı** — sorgu penceresi kayıyorsa
geciken her gün panel derinliğinden düşüyor.

## Karar noktaları — otomatikleştirilmeyecek

Bu noktalarda Claude Code durup sormalı; kendi başına seçmemeli:

| Nerede | Karar | Durum |
|---|---|---|
| 1.0 sonrası | requests mi playwright mi | ✔ requests |
| 1.0 sonrası | adım bütçeleri | ✔ 5 / 800 / 30 / 2.600 |
| 1.1 | Pazar bilgisi kaynağı ve maliyeti | açık |
| 1.2 | `disclosureClass=DG` KAFİF kaybettiriyorsa ne yapılacak | açık |
| 1.4 | Koşu kapsamı (güncel mi tüm pencere mi) | ✔ tüm pencere |
| 2.0 sonrası | Derinlik bulunduysa ek bütçe; bulunmadıysa Faz 2 kapanır | açık |
| 3.1 | Zincir boşluğunda tolerans durumu ne olur | açık |
| 3.2 | Ortalama PD kaynağı ve hangi dönemin ortalaması | açık |
| 4.3 | Hipotez reddi ve yerine geçecek kural | açık |
| 5.2 | Fiyat verisi kaynağı | açık |
| 5.3 | Sinyal mi risk filtresi mi |
