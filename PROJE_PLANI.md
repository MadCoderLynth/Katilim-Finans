# Proje Planı — Kalan İş

Kurallar ve güncel durum: `CLAUDE.md`. Sistem tasarımı: spec v0.1.
Tamamlanmış adımların özgün promptları: `PLAN_ARSIV.md` (otomatik yüklenmez).

**Durum (10 Ağu 2026): doğrulama kapısı GEÇİLDİ.** 4.2 mutabakatı 95/95
olayda uyuştu, uyuşmazlık sıfır. Testin gücü ölçüldü: kesim noktasında
panel tabanı %47/%53 iken bu sonucun şansla olma olasılığı ≈10⁻²⁹.
Spec §4'ün "Faz 4 öncesi panel araştırma çıktısıdır" kaydı artık geçmişte —
**motor öngörücü ve kullanılabilir.**

Biten: 0 · 1.0 · 1.1 · 1.1b · 1.2 · 1.3 · 1.4a · 1.4b · 2.0 · 2.3 · 3.1 ·
4.0 · 4.1 · 4.2. Testler 210. Panel 1.280 satır / 539 pay kodu.

## Kullanılabilirliğe kalan yol

Motor hazır; eksik olan temiz bir arayüz. Asgari yol **iki adım ve ikisi
de ağa çıkmıyor**:

| Adım | Ne yapar | Bağımlılık |
|---|---|---|
| **5.1** | Panelden olay serisi + `kesinlik` alanı | yok, diskten |
| **5.3** | `uygunluk_durumu()` ve `olaylar()` | 5.1 |

**Bugün bile risk filtresi olarak kullanılabilir:** `veri/panel/panel.csv`
"X, T anında uygun muydu" sorusunu look-ahead'sız cevaplıyor,
`veri/evren/endeks_uyeligi.csv` bugünkü XKTUM'u veriyor. 5.1+5.3 bunu
programatik hale getiriyor, yeni bilgi üretmiyor.

**5.2 (getiri çalışması) ayrı bir iştir ve kullanımı engellemez.** O,
"sinyal mi risk filtresi mi" sorusunun cevabı.

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

# SIRADAKİ İŞ — Faz 5

## 5.1 — Olay serisi üretimi

