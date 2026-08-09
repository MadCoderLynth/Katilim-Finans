# Şirket Özet Sayfaları — Pazar, Sektör, Endeks Üyeliği

**Plan adımı:** 1.1b — Özet sayfaları
**Tarih:** 2026-08-08
**Modül:** `katilim/ozet.py` · CLI: `python -m katilim.cli ozet`
**Çıktı:** `veri/evren/sirketler.csv` (pazar + sektör) ·
`veri/evren/endeks_uyeligi.csv` (5.161 satır) · `veri/evren/ozet_durumu.csv`
**Bütçe:** onaylanan 800 **aşıldı** → 400 ek bütçe onayınızla alındı.
Toplam **746 başarılı çekim + ~210 yeniden deneme ≈ 956 HTTP denemesi.**

---

## 0. Özet

```
tüzel kişi            : 746 / 746 çekildi
durum                 : OK 583 · ALAN_EKSIK 162 · SAYFA_OKUNAMADI 1
pazar dolu            : 793 / 795 pay kodu
sektör dolu           : 643 / 795 pay kodu
endeks üyeliği        : 5.161 satır / 605 pay kodu
BIST KATILIM TÜM üyesi: 243 pay kodu      <- 4.0'ın referans tarafı
belirsiz muafiyet     : 33 -> 27 (6'sı kapandı)
```

---

## 1. Bütçe aşımı — karar noktası olarak işletildi

İlk koşu 800 isteklik onaylı bütçeyi **604. sayfada** doldurdu ve
`BütçeAşıldı` fırlattı. Bütçe kod içinden büyütülmedi; durum ölçülüp size
getirildi ve **400 ek bütçe onayınızla** alındı.

Aşımın sebebi: yeniden denemeler de bütçeden düşüyor. 604 başarılı çekim +
~196 yeniden deneme = 800. 1.4a'daki dalgalı sıkıştırmanın aynısı.

| Geçiş | Aralık | Başarılı | Yeniden deneme | Kalan hata |
|---|---|---|---|---|
| 1 | 2,0 sn | 604 | ~196 | 53 + 142 çekilmemiş |
| 2 | 4,0 sn | 138 | 14 | 4 + 1 okunamadı |
| 3 | 6,0 sn | 4 | 0 | **0** + 1 okunamadı |

Her geçişte aralık **yükseltildi**; yön tek taraflı.

Kontrol noktası her 50 istekte diske yazdığı için ilk koşunun işi
kaybolmadı — ikinci geçiş 604 sayfayı önbellekten okudu, yalnız kalanı
ağdan istedi.

---

## 2. Üç alan nereden geliyor

Değerler sayfanın RSC yükünde, **çip bağlantılarının href'inde** ve base64
kodlu:

```
/tr/Pazarlar?market=WUlMRElaIFBBWkFS       -> "YILDIZ PAZAR"
/tr/Sektorler?sector=xLBNQUxBVA            -> "İMALAT"
/tr/Endeksler?indice=QklTVCBLQVRJTElNIDMw  -> "BIST KATILIM 30"
```

İçerik imzası kullanıldı, konum değil (kural 4). Sektör alanı **sıralı**:
ana sektör önce, alt sektör sonra (ACSEL: `İMALAT / KİMYA İLAÇ...`);
`set()` kullanmak bu bilgiyi yok ederdi, sıra koruyarak tekilleştirildi.

---

## 3. Bulgu — pazar sözlüğü spec §0.4'ün varsaydığından geniş

Spec §0.4 pazarı `Yıldız / Ana / Alt` diye tarif ediyor. **Gözlem 25 farklı
değer/kombinasyon:**

| Pazar | Pay kodu |
|---|---|
| ANA PAZAR | 242 |
| YILDIZ PAZAR | 229 |
| KESİN ALIM SATIM PAZARI-NİTELİKLİ YATIRIMCILAR ARASINDA | 138 |
| ALT PAZAR | 46 |
| PİYASA ÖNCESİ İŞLEM PLATFORMU | 18 |
| YAKIN İZLEME PAZARI | 15 |
| YAPILANDIRILMIŞ ÜRÜNLER VE FON PAZARI | 5 |
| GÖZALTI PAZARI · EMTİA PAZARI · (kombinasyonlar) | kalanı |

**Bir pay kodu birden çok pazarda işlem görebiliyor** (ör. TCELL:
"KESİN ALIM SATIM PAZARI-NİTELİKLİ YATIRIMCILAR ARASINDA / YILDIZ PAZAR").
Bu yüzden alan tek değer değil, `/` ile birleşik liste olarak taşındı —
bilgi kaybetmemek için.

