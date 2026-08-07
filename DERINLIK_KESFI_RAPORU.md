# KAP Tarihsel Derinlik Keşfi — Ölçüm Raporu

**Plan adımı:** 2.0 — Tarihsel derinlik keşfi (ölçüm turu)
**Tarih:** 2026-08-07
**Betik:** `arac/derinlik_kesfi.py` (tek seferlik; üretim kodu değil)
**Ölçüm ham çıktısı:** `veri/onbellek/derinlik_kesfi_olcum.json`
**Bütçe:** `HızSınırlayıcı(min_aralik=2.0, jitter=1.0, oturum_butcesi=30)` —
**aşılmadı, yükseltilmedi.** Toplam 22 istek, hepsi 200, yeniden deneme yok.

---

## 0. Özet — iki cümle

**Pencere KAYIYOR.** İki günde tam iki gün kaydı: 5 Ağustos'ta pencerenin başı
`05-08-2025` iken 7 Ağustos'ta `07-08-2025`. Düşen 7 kaydın biri THY'nin
**2025/6 Aylık KAFİF'i (bildirim 1472632)** — yani gecikilen her gün panel
derinliğinden kalıcı olarak düşüyor ve **1.4 zaman duyarlıdır.**

**Pencereyi genişleten bir yol BULUNAMADI.** Altı yolun hepsi denendi; hiçbiri
1 yıllık sınırı aşmadı. Faz 2.1 (geri doldurma) bu rotalarla **koşulamaz**.

| Sonda | Sonuç |
|---|---|
| 0 — pencere kayıyor mu | **KAYIYOR** (1 gün/gün) |
| 1 — Detaylı Sorgulama formu | Gerçek alan adları okundu; **sunucu alıp atıyor** |
| 2 — sayfalama | **Sayfalama yok** (sunucu sayısı = render edilen satır) |
| 3 — sıralama | Üç parametre de yok sayıldı |
| 4 — şirket özet sayfası | Bildirim listesi yok; yeni rota bulundu ama boş çıktı |
| 5 — kfif dönem seçici | **Yok** — yalnız en güncel dönem, geçmiş kimlik vermiyor |
| 6 — bildirim_id kaba kuvvet | **Denenmedi** (bilinçli; Spec §3.2) |

Tek keşfedilmemiş uç kaldı: sitenin kendi arka uç JSON servisi
(`kapsitebackend.mkk.com.tr`). Bir karar noktası olarak §9'da duruyor —
kendi başıma girmedim.

---

## 1. Yöntem ve harcanan bütçe

```
TOPLAM HTTP İSTEĞİ           : 22   (hepsi 200)
Tek koşudaki en yüksek sayaç : 9 / 30
BütçeAşıldı                  : hayır
Yeniden deneme / geri çekilme: hiç tetiklenmedi (429/5xx görülmedi)
Yanıt süreleri               : 0,33 – 1,97 sn (medyan 0,62)
```

Önbellek açık çalışıldı; sonda 4 ve 5 diskteki gövdelerden ölçüldü (0 istek).
**Sonda 0 bilinçli olarak `zorla` çekti** — sorulan şey pencerenin bugün nerede
durduğu, dünkü kopya bunun cevabı değil.

**Arşiv korundu.** `zorla` çekmeden önce diskteki 05.08.2026 kopyası
`veri/onbellek/arsiv/794a04972ce9ac804511a126_20260805.html` olarak saklandı.
Üzerine yazmak, sondanın ölçtüğü şeyi (o gün pencerede olup bugün olmayan
bildirimleri) silmek olurdu.

### Ölçüm aleti — 1.0'da olmayan üç çıpa

Bu turun ölçümleri 1.0'dan daha keskin, çünkü sayfanın kendi beyanları
kullanıldı:

1. **Sunucunun ilan ettiği pencere.** Sonuç sayfası gövdesine
   `Başlangıç Tarihi: 07-08-2025 / Bitiş Tarihi: 07-08-2026` basıyor. Bir
   parametre pencereyi oynattıysa sayfa bunu **kendisi söyler**; kayıt
   sayısından tahmin etmeye gerek yok.
2. **Sunucunun kendi kayıt sayısı.** `92 bildirim bulundu.` Bu sayı render
   edilen satır sayısından farklıysa sayfalama var demektir.