```
Görev: Panelden look-ahead'sız olay serisi çıkar.

Ön koşul: Faz 4 tamamlandı. Öncesinde bu seriyi trading sistemine bağlama.

katilim/olay.py
- Olay tipleri: UYGUNLUK_KAYBI, UYGUNLUK_KAZANIMI, TOLERANSA_DUSUS,
  TOLERANSTAN_CIKIS, KILPAYI_UYARI (limite 0,5 puandan yakın — THY'nin
  %4,92'si bu kategorinin gerekçesi)

DÜZELTME PENCERESİ — 2.3'te ÖLÇÜLDÜ, tasarıma girer.

  düzeltme gecikmesi (n=181): medyan 21 gün · p90 35 · p95 38 · max 55
  karar çeviren 14 düzeltmenin hepsi: <= 31 gün
  düzeltme oranı: 163 dönem / ~1.100 geçerli dönem kaydı ≈ %15

Bu, bilgi öncüllüğü penceresini büyük ölçüde TÜKETİYOR. DEVIR_NOTU
§2.5 "4-8 hafta" diyordu; gerçek kullanılabilir pencere daha dar:
  DOGUB 2026/6 Aylık 30.07.2026 -> revizyon 01.10 = 63 gün
    p95 düzeltme penceresi 38 gün -> temiz sinyal ~25 gün
  PNLSN 2025/Yıllık 25.02.2026 -> revizyon 01.05 = 65 gün -> ~27 gün
Yani sinyal var ama 2-4 hafta. Max gecikmeyi (55 gün) beklerseniz
pencere neredeyse kapanıyor. 5.2 bunu ölçmenin merkezine koysun.

- Olaya `kesinlik` alanı: HAM (yeni yayım) / OLGUN (>38 gün, p95
  geçildi) / KESIN (sonraki dönem yayımlandı). Eşikler 2.3'ün
  ölçümünden, tahminden değil.
- Aynı (ticker, dönem) için düzeltme gelirse olayı İPTAL ETME,
  KARŞI OLAY üret — iptal look-ahead'a davetiye, karşı olay değil.
- 5.2 iki rejimi AYRI ölçsün: medyanda (21 gün) işlem eden ile p95'te
  (38 gün) işlem eden. Aradaki fark, hız/kesinlik ödünleşmesinin
  fiyatı — ve bu modülün sinyal mi risk filtresi mi olacağını
  belirleyecek olan da o.

G1 KAPISI EN GÜVENİLMEZ — 2.3 bulgusu. Karar çeviren 14 düzeltmenin
9'u `b1_1`/`b1_2` (esas sözleşme beyanları) ve 7'si False->True. Esas
sözleşme üç haftada değişmez; bunlar eksik beyanın düzeltilmesi. Yani
ilk bildirimin "G1 temiz" demesi, düzeltilmiş bildirimin aynı şeyi
demesinden zayıf kanıttır. `kesinlik` alanı bunu yansıtsın: G1'e
dayanan UYGUN kararları HAM aşamasında ayrıca işaretle.
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

Fiyat verisi: **mevcut swing trading sistemimin veri katmanı** (karar
verildi, 11 Ağu). Arayüzünü ben anlatacağım; varsayma, sor. Yeni bir
fiyat kaynağı çekmeye kalkma — bölünme/temettü düzeltmesi orada zaten
yapılmış durumda ve iki kaynak iki farklı düzeltilmiş seri demek.

KARŞI OLAY EŞİĞİ AYRI: ilk olay için olgunluk +38g, karşı olay için
+22g (5.1 devri; ikinci düzeltme dağılımı n=16, medyan 4g, p95 22g).
"38 gün" karşı olaya uygulanırsa pencere yapay olarak negatif çıkar.

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


## 5.3 — `katilim.api` · **SIRADAKİ** · ağ isteği yok

> **5.2'den öne alındı (11 Ağu 2026).** Motor 4.2'de doğrulandı; eksik
> olan arayüz. 5.2'nin sonucu entegrasyonun *şeklini* etkiliyor, arayüzü
> değil — iki fonksiyon şimdi yazılabilir ve risk filtresi olarak
> bugün bağlanabilir.
>
> **Önce küçük bir düzeltme (5.1'den devir):** `olgunlasma_ts` olay
> tipine duyarlı olmalı. `+38g` eşiği ilk-bildirimden-ilk-düzeltmeye
> dağılımının p95'i; karşı olay zaten bir düzeltme olduğu için onun
> eşiği **ikinci düzeltme** dağılımından gelir: n=16, medyan 4g,
> **p95 22g**. İlk olay +38g, karşı olay +22g. Testini ekle.
> (Düzeltmelerin %90,2'si bir daha düzeltilmiyor; 16 ikinci düzeltmenin
> 10'u ≤7 gün.)

```
Görev: Üç şey — (a) olgunluk eşiği düzeltmesi, (b) katilim.api,
(c) tek hisse kartı + basit portal.

Ön koşul: 5.1 ✔. 5.2 ÖN KOŞUL DEĞİL.
YENİ BAĞIMLILIK YOK. requirements.txt üç satır kalacak; portal
stdlib http.server + subprocess ile yazılır.

