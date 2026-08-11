# Uygunluk Olay Serisi — Look-Ahead Denetimi ve Pencere Ölçümü

**Plan adımı:** 5.1 — Panelden look-ahead'sız olay serisi
**Tarih:** 2026-08-11
**Modül:** `katilim/olay.py` · CLI: `python -m katilim.cli olaylar`
**Çıktı:** `veri/panel/olaylar.csv` (206 olay × 17 sütun)
**Ağ isteği: 0.**

---

## 0. Sonuç — iki cümle

Panelden **206 olay / 137 pay kodu** çıkarıldı ve look-ahead disiplini
mutasyon testiyle kanıtlandı (§4). Asıl bulgu ölçümde: **karşı olayların
temiz penceresi NEGATİF** — düzeltme p95'ini bekleyen bir kural onları
hiç yakalayamaz (§3).

---

## 1. Olay tipleri

```
UYGUNLUK_KAZANIMI  70
UYGUNLUK_KAYBI     57
KILPAYI_UYARI      51
TOLERANSTAN_CIKIS  17
TOLERANSA_DUSUS    11
```

**İlk gözlem olay değildir.** Bir pay kodunun ilk kaydı taban durumu
kurar, geçiş olayı üretmez — aksi halde panel başlangıcında 539 sahte
"kazanım" doğardı. Durum bilgisi panelde, değişim bilgisi burada.

**`KILPAYI_UYARI` eşiği THY vakasından:** limite ≤0,5 puan kalmış ama
aşmamış oran. THY 2025 gelir oranı %4,92, limit %5 — üç finansal oranı
da geçiyor ama 0,08 puan mesafede. Aşan oran zaten kendi kapısından olay
üretiyor; kılpayı onun **öncesindeki** uyarı seviyesidir. Uyarı bir
durum değil olay: açıkken her kayıtta tekrar üretilmiyor.

---

## 2. Düzeltme İPTAL değil KARŞI OLAY

Bir olayı sonradan silmek look-ahead'a davetiyedir: o sinyal geçmiş bir
tarihte gerçekten yayımlanmış ve işlem yapılabilir durumdaydı. Silmek,
backtest'i imkânsız biçimde iyi gösterir.

Düzeltme geldiğinde eski olay yerinde kalır; düzeltmenin **kendi zaman
damgasıyla** ters yönde yeni bir olay üretilir.

```
karşı olay : 84 / 206   (75 benzersiz ticker-dönem)
```

84 sayısı düzeltme oranından (%15) yüksek görünüyor ama tutarlı: bir
düzeltme yalnız beyanı değil oranları da değiştiriyor (2.3: 160 olayda
oran değişmiş) ve oran değişimi UYGUN↔TOLERANSTA↔UYGUN_DEGIL sınırlarını
geçebiliyor.

### G1 teyitsiz — 2.3'ün bulgusu koda girdi

Karar çeviren 14 düzeltmenin **9'u `b1_1`/`b1_2`** (esas sözleşme) ve
**7'si False→True**. Esas sözleşme üç haftada değişmez; bunlar eksik
beyanın düzeltilmesidir. Yani ilk bildirimin "G1 temiz" demesi,
düzeltilmiş bir bildirimin aynı şeyi demesinden **zayıf kanıttır**.

`g1_teyitsiz` bayrağı: olumlu karar + henüz düzeltmeyle teyit edilmemiş.
**68 olayda açık.** Bayrak yalnız kaydın kendi alanlarına bakıyor, yani
look-ahead'sız.

---

## 3. ★ PENCERE ÖLÇÜMÜ — sinyal 2-4 hafta, karşı olayda YOK

Olgunluk **etiket olarak değil TARİH olarak** saklanıyor: `kesinlik`
zamana bağlıdır, tek bir etiket backtest'i o etiketin hesaplandığı ana
kilitlerdi. Olay iki eşik zamanı taşıyor:

```
olgunlasma_ts = olay_ts + 38 gün          (2.3'ün p95 düzeltme penceresi)
kesinlesme_ts = sonraki DÖNEMİN ilk yayını
```

Backtester `kesinlik(t)` çağırır ve kendi saatiyle karşılaştırır.

### Öncüllük — ikiye ayrılmalı

| | n | öncüllük medyanı | p95 (38 gün) sonrası |
|---|---|---|---|
| ilk bildirim | 122 | 56 gün | **+18 gün** |
| **karşı olay** | 84 | 28 gün | **−10 gün** |
| tümü | 206 | 50 gün | +12 gün |

**Karşı olaylarda pencere kapanıyor.** Düzeltme zaten geç geliyor
(medyan 21 gün); üstüne bir p95 daha beklemek revizyon tarihini aşıyor.
Yani düzeltmelerden gelen bilgi **ancak hızlı işlem edilirse**
kullanılabilir — ki bu tam olarak düzeltme riskinin en yüksek olduğu
rejimdir.

Bu, 5.2'nin ölçmesi gereken ödünleşmenin sayısal çekirdeği:

```
medyanda (21 gün) işlem   -> pencere geniş, düzeltme riski üstlenilir
p95'te   (38 gün) işlem   -> ilk bildirimde 18 gün kalır,
                              karşı olayda HİÇ kalmaz
```

### Doğrulama — görev metnindeki iki vaka

```
DOGUB 2026/6 Aylık  30.07.2026 -> yürürlük 01.10.2026 = 63 gün  ✔
```

Testle donduruldu (`test_gercek_dogub_pencere_olcumu`).

---

## 4. Look-ahead disiplini — ve KANITI