3. **RSC yükündeki yapılandırılmış kayıtlar.** `disclosureBasic` nesnesi
   `disclosureIndex` (= `bildirim_id`), `publishDate`, `disclosureClass`,
   `year`, `period`, `title` taşıyor.

### Pozitif kontrol — "hepsi yok sayıldı" ölçüm körlüğü mü?

Bir turda her parametre "yok sayıldı" çıkıyorsa ilk şüphelenilecek şey
ölçüm aletidir. Bu yüzden işlediği bilinen bir parametre kontrol olarak
koşuldu:

```
&disclosureClass=DG&kontrol=1  →  92 → 9 kayıt, sınıflar: ['DG']   İŞLENDİ
```

Alet çalışan parametreyi görüyor, uydurma `kontrol=1`'i ise zararsızca
yok sayıyor. Yani §3–§5'teki negatif sonuçlar gerçek.

---

## 2. Sonda 0 — pencere kayıyor mu (1 istek)

Aynı URL'in **iki gövdesi** karşılaştırıldı: diskteki 05.08.2026 kopyası ve
bugün zorla çekilen kopya. Rapora yazılmış sayılara güvenilmedi, ikisi de
yeniden ayrıştırıldı.

```
URL: https://kap.org.tr/tr/bildirim-sorgu-sonuc?member=4028e4a140f2ed720140f376bebb01a7
```

| Ölçüt | 05.08.2026 (disk) | 07.08.2026 (canlı) |
|---|---|---|
| ilan edilen pencere | `05-08-2025` → `05-08-2026` | **`07-08-2025` → `07-08-2026`** |
| kayıt (sunucu / render) | 98 / 98 | 92 / 92 |
| en eski kayıt | 05.08.2025 19:15:36 | **07.08.2025 10:12:14** |
| en yeni kayıt | 05.08.2026 08:01:20 | 07.08.2026 13:57:02 |
| KAFİF bildirimleri | 1472632 · 1566002 · 1643241 | **1566002 · 1643241** |
| DG sınıfı kayıt | 12 | **9** |

**Düşen 7 kayıt:** 1472624, 1472627, 1472630, **1472632**, 1472633, 1472634,
1472635. Hepsi 05.08.2025 tarihli.

**Karar: KAYIYOR.** Pencere sonu bugüne, başı bugün − 1 yıla sabitli; kayma
hızı tam 1 gün/gün. Yani panel derinliği kalıcı olarak `[bugün − 1 yıl, bugün]`
ile sınırlı ve **çekilmeyen gün telafi edilemez.**

### Bunun 1.4'e faturası — somut

Kaybedilen 1472632, THY'nin **2025/6 Aylık KAFİF'i.** İki gün önce
erişilebilirdi, bugün değil. Aynı mantıkla ASELS'in 2025/6 Aylık formu
(1472641, 05.08.2025 19:34 — 1.0 raporu §3) de bugün pencere dışında;
bu ölçülmedi, tarih damgasından **çıkarım**.

6 Aylık bilançolar ve onlara bağlı KAFİF'ler ağustos–eylülde yayımlanıyor.
Yani **2025/6 Aylık dalgasının süresi doluyor:** dalganın başı (5–7 Ağustos)
zaten düştü, kalanı önümüzdeki haftalarda gün gün düşecek. 1.4 ne kadar
ertelenirse o dalganın o kadar büyük kısmı kalıcı olarak kaybedilir.

**1.4 maliyet tahmini güncellendi.** THY'de pencerede artık 3 değil **2**
KAFİF var (2025/Yıllık + 2026/6 Aylık). Şirket başına ~2 form varsayımıyla:
746 sorgu + ~1.500 form ≈ **2.250 istek**, onaylanmış 2.600 bütçesinin altında.

---

## 3. Sonda 1 — "Detaylı Sorgulama" formunun gerçek alan adları (1 istek)

```
URL   : https://kap.org.tr/tr/bildirim-sorgu
Gövde : 1.141.334 karakter
```

**Formun HTML `action`'ı yok.** Sayfada 3 `<form>` var, üçünün de `action` ve
`method` niteliği `null`; tek gerçek `<input>` üstteki genel arama kutusu.
Form React ile yönetiliyor, yani "action" bir HTML niteliği değil bir JS
çağrısı. Sayfanın kendi yapılandırması iki taban adres açıklıyor:

```json
{"clientBaseUrl":"https://kap.org.tr","serverBaseUrl":"https://kapsitebackend.mkk.com.tr"}
```