**XKTUM ön şartı açısından:** Yıldız/Ana/Alt pazarlardan birinde işlem gören
**605 pay kodu** var. Kalanlar nitelikli yatırımcı pazarı, piyasa öncesi
platform, gözaltı gibi endekslere girmeyen pazarlarda.

> **Spec §0.4'e not gerekiyor.** Alan tanımı "Yıldız/Ana/Alt" olarak
> yazılmış; gerçek sözlük bundan geniş ve çoklu. Metni güncellemedim —
> §0.4 bir *veri kaynağı tablosu*, hipotez değil; yine de bir sonraki
> düzenlemede genişletilmesi gerekiyor.

---

## 4. Endeks üyeliği — 4.0'ın girdisi

`veri/evren/endeks_uyeligi.csv` (ticker, endeks_adi, **olcum_tarihi**):

```
5.161 satır / 605 pay kodu
BIST KATILIM TUM              : 243
BIST KATILIM 100              : 103
BIST KATILIM 50               :  52
BIST KATILIM TEMETTU          :  39
BIST KATILIM 30               :  32
BIST SÜRDÜRÜLEBİLİRLİK KATILIM:  25
```

**`olcum_tarihi` zorunlu alan ve her satırda dolu.** Bu tablo **bugünün
fotoğrafı**, tarihsel değil; tarihsiz saklanırsa 4.0 onu nokta-zaman verisi
sanar ve yanlış döneme bakar.

### Join denetimi (mutabakat DEĞİL)

Panelin ticker anahtarı ile endeks tablosu birleşiyor mu diye bakıldı:

```
panelde ticker 539 · XKTUM üyesi 243 · ORTAK 232
XKTUM üyesi ama panelde yok: 11
```

Ham dağılım (yalnız veri kullanılabilirliğini gösterir):

| | karar UYGUN | TOLERANSTA | UYGUN_DEGIL |
|---|---|---|---|
| XKTUM **içinde** | 224 | 6 | **2** |
| XKTUM **dışında** | **17** | **4** | 286 |

**Bu bir mutabakat sonucu değildir.** 4.0 dört sınıfı (gerçek uyuşmazlık /
dönem uyumsuzluğu / kod ayrışması / kapsam) ayırmadan uyuşmazlık oranı
hesaplanamaz — özellikle "XKTUM dışında ama biz UYGUN diyoruz" 21 kaydın
kaçının dönem uyumsuzluğu olduğu bilinmiyor. Burada gösterilen tek şey:
**anahtarlar tutuyor, 4.0 koşulabilir.**

---

## 5. 33 belirsiz muafiyet — 6'sı kapandı, 27'si kaldı

### Kapananlar (6) — spec §0.4'te adı geçiyor

ETYAT · EUKYO · GRNYO · ISYAT · MTRYO · OYAYO

Sektörleri `MALİ KURULUŞLAR / MENKUL KIYMET YATIRIM ORTAKLIKLARI`; §0.4'ün
muafiyet listesinde "menkul kıymet yatırım ortaklıkları" **birebir yazılı**.

**Kapatmadan önce güvenlik kontrolü yapıldı:** altısının da hiç KAFİF'i yok
(1.2 ölçümü). Yani `MUAF` işaretlemek veri düşürmüyor; kayıt
`AYIRT_EDILEMEDI` → `KAPSAM_DISI`'ya geçiyor, ki doğru sınıf bu.

*Bu kapanma bir kod hatasını da ortaya çıkardı:* kalıp tekil yazılmıştı
("menkul kiymet yatirim ortakligi") ama KAP çoğul basıyor
("ORTAKLIKLARI") ve tekil, çoğulun içinde geçmiyor. Kök kalıba çevrildi;
`tests/test_ozet.py::test_mkyo_cogul_yazimla_da_kapaniyor` donduruyor.

### Kalanlar (27) — MUAF İŞARETLENMEDİ

**26 varlık kiralama şirketi** (sukuk ihraç aracı): AKTVK, ATAVK, BRKT,
DGRVK, DKVRL, DVRLK, EKTVK, EMVAR, GGBVK, GYVAR, HAYVK, HDFVK, HLVKS,
KATVK, KLVKS, KTKVK, KTSVK, NURVK, OSVKS, QNBVK, TEVKS, TFNVK, VAKVK,
YATVK, ZKBVK, ZKBVR.

İkisi birden geçerli: **sektör alanları boş** (sayfalarında o bölüm yok) ve
§0.4 "varlık kiralama"yı saymıyor — listedeki "varlık yönetim şirketleri"
farklı bir şey. Kapatacak kanıt yok, belirsiz bırakıldı.

