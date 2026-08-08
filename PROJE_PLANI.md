# Proje Planı — Faz Promptları

Bu belge, her fazın Claude Code'a verilecek promptlarını içerir. Kaynaklar:
`CLAUDE.md` (değiştirilemez kurallar), spec v0.1 (§4 faz tanımları),
`DEVIR_NOTU_2026-08-05.md` (alan bulguları ve teknik durum).

**Durum (7 Ağu 2026):** Faz 0 ✔ (THY 2025/Yıllık, self-check GEÇTİ) ·
1.0 rota keşfi ✔ · 1.1 evren ✔ (795 ticker / 746 tüzel kişi) ·
2.0 derinlik keşfi ✔ (BULUNAMADI, pencere kayıyor) ·
**1.2 bildirim sorguları ✔ — 1.276 KAFİF kimliği toplandı.**
**1.4a form arşivi ✔** (1.276/1.276 form) · **1.3 parser kapısı ✔**
(1.276 formda ayrıştırma hatası 0, 22 sapmanın 22'si teşhisli).
106 test geçiyor. Sıradaki: **1.4b** (ayrıştırma + panel, ağ isteği yok).

**1.1b ertelendi ve 1.3'ün kapısı yer değiştirdi (7 Ağu).** Şirket özet
sayfaları kaymıyor, ne zaman çekilse aynı veriyi veriyor; KAFİF formları
kayıyor. Bu yüzden zaman duyarlı olmayan her şey arşiv çekiminin arkasına
alındı. Sıra: **1.2 → 1.4a (arşiv) → 1.3 (20/20) → 1.4b (panel) → 1.1b →
2.0b → 4.0**.

> **1.4 artık zaman duyarlı ve bu ölçüldü.** Pencere 1 gün/gün kayıyor;
> 5→7 Ağustos arasında THY'nin 2025/6 Aylık KAFİF'i erişilemez oldu
> (@DERINLIK_KESFI_RAPORU.md §2). 6 Aylık dalgası ağustos-eylülde
> yayımlandığı için gecikilen her hafta o dalgadan bir dilim götürüyor.
>
> **1.2'nin ölçümü bunu yumuşattı (7 Ağu, n=1).** Kayan şey **keşif**:
> pencereden düşen 1472632 bugün `/tr/Bildirim/{id}`'den indi, self-check
> geçti (@BILDIRIM_GECMISI_RAPORU.md §5). Kimlik `bildirim_gecmisi.csv`'ye
> yazıldıysa form sonra da inebiliyor — yani **asıl zaman duyarlı adım
> 1.2'ydi ve bitti.** Bu, 1.4a'nın önüne 1.1b'yi almayı mümkün kılar ama
> gözlem tek bildirime dayanıyor; sırayı değiştirmeden önce birkaç kimlikle
> daha sınanmalı.
>
> **Karar (7 Ağu): sıra değişmiyor, 1.4a önce koşuyor.** Gerekçe maliyet
> asimetrisi: 1.276 form ≈ 68 dakika, hipotez doğruysa bu 68 dakikanın
> kaybı yok; hipotez yanlışsa 1.1b'yi öne almanın bedeli telafi edilemez.
> Üstelik **1.4a koşusu hipotezi bedavaya sınıyor**: arşivde pencere dışı
> kimlikler zaten var, hepsi inerse gözlem n=1'den n=1.276'ya çıkıyor.
> Ayrı bir sonda yazmaya gerek yok, 1.4a raporunda bir bölüm yeter.

Planın şeklini değiştiren bulgular:

| Nereden | Ne değişti |
|---|---|
| 1.0 | Eski 1.2 (kimlik eşlemesi) iptal — iki kimlik aynı istekten çıkıyor |
| 1.0 | Eski 2.1 (bildirim geçmişi) 1.2'ye taşındı — pencere 1 yıl |
| 1.0 | Faz 2 bloke; önüne 2.0 derinlik keşfi eklendi |
| 1.1 | Evren 795 ticker / 746 tüzel kişi — sorgu ekseni uuid, panel ekseni ticker |
| 1.1 | Pazar sondası endeks üyeliğini de buldu → 1.1b ve 4.0 açıldı |
| 2.0 | Pencere genişletilemiyor → 2.1 atlandı; pencere kayıyor → 1.4 acil |

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

## 1.1 — Evren çekimi ✔ **BİTTİ (6 Ağu 2026)**

`katilim/evren.py`, 23 test, `veri/evren/sirketler.csv` kalıcı.

```
795 pay kodu / 746 tüzel kişi      slug eşleşen: 795/795
muafiyet: 150 muaf · 612 değil · 33 belirsiz (el ile bakılacak)
```

**Rota keşfi raporunun bir ölçümü düzeltildi:** `stockCode` virgüllü çoklu
kod taşıyabiliyor (`"ALBRK, ALK"`), 45 tüzel kişide böyle. "746 benzersiz
stockCode" dize olarak doğru, pay kodu olarak değildi. Sonuç: **evren 795
ticker, 746 tüzel kişi.**

> **Aşağı akışa taşınan sonuç — panelin iki ekseni var.**
> KAFİF ve dolayısıyla **karar tüzel kişi düzeyinde** (bir beyan, tek uuid).
> Endeks üyeliği ise **pay kodu düzeyinde**: XKTUM'a girmek için likidite ve
> fiili dolaşım şartları da var ve bunlar kod bazında değerlendiriliyor.
> Aynı tüzel kişinin bir kodu endekste olup diğeri olmayabilir.
>
> Bu yüzden: 1.2/1.4 **uuid başına** çeker (746, 795 değil); panel **ticker
> başına** satır tutar; mutabakat (4.0/4.2) ticker düzeyinde yapılır ve
> "aynı uuid'in kodları arasında ayrışma" ayrı bir uyuşmazlık sınıfıdır —
> kriter kaynaklı değil likidite kaynaklıdır ve **H1–H4'ün reddi sayılmaz.**

*1.1 promptu arşiv olarak duruyor.*

<details>
<summary>1.1 promptu (arşiv)</summary>

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

**Çıkış kriteri:** ✔ karşılandı (795 satır, 746 uuid).

</details>

---

## 1.1b — Şirket özet sayfaları · bütçe **800**

> Pazar sondası beklenenden fazlasını buldu; ayrı adım oldu.

```
Görev: 746 tüzel kişinin özet sayfasını çek, üç alanı evrene bas.

Rota: /tr/sirket-bilgileri/ozet/{id}-{slug} — sunucu tarafında render
ediliyor, 1.1'in sondasında 3 şirkette (THYAO, ACSEL, ASELS) doğrulandı.

Çekilecek alanlar:
- "Sermaye Piyasası Aracının İşlem Gördüğü Pazar" -> pazar
  (YILDIZ PAZAR / ANA PAZAR / ALT PAZAR) — spec §0.4'ün XKTUM ön şartı
- "Şirketin Sektörü" -> sektor
- "Dahil Olduğu Endeksler" -> endeksler (liste)
  BIST KATILIM 30/50/100/TÜM üyeliği buradan çıkıyor. Bu alan 4.0'ın
  girdisi; ayrı bir sütuna değil, ayrı bir tabloya yaz:
  veri/evren/endeks_uyeligi.csv (ticker, endeks_adi, olcum_tarihi)
  DİKKAT: bu GÜNCEL üyelik, tarihsel değil. olcum_tarihi olmadan
  saklanırsa ileride nokta-zaman sanılır — tarih zorunlu alan.

İstek sayısı uuid başına 1 = 746 (795 değil; çoklu kodlu tüzel kişiler
aynı sayfayı paylaşıyor). ~40 dk. İlerlemeyi 50 istekte bir diske yaz,
koşu kesilirse kaldığı yerden devam etsin.

Sonra: 33 belirsiz muafiyeti sektör alanıyla yeniden değerlendir.
- Kapanabilenleri kapat, gerekçesini yaz.
- Kapanmayan kalırsa MUAF İŞARETLEME, belirsiz bırak. Yanlış muafiyet
  şirketi sessizce panelden düşürür; fazladan sorgulamak zararsızdır.
- KTLEV özel vaka: spec §0.4 "KAFİF doldurmuyor" diyor ama tasarruf
  finansman şirketleri muafiyet listesinde yazılı değil. Sektör alanı
  ne diyor, bak ve bana getir — çözüm ya spec §0.4'e madde eklemek ya
  da "muaf değil ama beyan vermiyor" diye üçüncü bir durum tanımlamak.
  Kendi başına seçme.

Test: pazar/sektör/endeks ayıklama, alanı olmayan sayfa (None kalmalı,
boş dize değil), 33 belirsizin yeniden sınıflaması.
```

**Çıkış kriteri:** 746 sayfa çekilmiş; `sirketler.csv`'de pazar ve sektör
dolu; `endeks_uyeligi.csv` ölçüm tarihiyle yazılmış; belirsiz muafiyet
sayısı düşmüş ve kalanlar gerekçeli.

---

## 1.2 — Bildirim sorguları ✔ **BİTTİ (7 Ağu 2026)**

Çıktı: `BILDIRIM_GECMISI_RAPORU.md`, modüller `katilim/bildirim.py` +
`katilim/rsc.py`. **651 istek / onaylı 800.** 643 tüzel kişi sorgulandı.

```
KAFIF_VAR 537 · KAFIF_YOK 101 · BOS_SONUC 5 · okunamayan 0 · hata 0
ticker satırı 1.280  ·  BENZERSİZ form 1.276  <- 1.4'ün maliyeti
```

| Bulgu | Etkisi |
|---|---|
| Pencereden düşen bildirim `/tr/Bildirim/{id}`'den **hâlâ iniyor** (n=1) | Kayan pencere **keşfi** öldürüyor, erişimi değil → 1.4'ün aciliyeti düştü |
| `periyot` alanı `3 Aylık`/`9 Aylık` da içeriyor | Panel kronolojisi `gonderim_ts` ile sıralanmalı; spec §1.2 güncellendi |
| 163 tekrar eden (ticker, yıl, periyot), 135 şirkette | RSC `isChanged` = `DUZENLENEN`/`DUZELTILEN` → 2.3'ün gerçek kaynağı |
| DG filtresi 10 şirkette daha doğrulandı (n=12) | Filtre korunuyor |
| 33 belirsiz muafiyetin **hepsi** KAFİF vermemiş | 1.1b'ye girdi; ama muaf ≠ beyansız, 1.4'te `AYIRT_EDILEMEDI` |
| İki sessiz veri kaybı hatası (RSC kaçış + parantez konumu) | `katilim/rsc.py` açıldı, 7 regresyon testi; evren çıktısı değişmedi |

**Sıra kısıtı gevşedi.** "1.2 biter bitmez 1.4a, araya 1.1b sokma" kuralı,
kimliklerin kaydedilmesiyle zorunluluk olmaktan çıktı — kimlik elde
olduğu sürece form sonra da inebiliyor. Yalnız bu gözlem **n=1**; 1.1b'yi
araya almadan önce birkaç kimlikle daha sınanmalı.

*1.2 promptu arşiv olarak duruyor.*

<details>
<summary>1.2 promptu (arşiv)</summary>

```
Görev: Her tüzel kişi için KAFİF bildirim kimliklerini topla.

Sorgu ekseni TİCKER DEĞİL UUID: 795 ticker var ama 746 tüzel kişi.
Çoklu kodlu şirketleri (ALBRK/ALK gibi) iki kez sorgulamak 45 gereksiz
istek ve aynı bildirimin iki kaydı demek. Muaf olmayan uuid'ler üzerinden
döngü kur, sonucu ticker'lara sonradan dağıt.

Rota: /tr/bildirim-sorgu-sonuc?member={mkkMemberOid}&disclosureClass=DG

Kaynak DOM DEĞİL, RSC yükü. 2.0'da ölçüldü: `disclosureBasic` nesnesi
disclosureIndex, publishDate, disclosureClass, year, period, title
alanlarını yapılandırılmış veriyor. Checkbox kazımaya (id niteliği)
gerek yok — o yol yedek katman olarak kalsın, birincil değil.
KAFİF satırı: title "Katılım Finansı İlkeleri Bilgi Formu".

Sayfalama döngüsü YAZMA. 2.0 ölçtü: sunucu bulduğu kaydın tamamını tek
sayfada basıyor (92=92), page/offset/size parametreleri yok sayılıyor.

Bu adım HTML formu İNDİRMEZ, yalnız kimlik listesi çıkarır. Sebep: kaç
form indireceğimizi bilmeden 1.4'ün bütçesini konuşamayız.

ZAMAN DUYARLI — GECİKTİRME. Pencere 1 gün/gün kayıyor (2.0 sonda 0).
Bu adım bittiği anda 1.4a başlamalı; araya 1.1b veya 1.3 sokma.

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

**Çıkış kriteri:** ✔ karşılandı — `bildirim_gecmisi.csv` 1.280 satır; DG
filtresi 10 şirkette doğrulandı; üç durum (dolu / boş / okunamadı) kodda ve
`sorgu_durumu.csv`'de ayrı; 1.4'ün maliyeti **1.276 istek** olarak ölçüldü.

</details>

---

## 1.3 — 20/20 parser kapısı ✔ **BİTTİ (8 Ağu 2026)**

Çıktı: `PILOT_20_RAPORU.md` · fixture `tests/fixtures/pilot/` (20 JSON) ·
`tests/test_pilot.py` (9 test). Betik `arac/pilot_20.py`. **Ağ isteği 0.**

**Kapı geçildi.** Örneklemde 13 GEÇTİ / 7 KALDI; KALAN 7'nin 7'si teşhisli.
Örneklem seçilmeden önce **arşivin tamamı** ayrıştırıldı:

```
1.276 form · ayrıştırma hatası 0 · self-check GEÇTİ 1.254 / KALDI 22 (%98,3)
22 sapmanın 22'si teşhis edildi -> açıklanmamış karantina YOK
```

| Bulgu | Etkisi |
|---|---|
| 19 sapmada **formun kendi 4E TOPLAM satırı kalemleriyle tutmuyor** | Parser doğru; kaynak veri tutarsız. Kural 3'ün var olma sebebi |
| 3 sapmada 4E=0 → oran tanımsız, form 0 basıyor | `None`≠0 korundu (kural 2'nin oran karşılığı) |
| **Tek şablon imzası** (1.276/1.276) | 2.2 tek etiket üretecek; **2024 öncesi şablon SINANMADI** |
| Her formda 55 kalem, 13/13 beyan | "Kısmen boş tablo" ölçütü satır sayısıyla ölçülemez; vekil: dolu kalem sayısı |
| **`is_duzeltme` doğrulandı**: 181/181, kaçırma 0 | OKUBENI açığı kapandı; KAP "Düzeltme Nedeni" de basıyor (2.3'e girdi) |
| Formun dönem etiketi meta veriden farklı (20/1.276) | Panel dönem anahtarı **meta veriden** alınmalı |

**AÇIK KARAR (1.4b'ye taşındı):** 19 kayıtta iki oran var — bizim
kalemlerden hesapladığımız ve formun özetindeki. En az biri kararı
çeviriyor (PNLSN 2025/6 Aylık: 4,67 % UYGUN ↔ form 5,30 % aşım). Kod
içinde seçilmedi; panelde ikisini birden taşımak önerildi.

*1.3 promptu arşiv olarak duruyor.*

<details>
<summary>1.3 promptu (arşiv)</summary>

> **Kapı yeri değişti (7 Ağu 2026).** Önce "1.3 geçmeden 1.4 koşulmaz"
> yazıyordu, gerekçe "2.600 isteği doğrulanmamış parser'a harcamak pahalı".
> **O gerekçe yanlıştı:** çekim parser'ı hiç kullanmıyor, HTML `bildirim_id`
> ile arşivleniyor ve ayrıştırma sonradan tekrar tekrar yapılabiliyor
> (kural 6 zaten bunun için var). Parser yanlış çıkarsa tek istek bile
> boşa gitmez; ama beklenen her gün pencereden bir gün siliyor.
>
> 1.3 artık **1.4b'yi (panel üretimi) kapılıyor**, çekimi değil. Örneklem
> 1.4a'nın arşivinden seçilir, ağa çıkmaz.

```
Görev: Parser'ı arşivdeki 20 farklı gerçek bildirimde doğrula.

Örneklem 1.4a'nın indirdiği arşivden seçilir; ağa çıkma, diskten oku.
Kolay olanı değil zoru kapsa:
- en az 3 solo (konsolide olmayan) finansal tablo
- en az 3 farklı sektör (sanayi, GYO, perakende)
- en az 2 küçük şirket (kalem sayısı az, tablolar kısmen boş)
- en az 2 tanesi 2025/6 Aylık (pencerenin en eski ucu — şablon farkı
  çıkacaksa orada çıkar)
- en az 1 düzeltme bildirimi varsa; is_duzeltme tespiti hiç doğrulanmadı

NOT: 2024 öncesi dönem bu pencereden çekilemiyor. Eski şablon (CLAUDE.md
kural 4'teki 3 soru -> 2 soru değişikliği) bu turda sınanamaz; kapsam
dışı olduğunu rapora yaz, "sınandı" sayma.

Her bildirim için: arşivden oku -> dogrula.

Kalıcı çıktı: tests/fixtures/pilot/ altına ayrıştırılmış JSON + beklenen
üç oran. tests/test_pilot.py bunları ağa çıkmadan regresyon olarak koşar.

Rapor: PILOT_20_RAPORU.md
- tablo: ticker | dönem | nitelik | şablon imzası | self-check | karar
- görülen farklı şablon imzalarının listesi
- self-check kalan her kayıt için TEŞHİS: parser mı bozuk, şablon mu farklı

Self-check kalırsa TOLERANS'ı gevşetme. `dok` ile sapmanın kaynağını bul.
Teşhis edemediğin sapmayı karantinada bırak ve raporla — bu bir bulgudur.
```

**Çıkış kriteri:** ✔ karşılandı ikinci koldan — 20/20 GEÇTİ değil, ama
geçmeyen 7 kaydın **her biri gerekçeli ve karantinada** (arşiv genelinde
22/22 teşhisli). `tests/test_pilot.py` yeşil (9/9), 20/20 ham HTML'den
yeniden ayrıştırıldı.

</details>

---

## 1.4a — Arşiv çekimi ✔ **BİTTİ (8 Ağu 2026)**

Çıktı: `INDIRME_RAPORU.md`, modül `katilim/toplayici.py`.
**1.276/1.276 form arşivde** (239 MB), eksik yok, kalıcı hata yok.
1.273 başarılı çekim + 373 yeniden deneme ≈ 1.646 HTTP denemesi;
onaylı 2.250/2.600 bütçesi aşılmadı.

| Bulgu | Etkisi |
|---|---|
| **Pencere dışı 15 kimliğin 15'i indi, 0 404** | `/tr/Bildirim/{id}`'de erişim ufku bulunamadı → arşiv kimliklerden yeniden kurulabilir |
| Üçü `dogrula` ile açıldı, üçünde de self-check GEÇTİ | "yumuşak 404" değil, gerçek form |
| Erişim ufkunun **derinliği ölçülemedi** | En eski kimliğimiz 05.08.2025; daha eskisi için kimlik yok |
| 114 geçici hata, üç geçişte kapandı (aralık 2→5→6 sn) | Negatif önbelleğe yazılmadı; yazılsaydı 114 form kalıcı "yok" olurdu |
| 33 pay kodu `AYIRT_EDILEMEDI` | Muaf ile beyansız bu rotadan ayrılmıyor; `MUAF` varsayılmadı |

**Yedekleme politikası için sonuç (karar bekliyor):** asıl kritik dosya
`veri/evren/bildirim_gecmisi.csv` (~90 KB, git'e sığar) — 239 MB'lık HTML
ondan yeniden indirilebilir. Yine de arşiv silinmemeli: ölçüm bugünün
davranışı, KAP yarın bu rotaya da ufuk koyabilir.

*1.4a promptu arşiv olarak duruyor.*

<details>
<summary>1.4a promptu (arşiv)</summary>

```
Görev: 1.2'nin listelediği TÜM KAFİF formlarını indir ve arşivle.

BU ADIM AYRIŞTIRMAZ. Tek işi HTML'i diske almak. Parser'a hiç
dokunmuyor, dolayısıyla 1.3'ü beklemesi gerekmiyor: yanlış ayrıştırma
sonradan düzeltilir, kaçırılan bildirim düzeltilemez.

Ön koşul: 1.2 bitti. 1.3 ÖN KOŞUL DEĞİL.

Kapsam: pencerede ne varsa hepsi. ~2.250 istek (2.0 sonrası aşağı çekildi:
şirket başına ~3 değil ~2 KAFİF görünüyor), ~2 saat.

Yeni modül: katilim/toplayici.py
- formlari_indir(bildirim_gecmisi, cekici) -> indirme raporu
- Tek sabit pencere toplayıcısı. SAYFALAMA DÖNGÜSÜ YAZMA (2.0: 92=92).
- İdempotanlık bildirim_id üzerinden (sha256 ile DEĞİL)
- Dosya adı: veri/ham/{TICKER}_{YIL}_{PERIYOT}_{bildirim_id}.html
- KAFİF'i olmayan şirket sessizce atlanmaz: 'BEYAN_YOK'. Muaf olan ile
  beyan vermeyen ayrı kayıtlanır; ayırt edilemiyorsa 'AYIRT_EDILEMEDI',
  ikisinden birini varsayma.

ÖNCE DUMAN TESTİ: 20 şirketle koş, arşivi gözle doğrula (dosya sayısı,
boyut dağılımı, rastgele birini `dogrula` ile aç). Çekim döngüsünde hata
varsa kalan isteği ondan sonra at. Bu 1.3 değil — parser kapısı değil,
indirme döngüsünün duman testi.

AYRICA ÖLÇ — "pencere keşfi öldürüyor, erişimi değil" hipotezi:
1.2'de n=1 gözlendi (1472632 pencereden düşmüştü, /tr/Bildirim/{id}'den
indi). Bu koşu hipotezi bedavaya n=1.276'ya çıkarıyor. Raporda ayrı bir
bölüm aç: pencere dışı kimliklerden kaçı indi, kaçı 404 verdi.
- Hepsi iniyorsa: arşiv kimliklerden yeniden kurulabilir demektir; bu,
  yedekleme ve yeniden çekme politikasını değiştirir (bana söyle).
- 404 çıkanlar varsa: erişimin de bir ufku var. En eski erişilebilen
  gonderim_ts'i raporla — asıl sınır o.
Bu ölçüm ek istek gerektirmiyor, zaten indirilecek kimlikler.

ARŞİV KURALI: veri/ham/ ve veri/onbellek/ artık önbellek değil, tek
kopyası olan arşiv. Temizleme komutu YAZMA, --zorla ile toplu yeniden
çekme YAPMA. (2.0'da olduğu gibi tekil --zorla ölçüm için serbest, ama
önce eski kopyayı veri/onbellek/arsiv/ altına tarihiyle al.)

Uzun koşu disiplini: ilerlemeyi her 50 istekte diske yaz; koşu kesilirse
kaldığı yerden devam etsin.

Çıktı: INDIRME_RAPORU.md — kaç form, kaç BEYAN_YOK, kaç hata, harcanan
istek, en eski ve en yeni gonderim_ts (pencerenin fiili genişliği).
```

**Çıkış kriteri:** ✔ karşılandı — 1.276 kimliğin 1.276'sının karşılığı
diskte; eksik 0, kimliksiz dosya 0, 50 KB altı şüpheli dosya 0; 30 dosyada
sha256 yeniden hesaplandı, hepsi tuttu.

</details>

---

## 1.4b — Ayrıştırma ve panel · **ağ isteği yok**

```
Görev: 1.4a'nın arşivini ayrıştır, snapshot panelini üret.

Ön koşul: 1.3 ✔ (22 sapmanın 22'si teşhis edildi, açıklanmamış karantina
yok). Bu kapı BURADA duruyor — panel, doğrulanmamış parser'ın çıktısıyla
yayımlanmaz.

Ağa çıkmaz; her şey diskten. Yanlış çıkarsa düzelt ve yeniden koş,
maliyeti sıfır.

- ayristir_arsiv(veri/ham) -> list[KafifBildirim]
- Ticker dosya adından tahmin edilmiyor, evren tablosundan geliyor
  (OKUBENI.md "bilinen açıklar" maddesi kapanır)
- Self-check kalan kayıt karantinaya; TOLERANS gevşetilmez

İKİ KARAR 1.3'ten geldi, ikisi de burada uygulanır:

1. HER İKİ ORAN TAŞINIR (H5, spec §2.3). 19 formda formun kendi 4E
   TOPLAM'ı kalemleriyle tutmuyor ve iki oran ayrışıyor.
   - `karar` sütunu ÖZET alanından üretilir (varsayılan; H5 kabul
     edilmiş gibi). Gerekçe aritmetik değil, hata maliyeti: BIST özeti
     kullanıyorsa ve biz kalemi kullanırsak PNLSN gibi vakada "UYGUN"
     deriz ve BIST elemiştir → yanlış pozitif, pahalı olan hata.
   - `*_orani_kalem` ve `*_orani_ozet` ayrı sütunlarda; `oran_ayrisiyor`
     bayrağı ve `karar_kalem_bazli` ikinci karar sütunu.
   - Bu 19 kayıt H5'in TEK ayırt edici örneklemi. `h5_ayirt_edici`
     bayrağıyla işaretle ki 4.0 doğrudan sorgulayabilsin.

2. DÖNEM ANAHTARI META VERİDEN. 1.276 formun 20'sinde formun kendi
   etiketi meta veriden farklı ("Yıllık" → "4. 3 Aylık Bildirim" 13 kez,
   "6 Aylık" → "2. 3 Aylık Bildirim" 7 kez); yıl hiç ayrışmıyor.
   Formun kendi etiketi `form_donem_etiketi` olarak taşınır ama anahtar
   değildir. Sıralama zaten gonderim_ts ile (3.1).

Çıktı:
- veri/panel/snapshot_{YYYYMMDD}.csv — ticker, yıl, periyot, altı oran
  (kalem+özet), oran_ayrisiyor, h5_ayirt_edici, karar, karar_kalem_bazli,
  red kodları, self-check, bildirim_id, gonderim_ts, is_duzeltme
- TOPLAMA_RAPORU.md — şirket/bildirim sayıları, BEYAN_YOK, karantina,
  karar dağılımı, şablon imzası dağılımı
```

**Çıkış kriteri:** Muaf olmayan her şirket için ya en az bir kayıt ya
`BEYAN_YOK`/`AYIRT_EDILEMEDI` işareti var. Karantina oranı raporlanmış.

---

# FAZ 2 — Tarihsel Derinlik

**Spec çıkış kriteri:** KAFİF başlangıcından bugüne panel dolu; şablon
versiyonları ayrıştırılmış.

> **Bu fazın "geri doldurma" ayağı kapandı (7 Ağu 2026).** 2.0 sistematik
> olarak sınadı: KAP bildirim sorgusu 1 yıldan geriye gitmiyor ve pencere
> 1 gün/gün kayıyor (@DERINLIK_KESFI_RAPORU.md). Faz 1.4 pencerenin
> tamamını topluyor; **derinlik bundan sonra geri doldurmayla değil,
> düzenli çekimle zamanla birikiyor.** Fazda geriye 2.2 (şablon
> versiyonlama) ve 2.3 (düzeltme mantığı) kaldı; ikisi de 1.4'ün çıktısı
> üstünde çalışır ve bloke değil.

## 2.0 — Tarihsel derinlik keşfi ✔ **BİTTİ (7 Ağu 2026)**

Çıktı: `DERINLIK_KESFI_RAPORU.md`, betik `arac/derinlik_kesfi.py`.
22 istek, bütçe 30'un en fazla 9'u tek koşuda kullanıldı, `BütçeAşıldı`
tetiklenmedi.

**Sonuç: BULUNAMADI.** Altı yol da denendi, pencere genişletilemedi.

| Bulgu | Etkisi |
|---|---|
| Pencere **1 gün/gün kayıyor** (05-08-2025 → 07-08-2025) | 1.4 zaman duyarlı; THY 2025/6 Aylık zaten kayboldu |
| `startDate`/`endDate` sunucuya **ulaşıyor ama atılıyor** | "isim bilmiyoruz" değil; rota tarih kabul etmiyor |
| Sunucu sayısı = render edilen satır (92=92) | **sayfalama yok**; sınır kayıt değil tarih |
| `/tr/kfif/` dönem seçici yok, geçmiş kimlik vermiyor | o yol da kapalı |
| Özet sayfasında bildirim listesi yok | `/tr/sirket-bildirimleri/` tek kayıt basıyor |
| `serverBaseUrl: kapsitebackend.mkk.com.tr` | tek keşfedilmemiş uç — **karar bekliyor** |
| RSC'de `disclosureBasic` yapılandırılmış geliyor | 1.2 checkbox kazımasın |

**Faz 2.1 koşulmaz** (koşulu sağlanmadı). Derinlik bundan sonra yalnız
**zamanla birikir**: bugün başlarsak 1 yıl, düzenli çekersek her gün +1 gün.

*Aşağıdaki 2.0 promptu arşiv olarak duruyor; yeniden koşulmaz.*

<details>
<summary>2.0 promptu (arşiv)</summary>

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

**Çıkış kriteri:** ✔ karşılandı — altı yol da denendi, karar "genişletilemiyor",
kayma ölçüldü (1 gün/gün).

</details>

---

## 2.0b — Arka uç servisi sondası · bütçe **10** · **1.4a'dan SONRA**

> Sıralama kasıtlı: servis ~%30-40 ihtimalle Faz 2'yi açar, kayan pencere
> ise kesin kaybettiriyor. Önce ölen veriyi yakala, sonra ölç.

```
Görev: kapsitebackend.mkk.com.tr uçlarını YALNIZCA ÖLÇ.

Ön koşul: 1.4a bitti, arşiv diskte. Bu adım aciliyetli değil.

Gerekçe (2.0'ın bıraktığı iz): 1 yıl sınırı formun kendi metnine göre bir
ARALIK GENİŞLİĞİ sınırı — "Seçilen Tarih Aralığı 1 Yıldan Fazla Olamaz" —
çapa sınırı değil. Ön yüz her zaman [bugün−1yıl, bugün] çapası kuruyor.
Servis keyfi çapa kabul ediyorsa (örn. 2023-01-01 → 2023-12-31) Faz 2
tümüyle açılır.

ÖLÇMEK İLE KULLANMAK AYRI KARARLAR. Bu adım yalnız birincisi:
- Uç yolunu bul: 2.0'da taranmayan 21 ortak JS parçasında ara. Tarama
  ağ isteği değil, indirilmiş parçalarda metin araması.
- Yol bulunursa EN FAZLA 10 istek: bir tanesi bilinen pencereyle (pozitif
  kontrol — servisin çalıştığını doğrular), bir tanesi geçmiş çapayla.
- min_aralik'i DÜŞÜRME, yükselt (5,0 sn). Belgelenmemiş bir iç servise
  ön yüzden daha nazik davranılır, daha az değil.
- Kimlik doğrulama, imzalı istek veya özel başlık gerekiyorsa DUR.
  Bunları taklit etmek "iyi niyetli istemci" sınırının dışına çıkar.

Yol bulunamazsa veya 10 istek yetmezse: dur, bulduğunu raporla, bütçe
büyütme.

Çıktı: ARKA_UC_SONDASI.md — uç yolu (bulunduysa), istek/yanıt biçimi,
keyfi çapa kabul ediliyor mu, ve KULLANIM İÇİN ÖNERİ + karşı argüman.
Kullanma kararını bana bırak; kodu kendiliğinden bağlama.
```

**Çıkış kriteri:** "Keyfi çapa kabul ediliyor / edilmiyor / yol bulunamadı"
üçünden biri gerekçeli yazılı. Kullanım kararı ayrıca bana sorulmuş.

---

## 2.1 — Geri doldurma *(koşullu — ŞU AN DEVRE DIŞI)*

> **Yalnızca 2.0 bir yol bulduysa koşulur.** 2.0 bulamadı (7 Ağu 2026),
> bu adım **atlanıyor**, 2.2'ye geçiliyor.
>
> Tek yeniden açılma şartı: §9'daki arka uç servisi kararı (a) değil
> (b)/(c) yönünde verilir ve servis keyfi tarih çapası kabul ederse.

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

METİN ARAMASI YAPMA. `is_duzeltme` şu an sayfa metninde "düzeltme"
arıyor ve hiç doğrulanmadı (OKUBENI.md bilinen açıklar). 1.2 gerçek
kaynağı buldu: RSC yükündeki `isChanged` alanı `DUZENLENEN` /
`DUZELTILEN` değerlerini **yapılandırılmış** taşıyor. Metin araması
sil, bu alana bağlan.

Bilinen hacim (1.2 ölçümü): 163 tekrar eden (ticker, yıl, periyot)
grubu, 135 şirkette. `DUZENLENEN` ile `DUZELTILEN` arasındaki fark
belgelenmemiş — ikisini ayrı taşı, birleştirme; anlamları netleşince
karar veririz.

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

ÖNCE BİR HATA DÜZELT — karar.py:187 sıralaması bozuk:

    key=(yil, 0 if periyot == "6 Aylık" else 1, gonderim_ts)

1.2 ölçtü ki periyot yalnız 6 Aylık/Yıllık değil: `9 Aylık` (7 kayıt) ve
`3 Aylık` (5 kayıt) da var. Bu anahtarda üçü de aynı kovaya (1) düşüyor,
yani Mayıs'ta verilen bir 3 Aylık, Ağustos'ta verilen 6 Aylık'tan SONRA
sıralanıyor. Tolerans durum makinesi bu sırayı yürüdüğü için yanlış sıra
doğrudan yanlış karar üretir.

Düzeltme: **yalnız `gonderim_ts` ile sırala.** Dönem etiketi kronoloji
taşımıyor — futbol kulüpleri 31 Mayıs kapanışı yüzünden "2024/Yıllık"ı
Ağustos 2025'te veriyor. Spec §5.1 zaten geçerlilik anını gonderim_ts'e
bağlıyor; sıralama da aynı alana bağlanmalı.

Testi de yaz: 3 Aylık / 6 Aylık / 9 Aylık / Yıllık karışık bir seri kur,
gonderim_ts sırasının korunduğunu doğrula.

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

## 4.0 — Nokta-zaman ön mutabakat · ağ isteği **yok**

> 1.1b'nin `endeks_uyeligi.csv`'si sayesinde mümkün oldu. Tarihsel
> mutabakatın yerini TUTMAZ; onu erkene çeker.

```
Görev: 1.4 biter bitmez kararlarımızı bugünkü XKTUM üyeliğiyle karşılaştır.

Ön koşul: 1.1b (endeks üyeliği) + 1.4 (panel) tamam. Ağa çıkmaz, iki
yerel dosyayı karşılaştırır.

Neden şimdi: H1-H4 doğrulanmadan üretilen panel araştırma çıktısıdır.
Tarihsel PDF'leri (4.1) beklemeden sınayabildiğimiz kadarını sınamak,
parser ve karar hatalarını Faz 3'e taşımadan yakalar.

Karşılaştırma: karar UYGUN/TOLERANSTA <-> "BIST KATILIM TÜM" üyeliği var.
Ticker düzeyinde yapılır (endeks üyeliği kod bazında).

DÖRT SINIF, ve üçü uyuşmazlık DEĞİL — bunları ayırmadan oran hesaplama:

1. GERÇEK UYUŞMAZLIK — karar ile üyelik çelişiyor, aşağıdaki üç
   açıklamanın hiçbiri geçerli değil. Asıl inceleme konusu bu.
2. DÖNEM UYUMSUZLUĞU — elimizdeki KAFİF, endeksin son revizyonundan
   (1 May / 1 Eki) SONRA yayımlanmış. Endeks bunu henüz görmemiş
   olabilir; çelişki beklenen davranış. gonderim_ts ile son revizyon
   tarihini karşılaştırıp otomatik etiketle.
3. KOD AYRIŞMASI — aynı uuid'in bir kodu endekste, diğeri değil.
   Likidite/fiili dolaşım kaynaklı, kriter kaynaklı değil. H1-H4'ün
   reddi SAYILMAZ.
4. KAPSAM — KAPSAM_DISI, BEYAN_YOK, BELIRSIZ kayıtlar. Ayrı sayılır.

Yanlış pozitif (biz UYGUN, BIST dışarıda) ayrı raporlanır: uygunsuzu
uygun göstermek, uygunu kaçırmaktan pahalıdır.

H5 İÇİN AYRI SORGU — bu adımın en yüksek bilgi değerli parçası.
`h5_ayirt_edici` işaretli 19 kayıt, özet-oranı ile kalem-oranının
FARKLI sonuç öngördüğü tek örneklem. Bu satırlarda:
- `karar` (özet bazlı) ile `karar_kalem_bazli` ayrışıyor mu?
- Ayrışanlarda BIST'in fiili üyeliği hangisini destekliyor?
Sonucu ayrı raporla ve n'i yaz. Kararı fiilen çeviren alt küme çok
küçük olabilir (bilinen: PNLSN 2025/6 Aylık); **n≤2 ise H5
"doğrulandı" YAZMA**, "tek gözlem tutarlı" yaz.

Çıktı: ON_MUTABAKAT_{tarih}.md — dört sınıfın sayıları, gerçek
uyuşmazlıkların listesi (ticker, kararımız, gerekçemiz, üyelik durumu),
hipotez bazında gruplama, ve tek cümlelik sonuç.

Bu adım hipotez REVİZE ETMEZ, yalnız aday listesi çıkarır. Revizyon 4.3'te,
tarihsel veriyle birlikte yapılır.
```

**Çıkış kriteri:** Dört sınıf ayrılmış; gerçek uyuşmazlık oranı ölçülmüş;
şüpheli hipotezler adaylandırılmış.

---

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
        ZAMAN DUYARLI ✔ BİTTİ  ┊         aciliyetsiz, arşiv güvende
  ╔══════════════════════════╗ ┊
  ║ 1.2 ✔ ──► 1.4a ✔ (arşiv) ║ ┊ 1.3 ─► 1.4b ─► 1.1b ─► 4.0 ─► 2.2 ─► 2.3
  ╚══════════════════════════╝ ┊  (20/20)        2.0b ─┘         │
   1.0 ✔  1.1 ✔  2.0 ✔        ┊                                 ▼
   2.1 ✘ (koşul sağlanmadı)    ┊  3.1 ─► 3.2 ─► 3.3 ─► 5.1 ─► 5.2 ─► 5.3
                               ┊  4.1 ─► 4.2 ─► 4.3 ─┘
```

**Kritik yol tamamlandı (8 Ağu 2026).** 1.2 → 1.4a hattı bitti; 1.276
formun tamamı diskte. Bundan sonraki hiçbir adım zaman duyarlı değil:
kalanların hepsi ya ağa hiç çıkmıyor ya da çektiği veri kaymıyor.

**Yeni bakım yükümlülüğü: 1.2'nin düzenli koşulması.** Kayan pencere
yalnız *keşfi* öldürüyor (1.4a §3, n=15); yani kaçırılan tek şey "böyle
bir form var" bilgisi. Her 1.2 koşusu o günün penceresindeki kimlikleri
kalıcılaştırıyor ve arşiv sonradan tamamlanabiliyor.

**Kesikli çizginin sağı arşiv çekiminden sonra.** Hepsinin ortak özelliği
aynı: ya ağa hiç çıkmıyor (1.3, 1.4b, 4.0) ya da çektiği veri kaymıyor
(1.1b özet sayfaları, 2.0b arka uç sondası). Bekletmenin maliyeti yok.

**2.0 `toplayici.py`'nin şeklini belirledi: tek sabit pencere.** Keyfi
derinlik ve sayfalama yok — sayfalama döngüsü yazılmayacak (92=92).

4.1 (tarihsel XKTUM verisi) Faz 3 ile paralel başlatılabilir; 4.0 onu
beklemez.

## Karar noktaları — otomatikleştirilmeyecek

Bu noktalarda Claude Code durup sormalı; kendi başına seçmemeli:

| Nerede | Karar | Durum |
|---|---|---|
| 1.0 sonrası | requests mi playwright mi | ✔ requests |
| 1.0 sonrası | adım bütçeleri | ✔ 5 / 800 / 800 / 2.250 / 10 |
| 1.4a sonrası | Yedekleme: kimlik CSV'si mi, 239 MB HTML mi? (arşiv kimliklerden yeniden kurulabiliyor, n=15) | **açık** — önerim: ikisi de, CSV git'e |
| 1.1 | Pazar bilgisi kaynağı ve maliyeti | ✔ özet sayfası, +746 onaylandı |
| 1.4 | Koşu kapsamı (güncel mi tüm pencere mi) | ✔ tüm pencere |
| 2.0 sonrası | Derinlik bulunduysa ek bütçe; bulunmadıysa Faz 2 kapanır | ✔ bulunamadı → 2.1 atlandı |
| 2.0 sonrası | Arka uç servisi (`kapsitebackend`) ölçülsün mü | ✔ ölç, ama **1.4a'dan sonra** (2.0b) |
| 1.3 kapısı | 20/20 çekimi mi paneli mi kapılıyor | ✔ paneli (1.4b) |
| **1.2** | `disclosureClass=DG` KAFİF kaybettiriyorsa ne yapılacak | **sıradaki** |
| **1.4a** | Duman testi sonrası tam koşu onayı | **sıradaki** |
| 2.0b | Arka uç bulunursa: kullanılsın mı (ölçmekten ayrı karar) | açık |
| 1.1b | KTLEV / tasarruf finansman: spec §0.4'e madde mi, yeni durum mu | açık |
| 1.1b | Sektörle kapanmayan belirsiz muafiyetler | açık |
| 4.0 sonrası | Şüpheli hipotezler 4.3'e mi bekletilecek, erken mi revize | açık |
| 3.1 | Zincir boşluğunda tolerans durumu ne olur | açık |
| 3.2 | Ortalama PD kaynağı ve hangi dönemin ortalaması | açık |
| 4.3 | Hipotez reddi ve yerine geçecek kural | açık |
| 5.2 | Fiyat verisi kaynağı | açık |
| 5.3 | Sinyal mi risk filtresi mi | açık |