**Alan adları tahmin edilmedi, RSC yükünden okundu.** İlgili olanlar:

```
startDate · endDate · dateInterval · dateRanges · specificDateOrDateInterval
annoucementDateCriterias · disclosureClass · notificationType · subjectOid
mkkMemberOid · kapMemberOid · notificationYear · notificationPeriod
```

Üç metin, sınırın ne olduğunu formun kendi ağzından söylüyor:

| Anahtar | Metin |
|---|---|
| `invaidDateRangeWarningMessage` | **"Seçilen Tarih Aralığı 1 Yıldan Fazla Olamaz"** |
| `dateRanges` | `Bugün(0) · Dün(1) · Son 1 hafta(7) · Son 1 ay(30) · Son 3 ay(90) · Son 6 ay(180) · Son 1 yıl(365)` |
| `twoThousandDataWarn` | "Arama sonuçları 2000 bildirim ile sınırlıdır…" |

Buradaki ayrım kritikti: **1 yıl bir aralık genişliği sınırı, çapa sınırı
değil.** Eğer `startDate`/`endDate` çapası serbest olsaydı yıl yıl geriye
yürünebilirdi. Bu yüzden asıl sondayı bu isimlerle koştum.

### Parametreler sunucuya ULAŞIYOR ama atılıyor

Bu turun en net bulgusu. Sonuç sayfasının RSC yükü, sunucunun gördüğü sorgu
parametrelerini geri yansıtıyor:

```
__PAGE__?{"member":"4028e4a140f2ed720140f376bebb01a7",
          "startDate":"07-08-2024","endDate":"07-08-2025"}
```

Yani sunucu `startDate`/`endDate`'i **aldı**, `searchParams`'ına yazdı ve
pencereyi yine `07-08-2025 → 07-08-2026` olarak kurdu. Bu, 1.0'daki
"yok sayıldı" gözleminden daha güçlü bir sonuç: sorun **isim bilmemek değil**;
`/tr/bildirim-sorgu-sonuc` sunucu bileşeni `member` ve `disclosureClass`
dışındaki parametreleri okuyup atıyor.

---

## 4. Sonda 2 ve 3 — tarih, sayfalama, sıralama (13 istek)

Taban (bugün): 92 kayıt, pencere `07-08-2025`, en eski `07.08.2025 10:12:14`.

| Deneme | Kayıt | İlan pencere | En eski | Sonuç |
|---|---|---|---|---|
| `&startDate=07-08-2024&endDate=07-08-2025` | 92 | 07-08-2025 | 07.08.2025 10:12 | yok sayıldı |
| `&startDate=07.08.2024&endDate=07.08.2025` | 92 | 07-08-2025 | 07.08.2025 10:12 | yok sayıldı |
| `&startDate=2024-08-07&endDate=2025-08-07` | 92 | 07-08-2025 | 07.08.2025 10:12 | yok sayıldı |
| `&dateInterval=365` | 92 | 07-08-2025 | 07.08.2025 10:12 | yok sayıldı |
| `&page=2` | 92 | 07-08-2025 | 07.08.2025 10:12 | yok sayıldı |
| `&pageNumber=2` | 92 | 07-08-2025 | 07.08.2025 10:12 | yok sayıldı |
| `&index=2` | 92 | 07-08-2025 | 07.08.2025 10:12 | yok sayıldı |
| `&offset=100` | 92 | 07-08-2025 | 07.08.2025 10:12 | yok sayıldı |
| `&size=200` | 92 | 07-08-2025 | 07.08.2025 10:12 | yok sayıldı |
| `&rowCount=200` | 92 | 07-08-2025 | 07.08.2025 10:12 | yok sayıldı |
| `&sort=asc` | 92 | 07-08-2025 | 07.08.2025 10:12 | yok sayıldı |
| `&order=asc` | 92 | 07-08-2025 | 07.08.2025 10:12 | yok sayıldı |
| `&direction=asc` | 92 | 07-08-2025 | 07.08.2025 10:12 | yok sayıldı |
| `&disclosureClass=DG&kontrol=1` *(pozitif kontrol)* | **9** | 07-08-2025 | 06.11.2025 21:13 | **İŞLENDİ** |

Tarih formatı üç yazımda da (`07-08-2024`, `07.08.2024`, `2024-08-07`) denendi;
sorun format değil.