**+ KTLEV** (aşağıda).

Yanlış `MUAF` şirketi panelden sessizce düşürür; fazladan sorgulamak yalnız
istek harcar. Asimetri gereği hepsi belirsiz kaldı.

---

## 6. KTLEV — **karar sizin**

```
unvan  : KATILIMEVİM TASARRUF FİNANSMAN A.Ş.
pazar  : YILDIZ PAZAR
sektör : MALİ KURULUŞLAR / FİNANSMAN ŞİRKETLERİ
muafiyet: BELİRSİZ (değişmedi)
```

Sektör alanı soruyu **çözmüyor, keskinleştiriyor**: KAP onu "finansman
şirketi" diye sınıflıyor. Spec §0.4'ün muafiyet listesinde *finansman
şirketleri* geçmiyor — listede finansal kiralama ve faktoring var, tasarruf
finansman yok. Ama §0.4 aynı zamanda "KTLEV'in KAFİF sayfası 'Bilgi Mevcut
Değil' dönüyor" diyor ve 1.2 ölçtü ki KTLEV hiç KAFİF vermemiş.

Yani elimizdeki durum: **muafiyet listesinde yazmıyor ama beyan da
vermiyor.** İki çözüm var ve seçim sizin:

- **(a) Spec §0.4'e madde eklemek:** "tasarruf finansman şirketleri" muafiyet
  listesine yazılır. Sonuç: KTLEV `KAPSAM_DISI`. Risk: TKBB Standardı'nda
  böyle bir muafiyet yoksa uydurmuş oluruz.
- **(b) Üçüncü durum tanımlamak:** "muaf değil ama beyan vermiyor". Zaten
  1.4a'da `BEYAN_YOK` diye bir durum var; KTLEV oraya geçer ve ihtiyatlılık
  gereği endeks dışında sayılır (spec §0.4'ün mevcut mantığı). Risk yok,
  ama muafiyet sorusu açık kalır.

Ben **(b)**'yi öneriyorum: `BEYAN_YOK` zaten tanımlı ve ihtiyatlı taraf.
(a) TKBB Standardı'nın metnine bakmadan yapılmamalı. **Kendi başıma
seçmedim.**

---

## 7. Bir kayıt okunamadı — teşhis edildi

`YKR / YKYAT` (YAPI KREDİ YATIRIM MENKUL DEĞERLER): sayfa 200 döndü ama
üç etiketten hiçbirini taşımıyor. Gövde 70 KB (diğerleri ~240 KB).

Sebep: aracı kurum, payları BIST'te işlem görmüyor; KAP bu üye için şirket
bilgi bölümü yayımlamıyor. **Parser doğru davrandı** — tahmin etmek yerine
`OzetOkunamadi` fırlattı (kural 7).

Panele etkisi yok: YKR/YKYAT unvanından zaten `mali_sektor_muaf=True`
(aracı kurum, §0.4) ve KAFİF vermiyor.

**162 `ALAN_EKSIK`** kaydı ise hata değil: 97'sinde sektör+endeks, 31'inde
yalnız endeks yok. Nitelikli yatırımcı pazarı / piyasa öncesi platformdaki
şirketler hiçbir endekste olmuyor. Alan yoksa `None` kalıyor — **boş dize
değil**, çünkü "" ile "bilinmiyor" aynı şey değil.

---

## 8. Kodda kalan davranış

- **Sorgu ekseni slug (tüzel kişi), çıktı ekseni ticker.** Çoklu kodlu
  şirket tek istek, iki kayıt.
- **Kural 7 kodda:** etiket de çip de yoksa `OzetOkunamadi` fırlatılıyor;
  etiket var çip yoksa alan gerçekten boş ve `None` kalıyor.
- **Yeniden değerlendirme yalnız `None`'a dokunuyor** — unvan tabanlı
  mevcut `True`/`False` kararı sektörle ezilmiyor.
- **Şemsiye sektör tek başına kapatmıyor.** "FİNANS VE SİGORTA
  FAALİYETLERİ" içinde "sigorta" geçiyor; doğrudan eşleştirmek her finans
  şirketini (tasarruf finansman dahil) muaf yapardı. Şemsiye düşülüp
  **alt sektöre** bakılıyor. Bu bir testle donduruldu.

**Testler: 138 geçiyor** (22 motor + 9 çekici + 23 evren + 8 derinlik +
15 bildirim + 7 rsc + 13 toplayıcı + 9 pilot + 12 panel + 20 özet).