---------------------------------------------------------------
(a) OLGUNLUK EŞİĞİ — önce bu
---------------------------------------------------------------
olgunlasma_ts olay tipine duyarlı olsun: ilk olay +38g, KARŞI OLAY
+22g. Gerekçe: 38 gün ilk-bildirimden-ilk-düzeltmeye dağılımının
p95'i; karşı olay zaten bir düzeltmedir, onun riski "ikinci düzeltme
gelir mi" ve o dağılım ayrı — n=16, medyan 4g, p95 22g, max 22g
(163 düzeltme grubunun %9,8'i). Yanlış eşik karşı olay penceresini
yapay olarak negatif gösteriyordu. Testini ekle.

---------------------------------------------------------------
(b) katilim/api.py — dış dünyanın TEK giriş noktası
---------------------------------------------------------------
- uygunluk_durumu(ticker, tarih) -> Durum
  Verilen tarihte BİLİNEN en güncel karar. Look-ahead yok:
  gecerlilik_baslangic <= tarih olan en geç kayıt.
- olaylar(ticker, baslangic=None, bitis=None) -> list[Olay]
- hisse_karti(ticker, tarih=None) -> dict   (portal ve CLI bunu kullanır)

ÜÇ TUZAK — hepsi belgeli, api'de AÇIKÇA ele alınacak:

1. KARANTİNA. 22 kayıt self-check'ten geçmedi ama panelde duruyor.
   uygunluk_durumu varsayılan olarak bunları DIŞARIDA bırakır
   (karantinali=False parametresi ile istenirse döner). Bayrağı yok
   sayan bir tüketici doğrulanmamış kararı sessizce alır.
2. MUAF ≠ ELENMİŞ. KAPSAM_DISI "uygun değil" DEĞİLDİR — katılım
   esaslı finans kuruluşları (ALBRK, KTLEV) KAFİF vermiyor ama
   XKTUM'da. Durum nesnesi bunu ayrı bir alanla söylesin, çağıran
   "UYGUN değil" diye okumasın.
3. GÖRÜŞ YOK ≠ UYGUN DEĞİL. BEYAN_YOK, FORM_VAR_BILDIRIM_YOK,
   BELIRSIZ ve tarih panelin başlangıcından önceyse -> GORUS_YOK
   döner. None dönme, sessizce UYGUN_DEGIL'e düşme.

Trading sistemi panelin iç yapısına BU ÜÇ FONKSİYON DIŞINDA
bağlanmasın. CSV yollarını api içinde topla.

Test: look-ahead (dünkü tarih dünkü kararı verir), karantina süzgeci,
üç "görüş yok" durumu, KAPSAM_DISI'nin ayrı temsili.

---------------------------------------------------------------
(c) HİSSE KARTI + PORTAL
---------------------------------------------------------------
CLI: python3 -m katilim.cli kart THYAO      (terminalde aynı içerik)
Portal: python3 -m katilim.portal           (tarayıcıyı açar)

Kart içeriği (hisse_karti çıktısı):
  unvan · pazar · sektör · muafiyet durumu
  BUGÜNKÜ KARAR — büyük ve renkli (yeşil UYGUN / sarı TOLERANSTA /
    kırmızı UYGUN_DEGIL / gri GORUS_YOK|KAPSAM_DISI) + red kodları
  katılım endeksi üyeliği (endeks_uyeligi.csv) + XKTUM dönem geçmişi
  KARAR GEÇMİŞİ tablosu: geçerlilik_ts | dönem | karar | üç oran |
    red kodları; düzeltmeyle geçersiz kılınan satır soluk gösterilsin,
    geçerli kayıt işaretli
  OLAYLAR: tip, tarih, endeks yürürlük tarihi, olgunluk durumu
    (kesinlik'i ÇAĞRI ANINDA hesapla — CSV'den okuma, 5.1 kararı)
  DÜZELTMELER: neyin değiştiği
  karantina veya g1_teyitsiz varsa görünür uyarı

PORTAL TASARIMI — sade tut, tek dosya, tek sayfa:
- Üstte ticker kutusu + Ara. Enter çalışsın. Bilinmeyen kod için
  "evrende yok" desin, boş sayfa dönmesin.
- Altta ayrı ve GÖRSEL OLARAK AYRILMIŞ bir "Bakım" bölümü, iki düğme:
    [Bildirimleri tara]  -> cli bildirimler   (~650 istek, ~40 dk)
    [Formları indir]     -> cli indir          (~2.600 istek, ~2 sa)

  BU DÜĞMELER TEHLİKELİ, ona göre yaz:
  * her birinin yanında SON KOŞU TARİHİ ve harcanacak BÜTÇE yazsın
  * tek tıkla başlamasın — onay adımı olsun
  * koşarken düğme kilitlensin, çıktı canlı aksın (satır satır)
  * BütçeAşıldı veya hata olursa ekranda kırmızı görünsün, sessizce
    bitmiş sayılmasın (kural 7)
  * bu düğmeler bütçeyi kod içinden büyütmez; varsayılan bütçe sabit

- Stil: tek <style> bloğu, koyu tema, sistem fontu, CDN yok, JS
  çerçevesi yok. Amaç terminale girmemek, güzel bir site değil.
- Portal VERİ ÜRETMEZ, yalnız api.py'yi çağırır. İkinci bir doğruluk
  kaynağı olmasın.
- Yalnız 127.0.0.1'e bağlan.

Test: hisse_karti'nin bilinen bir tickerda beklenen alanları
döndürmesi, bilinmeyen tickerda düzgün hata; portalın HTML üretimi
(sunucu ayağa kaldırılmadan, fonksiyon düzeyinde).

Bu iki fonksiyon dışında trading sistemi panelin iç yapısına bağlanmasın.
```

**Çıkış kriteri:** `python3 -m katilim.portal` açılıyor, ticker girilince
kart geliyor, iki bakım düğmesi onaylı çalışıyor. `katilim.api` üç
fonksiyonu sağlıyor; look-ahead ve karantina süzgeci test edilmiş.
Yeni bağımlılık yok.

---

## 5.4 — Portal okunabilirliği + kapsam sondası

```
Görev: dört iş. (a) legend, (b) kaynak bağlantıları, (c) "ne"
detayı, (d) BEYAN_YOK kapsam sondası.

(a)–(c) ağa çıkmaz. (d) için ayrı bütçe isteyeceksin.

---------------------------------------------------------------
(a) KOD LEJANDI — kart üstünde açılır bir bölüm
---------------------------------------------------------------
Kod adları ezberlenmek zorunda kalmasın. Kaynak: karar.py'deki
KESIN_KAPILAR ve model.py'deki BEYAN_ALANLARI — ELLE YAZMA, oradan
türet ki kural değişirse lejand da değişsin.

  G0_MUAF            mali sektör muafiyeti — KAPSAM DIŞI (elenmiş değil)
  G1_ESAS_SOZLESME   esas sözleşmede Standart md. 1.2 faaliyeti/ortaklığı
  G2_IMTIYAZ         kâr payı veya tasfiye payı imtiyazı (md. 1.8)
  G3_MADDE_15        md. 1.5 kamuoyu açıklaması / mahkeme kararı
  G4_DOGRUDAN_AYKIRI Rehber md. 3.1 — 4A'daki yedi faaliyetten biri
  G5_GELIR           uygun olmayan gelir > %5
  G6_VARLIK          uygun olmayan varlık > %33
  G7_BORC            uygun olmayan borç > %33
  ..._TOLERANS       limit aşıldı ama tolerans bandı içinde (md. 3.5)

Bandları da yaz: gelir %5 → %5,5 · varlık/borç %33 → %36,3.

---------------------------------------------------------------
(b) KAYNAK BAĞLANTILARI — her iddia tıklanabilir olsun
---------------------------------------------------------------
- Her karar satırındaki bildirim_id -> https://kap.org.tr/tr/Bildirim/{id}
  (yeni sekmede). Kaynağı görmeden karara güvenilmemeli.
- XKTUM dönem geçmişindeki her dönem -> o dönemin yerel PDF'i
  (veri/referans/ham/…). Portal 127.0.0.1'de olduğu için dosyayı
  kendisi servis etsin; file:// bağlantısı tarayıcıda çalışmaz.
- Kaynak dosya adı kartta görünsün, gizli link olmasın.

---------------------------------------------------------------
(c) "NE" DETAYI — sıfır yeni veri
---------------------------------------------------------------
Kart şu an yalnız kapı kodunu gösteriyor. Hangi BEYANIN tetiklediğini
de göster; veri zaten elimizde.
  G4 -> hangi b4_* açık: alkol / domuz / tütün üretim-toptan / kumar /
        katılım dışı finans / aykırı yayıncılık / otel-turizm-eğlence
  G1 -> b1_1 (faaliyet) mi b1_2 (ortaklık) mı
  G2 -> kâr payı mı tasfiye payı mı
Adları model.py::BEYAN_ALANLARI'ndan al.

DÜRÜSTLÜK NOTU — kartta görünsün: KAFİF'in beyanı "şirketin kendisi,
tüzel kişi ortakları VEYA iştirakleri" diye tek bir evet/hayır. Form
HANGİSİ olduğunu söylemiyor. Yani "ne" biliniyor, "kim" bilinmiyor.
Kart bunu açıkça yazsın ki kullanıcı iştirak sandığı şeyin şirketin
kendisi olabileceğini bilsin. "Kim" sorusu KAP finansal rapor
dipnotlarını (bağlı ortaklık/iştirak tablosu) gerektirir — ayrı veri
kaynağı, bu adımın kapsamı DIŞINDA.
Serbest metin alanları (madde_4/7/16) kartta gösterilsin; gelir
kalemleriyle ilgili ama denetim izi olarak değerli (THY'de 5G/7'nin
katılım bankası mevduatı olduğu oradan anlaşılıyor).

---------------------------------------------------------------
(d) KAPSAM SONDASI — bütçe iste, sonra koş
---------------------------------------------------------------
BEYAN_YOK etiketli 73 şirket için /tr/kfif/{id}-{slug} ikili sondası:
form var mı yok mu. ~73 istek.

Gerekçe: 4.0'da bu mekanizma ("form var, bildirim yok") bulunmuştu ama
yalnız XKTUM üyesi 8 şirkete bakılmıştı. BIGTK (BİG MEDYA, ANA PAZAR,
0 bildirim kaydı) aynı örüntüde ve XKTUM üyesi değil — yani sonda
yapılmamış 65 şirket kaldı.

SONDA KAPSAMI ARTIRMAZ, ETİKETİ DÜZELTİR. kfif rotası panele giremiyor
(zaman damgası yok, b4_5/6/7 okunamıyor — rota keşfi §6, yasak).
Formu olanlar FORM_VAR_BILDIRIM_YOK'a geçer; "beyan vermemiş" ile
"beyanı var ama biz göremiyoruz" aynı şey değil.

Sonda gövdeleri önbelleğe YAZILMASIN (yasak rotanın gövdesi arşive
karışmasın). Sonuç: kaç şirkette form var, panelin fiili kapsamı ne
kadar iyimserdi. Rapora yaz.
```

**Çıkış kriteri:** Lejand kartta ve `karar.py`'den türetiliyor; her
bildirim_id KAP'a, her XKTUM dönemi yerel PDF'e tıklanabiliyor; G1/G2/G4
hangi beyanın tetiklediğini gösteriyor ve "kim" bilinmediği yazılı;
73 şirketin sonda sonucu raporlanmış, etiketler düzeltilmiş.

---

## Bakım — ertelenemez

> Proje park edilse bile bu durmaz.

Sorgu penceresi 1 gün/gün kayıyor. Kayan şey **keşif**: kimlik
`bildirim_gecmisi.csv`'ye yazıldıysa form sonradan da inebiliyor, ama
kimlik pencereden düşerse o form bir daha bulunamaz.

**Yılda iki koşu yeter, dalgalardan sonra:**

| Ne zaman | Komut | Süre |
|---|---|---|
| Eylül sonu (6 Aylık dalgası) | `bildirimler` → `indir` | ~1 sa |
| Nisan sonu (Yıllık dalgası) | `bildirimler` → `indir` | ~1 sa |

Portalın iki düğmesi tam olarak bunun içindir. Bir yılı tamamen
atlamak panelde **kalıcı** bir delik açar.

Arşiv 07.08.2026'da bitiyor; 2026/6 Aylık dalgası hâlâ akıyor.
**İlk koşu: eylül sonu.**

---

# ERTELENEN VE DÜŞÜRÜLEN

Hiçbiri kullanılabilirliği engellemiyor. Sıra önerisi: **4.3 → 3.3 → 4.1b**;
2.2 ve 3.2 için aşağıdaki gerekçelere bakın.

## 4.3 — Hipotez revizyonu

> **4.2 kanıt biriktirdi; kararlar bekliyor.** Kapsama eşitsiz ve bu
> başlı başına bir bulgu:
>
> | Hipotez | 4.2 kapsaması | Durum |
> |---|---|---|
> | H1 (4A'da EVET kesin eleme) | 2 olay | zayıf destek |
> | H2 (kâr payı imtiyazı) | **0 olay** | **SINANMADI** — "uyuşmazlık yok" onu desteklemiyor |
> | H3 (PD paydası) | 33 olay | uyuştu → **uygulanmamalı** (bkz. 3.2) |
> | H4 (tolerans şirket bazında) | 8 olay | destekleniyor |
> | H5 (özet oran) | 0 (ayırt edici örneklem yok) | yanlışlanamamış yargı |
> | H6 (gecikmeli yeniden giriş) | **doğrudan kanıt** | aşağıya bak |
>
> **H6 artık aday değil, kanıtlı.** 2026-05'te 4 olayda kararımız sınırın
> iki yanında aynıydı — biz erken davrandık. İkisi yeniden giriş:
> **KLSER** (çıkış 2024-07) ve **PNSUT** (çıkış 2025-05; önceki kesimde
> biz TOLERANSTA diyorduk, BIST 7 ay bekletti). PEKGY'nin 4.0'da açtığı
> soru buydu. Kodlamadan önce TKBB Standardı md. 3.5'in giriş yönünde
> simetrik bir hüküm içerip içermediğine bakılacak.
>
> **En ucuz kullanım: kural yerine bayrak.** H6'yı kural olarak çözmek
> yerine, yeniden giriş ima eden kararı 5.1'de "endeksçe henüz
> onaylanmadı" diye işaretlemek yeterli olabilir — daha ucuz ve daha
> dürüst. Kural haline getirmek ancak TKBB metni destekliyorsa.

```
Görev: 4.2'nin bulgularıyla H1-H6'yı karara bağla.

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


## 2.2 — Şablon versiyonlama · **fiilen no-op**

> **Ertelendi.** 1.3 ölçtü: arşivdeki 1.276 formun **1.276'sı tek imza**
> taşıyor (`4A|4B|4C|4D|4E|5F|5G|5H|6I|6J|OZET|S1|S2|S3`). Yani bugün
> ayrılacak versiyon yok; modül yalnız gelecek bir şablon revizyonunda
> devreye girecek. Bir sonraki KAFİF dalgasında imza değişirse önceliği
> yükselir. **Tetikleyici:** 1.2/1.4a'nın yeni koşusunda bilinmeyen imza
> çıkması.

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


## 3.2 — Belirsiz bant ve PD paydası · **UYGULAMAYIN**

> **Düşürüldü (10 Ağu 2026).** Panelde %33–36,3 bandında 51 kayıt /
> 46 dönem var — yani H3'ün H5'ten farklı olarak ayırt edici bir
> örneklemi VAR ve 4.2 onu sınadı: H3 kapsamındaki 33 olay uyuştu,
> uyuşmazlık sıfır.
>
> Mantık: PD paydası (`max(PD, TV)`) paydayı büyütür, oranı düşürür,
> kararı **gevşetir**. Şu anki yanlış negatif sayımız **sıfır** — yani
> gevşetecek bir şey yok. Uygulanması yalnızca yanlış pozitif
> üretebilir, ki bu pahalı olan hatadır.
>
> **Aşağıdaki prompt arşivdir, koşulmaz.** H3 revizyonu 4.3'ün konusu;
> orada da "uygulanmasın" gerekçesi bu ölçümdür. Panel derinleşip bir
> yanlış negatif çıkarsa yeniden değerlendirilir.

<details>
<summary>3.2 promptu (arşiv — koşulmaz)</summary>

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


</details>

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


### 4.1b — Daha eski dönem PDF'leri *(opsiyonel, 5.2 için)*

> 4.2 için değersiz, **5.2 için doğrudan değerli.** Karar: topla.

```
Görev: 01.07.2024 öncesine ait dönemsel değişiklik PDF'lerini ara.

Gerekçe — 4.2 için DEĞİL: o dönemlerin KAFİF'i yok ve gelmeyecek
(pencere kaydı). Mutabakat değeri kalıcı olarak sıfır.

Gerekçe — 5.2 için EVET: bir endeks çıkışını tespit etmek için KAFİF'e
gerek yok, iki ardışık bileşen listesi yeterli. Elimizdeki 4 sınır 248
olay veriyor (99 giriş, 149 çıkış); her yeni sınır ~50 olay daha
ekliyor ve getiri dağılımı çalışmasının örneklemi doğrudan bu.

DİKKAT — PDF'ler bildirim kimliği TAŞIMIYOR, yalnız pay kodu listesi.
"Eski PDF'lerden 2024 öncesi bildirim kimliği çıkarsa erişim ufku
sınanır" fikri YANLIŞTI; o sınama bu yoldan yapılamaz.

Başlangıç tarihi bilinmeyen dönem CSV'ye YAZILMAZ (4.1 kuralı):
tarihsiz dönem 5.2'de de kullanılamaz, çünkü olay tarihi yok.
Bir listenin başlangıcı belirlenemiyorsa o listeyi atla ve raporla.

Bütçe: 10 istek. Bulunamıyorsa zorlamayın — 248 olay 5.2 için zaten
yeterli bir taban.
```

**Çıkış kriteri:** Bulunan her yeni dönem için başlangıç/bitiş tarihi
belirli; `xktum_bilesenler.csv` genişletildi; yeni olay sayısı raporlandı.

---