**Sayfalama yok — kanıt kayıt sayısında değil, iki sayının eşitliğinde.**
Sunucunun bastığı "92 bildirim bulundu" ile render edilen satır sayısı her
sondada birebir eşit (fark 0). Sunucu bulduğunun tamamını tek sayfada
basıyor. Dolayısıyla **"pencere sınırı aslında kayıt sınırı olabilir"
hipotezi reddedildi**: sınır tarihtir. Formun kendi uyarısı da bunu destekliyor
— kayıt tavanı 2.000, bizim gördüğümüz 92.

`index` parametresinin ayrıca bir tuzağı var: Detaylı Sorgulama sayfasında
`index` **"Endeks"** demek (BIST endeks filtresi), sayfa indeksi değil.
Sayfalama adayı sanmak yanlış olurdu.

---

## 5. Sonda 4 — şirket özet sayfası (0 istek, önbellekten) + yeni rota (1 istek)

```
URL: https://kap.org.tr/tr/sirket-bilgileri/ozet/1107-turk-hava-yollari-a-o
```

Ayrı bir bildirim listesi **sunmuyor**: sayfada 0 bildirim kaydı, 0 checkbox
satırı, 0 `/tr/Bildirim/{id}` bağlantısı.

Ama sayfa bilmediğimiz bir rotaya bağlantı veriyor:
`/tr/sirket-bildirimleri/{id}-{slug}`. Ölçüldü:

```
URL   : https://kap.org.tr/tr/sirket-bildirimleri/1107-turk-hava-yollari-a-o
Kayıt : 1 (yalnız en güncel ODA bildirimi)
İlan edilen pencere : yok
KAFİF : yok
```

Sunucu tarafında tek kayıt basıyor; gerisi istemci tarafında yükleniyor
olmalı. Tarihsel derinlik için **kullanışsız**, ama arka uç servisinin
varlığına ikinci bir işaret.

---

## 6. Sonda 5 — `/tr/kfif/{id}-{slug}` dönem seçici (0 istek, önbellekten)

```
URL: https://kap.org.tr/tr/kfif/1107-turk-hava-yollari-a-o
```

| Aranan | Bulunan |
|---|---|
| `<select>` dönem seçici | **yok** (0 select alanı) |
| `/tr/Bildirim/{id}` bağlantısı | **yok** |
| gömülü `disclosureIndex` izi | **yok** |
| görülen dönem metni | yalnız **"2026 / 6 Aylık"** |

Sayfa tek dönem gösteriyor ve geçmiş dönemlere **kimlik vermiyor.** Yani
"kfif sayfasından kimlikleri al, formları `/tr/Bildirim/{id}`'den çek"
yolu kapalı. Rotanın veri kaynağı olarak yasak oluşu (ROTA_KESFI_RAPORU §6)
zaten geçerliydi; bu sonda onu bir kez daha gereksiz kıldı.

---

## 7. Sonda 6 — `bildirim_id` kaba kuvvet: DENENMEDİ

Bilinçli. Bilinen kimliklerin (1472632, 1566002, 1643241) arasını taramak
KAP'a rastgele yük bindirir ve Spec §3.2'nin "nazik davran" ilkesini ihlal
eder. Ayrıca kimlik uzayı **şirketler arası ortak** — 1472632 ile 1566002
arasında ~93 bin bildirim var ve bunların büyük kısmı başka şirketlere ait.
Verimsiz olduğu kadar saygısız.

---

## 8. SONUÇ — BULUNAMADI

**1 yıllık pencerenin ötesine geçen bir yol bulunamadı.** Bu negatif sonuç,
altı yolun her birinin ayrı ayrı denenmesiyle ve ölçüm aletinin pozitif
kontrolle doğrulanmasıyla desteklenmiştir.

Bunun üç doğrudan sonucu var:

1. **Faz 2.1 (geri doldurma) koşulmaz.** Koşulu — "2.0 bir yol bulursa" —
   sağlanmadı. Plan bu haliyle 1.4 → 4.0 → 2.2 hattından yürür.
2. **Panelin derinliği zamanla birikir.** Bugün başlarsak 1 yıllık derinlikle
   başlarız ve her çektiğimiz gün arşive kalıcı olarak eklenir. `veri/ham/`
   bir önbellek değil, **telafisi olmayan arşivin kendisi** (CLAUDE.md).
   Bu, 2,5 yıl sonra 3,5 yıllık panel demek — ama ancak düzenli çekersek.