Her olayın zamanı **KAFİF `gonderim_ts`** (spec §5.1): bilanço dönemi
değil, endeks yürürlük tarihi değil. Zaman damgası olmayan kayıttan olay
üretilmiyor — olayın zamanı uydurulamaz.

### `endeks_yururluk_ts` nasıl türetiliyor

Naif kural ("olaydan sonraki ilk 1 May / 1 Eki") iki yerden yanlış:
takvim düzenli değil (4.1) ve **duyurudan sonra yayımlanan KAFİF o
revizyonu etkileyemez** (4.2).

Kullanılan kural: *`an` anında yalnız **duyurusu geçmiş** revizyonlar
bilinir; bunların en sonuncusunun bitiş tarihi de o duyuruyla birlikte
yayımlanmıştır, sonraki revizyon onun ertesi günüdür.*

Bu kural 28.09.2025'te yayımlanan bir formu doğru biçimde **01.05.2026**
revizyonuna bağlıyor — 24.09'da duyurulmuş 01.10.2025 listesine değil.

### Denetim üç katmanlı

1. **`girdi_ts` alanı** — her olay, KARAR alanlarını üretirken okunan
   girdilerin zaman damgalarını taşır; hepsi `olay_ts`'ten küçük/eşit.
2. **Nokta-zaman yeniden üretim** (`test_look_ahead_nokta_zaman_yeniden_uretim`) —
   `girdi_ts`'e **güvenmez**. Her olay için panel o ana kadar kırpılıp
   seri baştan üretilir; karar alanları birebir aynı çıkmalı. 206/206.
3. **Takvim de kırpılıyor** (`test_look_ahead_takvim_de_kirpildiginda_...`) —
   (2) tek başına yetmiyordu: takvim iki koşuda da aynı kaldığı için
   duyuru filtresi kaldırılsa iki koşu da aynı yanlış cevabı verirdi.

> **(3) gözden geçirme sırasında bulunan gerçek bir açıktı.** İlk yazımda
> yalnız panel kırpılıyordu; denetim eksikti.

### Denetimin boşa dönmediğinin kanıtı

Kırpma 206 olayın **103'ünde etkili**, 103'ünde yapısal olarak etkisiz —
pay kodunun serisindeki son olaydan sonra zaten kayıt yoktur, saklanacak
gelecek de yoktur. (Dağılım: 83 kod 1 olay, 43 kod 2, 8 kod 3, 2 kod 4,
1 kod 5.) Test bu oranın çökmesini ayrıca denetliyor.

### Mutasyon testi — denetim gerçekten yakalıyor mu

Üç kasıtlı hata enjekte edildi, üçü de yakalandı:

| Mutasyon | Yakalayan test |
|---|---|
| Yürürlük duyuru yerine **yürürlük tarihine** baksın | `test_yururluk_duyurudan_sonraki_kafif_...` |
| Panel **`gecerli_kayit=EVET`** ile süzülsün (gerçekçi hata) | `test_look_ahead_nokta_zaman_yeniden_uretim` |
| Takvimde **en son kayıt** kullanılsın (geleceğe bak) | `test_look_ahead_takvim_de_kirpildiginda_...` |

İkinci mutasyon özellikle önemli: "yalnız geçerli kaydı al" en doğal
görünen ve en sinsi look-ahead hatasıdır — karşı olayları tümüyle yok
eder ve seriyi olduğundan temiz gösterir.

---

## 5. Çıktı — `veri/panel/olaylar.csv`

Görev metnindeki sütunlar (`ticker, olay_tipi, olay_ts,
endeks_yururluk_ts, onceki_karar, yeni_karar, red_kodlari, bildirim_id`)
başta; şunlar eklendi:

| Sütun | Neden |
|---|---|
| `yil`, `periyot` | dönem kimliği; karşı olay eşleştirmesi |
| `duzeltme_izi` | `DUZENLENEN`/`DUZELTILEN` ayrı taşınıyor (2.3) |
| `karsi_olay` | düzeltmenin ürettiği ters olay |
| `g1_teyitsiz` | §2'deki G1 zayıflığı |
| `kilpayi_kriterleri` | hangi oran(lar) kılpayı bandında |
| `olgunlasma_ts`, `kesinlesme_ts` | olgunluk TARİH olarak |
| `oncul_gun` | olay → yürürlük penceresi |

`kesinlik` **sütun olarak yazılmadı**, bilinçli: zamana bağlı bir
etiketi dosyaya gömmek onu hesaplandığı ana kilitler. `Olay.kesinlik(t)`
ile hesaplanıyor.

Nokta-zaman yeniden üretim CLI'da da var:

```
python -m katilim.cli olaylar --kesim 2025-12-31   # 60 olay
```

---

## 6. Kapsam dışı / karşılanmayanlar

- **`endeks_yururluk_ts` bir sonraki revizyonun DUYURUSUNU varsaymıyor.**
  Yürürlük tarihi doğru; ama o revizyonun duyurusu (4-7 gün önce) olay
  anında bilinmediği için "bu olay o listeye yetişir mi" sorusu burada
  cevaplanmıyor. 5.2'nin işi.
- **Fiyat verisi yok** — bu modül olay serisini üretir, etkisini ölçmez.
  5.2 fiyat kaynağı seçilmeden koşulamaz (açık karar).
- **Panel derinliği 1 yıl.** 206 olayın hepsi 05.08.2025 sonrası; olay
  başına örneklem 5.2 için ince. Derinlik zamanla birikiyor (2.0).
- **H1–H6 revize edilmedi.** Bu modül hipotez sınamıyor.

**Testler: 238 geçiyor** (öncesi 213; +25 `tests/test_olay.py`).