3. **2024 öncesi ve eski şablon bu rotadan asla gelmeyecek.** Faz 2.2'nin
   (şablon versiyonlama) tek imzayla karşılaşması muhtemel. Geriye dönük
   etiketleme için Spec §6'nın ikincil kaynağı — BIST "Dönemsel Değişiklikler"
   PDF'leri — tek yol olarak kalıyor (plan 4.1).

---

## 9. Açık kalan tek uç — karar noktası

**Sitenin kendi arka uç JSON servisi: `https://kapsitebackend.mkk.com.tr`.**

Nereden çıktı: Detaylı Sorgulama sayfası kendi yapılandırmasında
`clientBaseUrl` / `serverBaseUrl` çiftini açıkça yayımlıyor. Form React
olduğu için "gönderim" bu servise yapılan bir JSON çağrısı.

Neden cazip: 1 yıl sınırı formun kendi metnine göre bir **aralık genişliği**
sınırı. Servis keyfi çapa kabul ediyorsa yıl yıl geriye yürünerek KAFİF'in
başlangıcına kadar inilebilir — Faz 2 tümüyle açılır.

Neden kendi başıma girmedim, üç sebep:

1. **Uç yolu bulunamadı.** Detaylı Sorgulama'ya özel 5 JS parçası indirildi
   (5 istek), hiçbirinde servis yolu yok. Kalan 21 parça ortak; hepsini
   taramak bu turun bütçesini aşar. Yol **tahmin edilmeyecek** — sonda 6'yı
   reddeden gerekçe burada da geçerli.
2. **Belgelenmemiş bir iç servis.** KAP'ın resmî public API'si yok (Spec §3.2);
   arayüzün arkasındaki servisi doğrudan tüketmek, HTML kazımaktan farklı bir
   karar — kırılganlık ve kullanım koşulları riski ayrı ağırlıkta.
3. **Ayrı bütçe gerektirir.** Keşif turu 30 istekle sınırlıydı; bu iş kendi
   adımını ve kendi onayını hak ediyor.

**Karar sizin.** Üç seçenek: (a) kapat, derinlik zamanla biriksin;
(b) küçük bir bütçeyle (≈10 istek) tarayıcı ağ günlüğünden servis yolunu
gözlemleyip yalnız *ölçelim*, kullanma kararı sonra; (c) doğrudan Faz 2.1'e
geçilsin. Ben (b)'yi öneriyorum: ölçmek ucuz, kullanmak ayrı karar.

*Not: bu turda tarayıcıyla gözlem denendi ama tarayıcı bölmesi sayfayı hiç
yükleyemedi (gövde boş, konsol sessiz); ölçüm alınamadı, ısrar edilmedi.*

---

## 10. Kodda kalan davranış

Betik tek seferlik ama iki davranışı testlendi (`tests/test_derinlik_kesfi.py`,
8 test, ağa çıkmaz) — çünkü ikisi de 1.2'nin ayıklayıcısında tekrar edecek:

- **Kural 7 kodda.** `sorgu_olc`, beklediği üç çıpanın (sunucu sayısı, satırlar,
  tablo içi boş-sonuç metni) hiçbirini bulamazsa `SayfaOkunamadi` **fırlatır**;
  sessizce boş liste dönmez. "0 kayıt" ile "sayfa okunamadı" ayrı temsil edilir.
- **Sözlük tuzağı.** "Bildirim bulunamadı." metni i18n sözlüğünde **her**
  sayfada geçiyor; gövdede aramak dolu sayfayı boş gösterir. Ayrım tablo
  içinde aranarak yapılıyor ve testi var.
- **Alan sırasından bağımsız RSC ayıklama.** Kayıt nesnesi süslü parantez
  eşlemesiyle çıkarılıyor; KAP alan sırasını değiştirirse regex sessizce boş
  küme döndürürdü.

**1.2 için devir notu:** `bildirim_id`'yi checkbox `id`'sinden kazımaya gerek
yok. RSC yükündeki `disclosureBasic` nesnesi `disclosureIndex`, `publishDate`,
`disclosureClass`, `year`, `period`, `donem`, `title` alanlarını
yapılandırılmış olarak veriyor — checkbox yolu yedek katman olarak kalsın.
