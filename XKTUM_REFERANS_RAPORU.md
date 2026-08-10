# XKTUM Tarihsel Bileşen Listeleri — Toplama ve Dönem Eşlemesi

**Plan adımı:** 4.1 — XKTUM bileşen listelerini tarihsel olarak topla
**Tarih:** 2026-08-10
**Betik:** `arac/xktum_referans.py` (tek seferlik) · `--indir` / `--ayristir` / `--kur`
**Çıktı:** `veri/referans/xktum_bilesenler.csv` (3.979 satır) ·
`veri/referans/ham/` (5 PDF, 1,74 MB) · `ayristirma_olcumu.json` ·
`kurulum_tanilari.json`
**Ağ isteği:** **5** (yalnız PDF indirme, borsaistanbul.com). KAP'a 0.

---

## 0. Sonuç — üç cümle

Beş dönemsel değişiklik PDF'i indirildi ve XKTUM bileşen listesi bugünden
geriye yürüyerek **5 endeks dönemi için** kuruldu (293 → 257 → 241 → 235
→ 243 üye). **Dönem eşlemesi ölçüldü, varsayılmadı:** 01.10.2025
revizyonunu **2025/6 Aylık**, 01.05.2026 revizyonunu **2025/Yıllık**
KAFİF dalgası besliyor; daha eski üç revizyonun KAFİF karşılığı
elimizde **hiç yok**.

⚠ **Görev metnindeki "endeks yürürlük tarihi 1 Mayıs / 1 Ekim"
varsayımı yanlışlandı** (§2) ve **gerçek veri kesim noktası yürürlük
tarihi değil DUYURU tarihidir** (§5). İkisi de sahte uyuşmazlık üretirdi.

---

## 1. Kaynaklar

Borsa İstanbul "BIST Katılım Endeksleri Dönemsel Değişiklikleri" PDF'leri.
Dosya adı kalıbı **tutarsız** (biri tarihsiz, biri `-1` ekli, biri tire
karakteri farklı), bu yüzden URL'ler tahmin edilmedi; arama ve duyuru
sayfasından toplanıp betikte sabitlendi.

| Dönem | Duyuru | Boyut | Dosya |
|---|---|---|---|
| 01.07.2024 – 30.11.2024 | 25.06.2024 | 189 KB | `katilim_endeksleri_20240701_20241130.pdf` |
| 01.12.2024 – 30.04.2025 | 26.11.2024 | 213 KB | `..._20241201_20250430.pdf` |
| 01.05.2025 – 30.09.2025 | 25.04.2025 | 1.048 KB | `..._20250501_20250930.pdf` |
| 01.10.2025 – 30.04.2026 | 24.09.2025 | 147 KB | `..._20251001_20260430.pdf` |
| 01.05.2026 – 30.09.2026 | 27.04.2026 | 191 KB | `..._20260501_20260930.pdf` |

**Dönem sınırları PDF'lerin kendi başlıklarından doğrulandı** — dosya
adına güvenilmedi. Beşinde de başlık dosya adıyla tuttu; tutmasaydı
uyarı üretilecekti.

**Duyuru tarihi PDF meta verisinin `CreationDate` alanından.** Bağımsız
doğrulandı: 01.05.2026 dönemi için borsaistanbul.com duyuru sayfası
(`duyuru/15415`) da **27.04.2026** diyor. Beşinde de duyuru, yürürlükten
**4–7 gün önce**.

`veri/referans/ham/` **silinmez** (kural 6'nın referans tarafındaki
karşılığı): PDF'ler URL'lerinden düşerse geçmişi yeniden ayrıştırmanın
tek yolu bu.

---

## 2. BULGU — revizyon takvimi düzenli DEĞİL

Görev metni ve spec §5.2 revizyonu **"1 Mayıs / 1 Ekim"** diye tarif
ediyor. Kaynağın kendi başlıkları bunu yanlışlıyor:

```
01.07.2024  ──5 ay──▶  01.12.2024  ──5 ay──▶  01.05.2025
     ──5 ay──▶  01.10.2025  ──7 AY──▶  01.05.2026  ──5 ay──▶  (01.10.2026?)
```

İki ayrı sapma var:

1. **2024'te takvim Temmuz/Aralık'tı**, Mayıs/Ekim değil. Mayıs/Ekim
   ritmi ancak 01.05.2025'ten itibaren başlıyor.
2. **01.10.2025 – 30.04.2026 dönemi 7 ay sürdü.** Geçiş dönemi; PDF'in
   kendi başlığı böyle diyor.

### Bunun koda faturası — `mutabakat.py` düzeltilmeli (4.2'nin işi)

`katilim/mutabakat.py:49` şu an sabit:

```python
REVIZYON_AYLARI = (5, 10)

def son_revizyon(bugun: date) -> date:      # satır 69
    """Yürürlükteki son endeks revizyonu (1 Mayıs / 1 Ekim)."""
```

**Bugünkü nokta-zaman ölçümü için doğru sonuç veriyor** (10.08.2026 →
01.05.2026 ✔), yani 4.0'ın bulguları etkilenmedi. Ama tarihsel
mutabakatta yanlış:

| Sorulan tarih | `son_revizyon` | Gerçek | |
|---|---|---|---|
| 01.03.2026 | 01.10.2025 | 01.10.2025 | ✔ |
| 01.03.2025 | 01.10.2024 | **01.12.2024** | ✘ |
| 01.08.2024 | 01.05.2024 | **01.07.2024** | ✘ |

**Kural: takvim varsayılmaz, `xktum_bilesenler.csv`'den okunur.** Dosya
zaten her satırda `donem_baslangic`/`donem_bitis` taşıyor. Hipotez
değil bir *veri kaynağı* düzeltmesi olduğu için H1–H5'e dokunmuyor;
yine de kod içinde sessizce değiştirmedim — **4.2'nin işi** ve o
commit'te spec §5.2 ile birlikte güncellenmeli.

---

## 3. Ayrıştırma — sayfa değil BANT

PDF düzeni: her endeks kendi başlığı altında, yan yana
`ALINACAK PAYLAR | ÇIKARILACAK PAYLAR | (YEDEK PAYLAR)` blokları.

**İlk sürüm sayfa bazlıydı ve sessizce kirleniyordu.** 01.12.2024
PDF'inde XKTUM listesi 2. sayfaya taşıyor ve o sayfanın **altında**
"BIST KATILIM 100 ENDEKSİ" tablosu var; sayfa imzası ikisini birden
XKTUM sanıyordu (giren 54/çıkan 72 — gerçeği 31/65).

**Hatayı `yedek` sayacı yakaladı.** XKTUM'da yedek pay listesi yoktur,
alt endekslerde vardır; XKTUM bandından yedek çıkması bandın taşmış
olması demektir. Bu artık **hata fırlatıyor**, uyarı değil.

Düzeltilmiş yöntem, üç kademesi de içerikten:

1. **Bant:** `BIST KATILIM … ENDEKSİ` başlığından bir sonraki başlığa
   kadarki dikey aralık. Sayfa sınırı değil.
2. **Bölüm sınırları:** `ALINACAK` / `ÇIKARILACAK` / `YEDEK`
   sözcüklerinin x konumu.
3. **Pay kodu sütunu:** `PAY KODU` başlığındaki `PAY` sözcüğünün x0'ı.
   Ölçüldü — veri satırındaki pay kodunun x0'ı bu değere **birebir**
   oturuyor (5 PDF'in hepsinde; ör. `PAY@82 → AKYHO@82`,
   `PAY@323 → SONME@323`). Sarmalanmış başlıkta da çalışıyor.

`extract_tables()` kullanılmadı: 01.05.2025 PDF'i bütün sütunu **tek
hücreye** basıyor (satır ayrımı yok), koordinat yolu beşinde de çalışıyor.

**İkinci hata — çıpanın kendisi:** `PAY` sözcüğü tam çıpanın x0'ında
duruyor ve `[A-Z]{3,6}` kalıbına uyuyor. Elenmeden önce her bölüme sahte
bir `PAY` kodu giriyordu (5 PDF'de 5 kez). `_YAPISAL_SOZCUKLER`
bunun için var.

### Self-check — kaynağın kendi aritmetiği

PDF satırlarını `1..N` diye numaralıyor. Ayıklanan kod sayısı bu `N` ile
tutmalı. KAFİF self-check'iyle **aynı disiplin**: kaynağın kendi
sayımını kapı olarak kullan.

```
2024-07-01  giren 37  çıkan 21   self-check GEÇTİ
2024-12-01  giren 31  çıkan 65   self-check GEÇTİ
2025-05-01  giren 21  çıkan 36   self-check GEÇTİ
2025-10-01  giren 23  çıkan 29   self-check GEÇTİ
2026-05-01  giren 27  çıkan 19   self-check GEÇTİ
```

**5/5 geçti.** Geçmeseydi sayı düzeltilmez, sebebi araştırılırdı.

---

## 4. Geriye kurma — ve üç istisna

PDF'ler **tam liste vermiyor**, yalnız değişimi veriyor. Bileşen listesi
iki parçadan kuruldu:

```
bugünkü tam liste (KAP, endeks_uyeligi.csv, 243 kod, ölçüm 08.08.2026)
+ değişimlerin TERS uygulanması        önceki = (şimdiki − giren) ∪ çıkan
= her dönemin bileşen listesi
```

| Dönem | Üye | Panelde de var | Kaynak |
|---|---|---|---|
| 01.07.2024 – 30.11.2024 | 293 | 278 | `..._20241201_20250430.pdf` (ters) |
| 01.12.2024 – 30.04.2025 | 257 | 244 | `..._20250501_20250930.pdf` (ters) |
| 01.05.2025 – 30.09.2025 | 241 | 230 | `..._20251001_20260430.pdf` (ters) |
| 01.10.2025 – 30.04.2026 | 235 | 224 | `..._20260501_20260930.pdf` (ters) |
| 01.05.2026 – 30.09.2026 | **243** | 232 | `endeks_uyeligi.csv` (KAP) |

**En güncel dönemin çıpası PDF değil KAP'ın kendi listesi.** 01.05.2026
PDF'inin 27 girişi ve 19 çıkışı bu listeyle **birebir tutuyor** (eksik 0,
fazla 0) — yani zincirin başlangıcı bağımsız olarak doğrulanmış oldu.
01.10.2025 adımı da tam tutuyor.

### Üç tutarsızlık — hepsi açıklandı

| Kod | Girdiği dönem | Sonrası |
|---|---|---|
| EFORC | 01.05.2025 | çıkış listesinde yok, bugün üye değil |
| DAGHL, PEHOL | 01.12.2024 | aynı |

**Üçü de bugünkü evrende (795 pay kodu) YOK.** Yani borsadan çıkmışlar
(kotasyon iptali / birleşme / kod değişikliği). **Olağanüstü çıkarmalar
dönemsel değişiklik PDF'lerinde görünmez** — endeksten çıkış, dönem
revizyonunu beklemeden gerçekleşir.

Bu bir ayrıştırma hatası değil, **yöntemin bilinen sınırı**: geriye
yürüme yalnız *dönemsel* değişimleri geri alabilir. Etkisi küçük ve
ölçülü (5 dönemde 3 kod) ama **sessizce yutulmuyor** —
`kurulum_tanilari.json` her birini kaydediyor ve testi var.

---

## 5. ★ DÖNEM EŞLEMESİ — ölçüldü, varsayılmadı

Görev metni haklı olarak uyarıyordu: *"yanlış eşleme sahte uyuşmazlık
üretir."* Bu yüzden eşleme çıkarım yoluyla değil **sayarak** kuruldu.

**Ölçüt: bir revizyon ancak DUYURU tarihine kadar yayımlanmış KAFİF'leri
görebilir.** Yürürlük tarihi değil — BIST listeyi 4–7 gün önce
duyuruyor, o an veri kesilmiş oluyor.

Duyuru tarihine kadar yayımlanmış KAFİF sayısı (kümülatif, 1.280
panel satırı üzerinden):

| Endeks dönemi (duyuru) | 24/Yıllık | 25/6 Aylık | 25/9 Aylık | 25/Yıllık | 26/6 Aylık |
|---|---|---|---|---|---|
| 01.07.2024 (25.06.2024) | 0 | 0 | 0 | 0 | 0 |
| 01.12.2024 (26.11.2024) | 0 | 0 | 0 | 0 | 0 |
| 01.05.2025 (25.04.2025) | 0 | 0 | 0 | 0 | 0 |
| **01.10.2025 (24.09.2025)** | 6 | **557** | 0 | 0 | 0 |
| **01.05.2026 (27.04.2026)** | 6 | 571 | 7 | **606** | 0 |

### Eşleme tablosu

| Endeks dönemi | Yürürlük | Duyuru | Belirleyici KAFİF dönemi | Kapsam |
|---|---|---|---|---|
| 01.07.2024 – 30.11.2024 | 01.07.2024 | 25.06.2024 | *(2023/Yıllık)* | **veri yok** |
| 01.12.2024 – 30.04.2025 | 01.12.2024 | 26.11.2024 | *(2024/6 Aylık)* | **veri yok** |
| 01.05.2025 – 30.09.2025 | 01.05.2025 | 25.04.2025 | *(2024/Yıllık)* | **veri yok** |
| 01.10.2025 – 30.04.2026 | 01.10.2025 | 24.09.2025 | **2025/6 Aylık** | 557/571 |
| 01.05.2026 – 30.09.2026 | 01.05.2026 | 27.04.2026 | **2025/Yıllık** | 606/610 |
| *(01.10.2026)* | — | — | **2026/6 Aylık** | 81 (birikiyor) |

Örüntü tutarlı ve spec §5.2'nin öngördüğü pencereyle uyumlu: **6 Aylık
dalgası → o yılın Ekim revizyonu**, **Yıllık dalgası → ertesi yılın
Mayıs revizyonu**; medyan öncüllük **6–8 hafta** (2025/6 Aylık medyanı
18.08.2025 → duyuru 24.09.2025; 2025/Yıllık medyanı 06.03.2026 →
duyuru 27.04.2026).

### İki sayısal uyarı, ikisi de 4.2'yi bağlar

**(a) Yürürlük tarihini kesim noktası saymak neredeyse zararsız — ama
"neredeyse"si ölçüldü.** Duyuru ile yürürlük arasındaki 4–7 günlük
boşlukta yayımlanan KAFİF: 01.10.2025 için **1 kayıt** (KUVVA
2025/6 Aylık), 01.05.2026 için **0**. Yine de doğru ölçüt duyurudur;
boşluk bugün küçük diye yarın da küçük kalacak diye bir şey yok.

**(b) Duyurudan SONRA yayımlanan kayıtlar 18, 4.0'ın bulduğu 7 değil.**

```
01.10.2025 <- 2025/6 Aylık : duyurudan sonra 14 kayıt
                             ARENA ATEKS BALSU BJKAS BORSK DIRIT FENER
                             GSRAY KAYSE KUVVA MEPET MERKO (+2)
01.05.2026 <- 2025/Yıllık  : duyurudan sonra  4 kayıt
                             ARENA BORSK KAYSE REEDR
```

4.0 `DONEM_UYUMSUZLUGU`'nu kaba bir ölçütle ("01.05.2026'dan sonra
yayımlandı") saymış ve 7 bulmuştu. Doğru ölçüt duyuru tarihi olunca
sınıf **büyüyor**. Bu, gerçek uyuşmazlığı azaltma yönünde bir
düzeltmedir — ama **4.0'ı yeniden koşturmadım**: bu adım hipotez de
sınıflandırma da revize etmiyor, girdi üretiyor. 4.2'nin işi.

Not: futbol kulüpleri (BJKAS, FENER, GSRAY) listede beklenen yerde —
31 Mayıs kapanışı yüzünden dalganın dışına düşüyorlar (spec §1.2).

---

## 6. Çıktı — `veri/referans/xktum_bilesenler.csv`

Şema görev metnindeki gibi: `ticker, donem_baslangic, donem_bitis,
endekste_mi, kaynak_dosya`.

```
3.979 satır  ·  5 dönem  ·  EVET 1.269  ·  HAYIR 2.710
```

Üç davranış bilinçli:

- **`HAYIR` yalnız bugünkü evren (795 pay kodu) için yazılıyor.**
  Borsadan çıkmış bir kod hakkında görüşümüz yok; ona "hayır" demek
  uydurmak olurdu. `EVET` satırı kalıyor (kanıtı var): DOBUR
  (01.12.2024), EFORC · KARYE · SELGD (01.07.2024).
- **`kaynak_dosya` izlenebilirlik taşıyor:** o dönemin üyeliğini fiilen
  üreten dosya. Son dönem için `endeks_uyeligi.csv (KAP, 2026-08-08)`,
  öncekiler için ters uygulanan PDF.
- **01.07.2024'ten önceki dönem CSV'ye YAZILMADI.** Geriye yürüme onu da
  üretiyor (277 üye) ama **başlangıç tarihi bilinmiyor** — o dönemin
  PDF'i elimizde yok. Tarihsiz bir dönem "bu KAFİF gönderildiğinde
  endekste miydi" sorusuna cevap veremez, yani 4.2 onu kullanamaz.
  Sayı `kurulum_tanilari.json`'da duruyor.

---

## 7. 4.2'ye devir — üç bağlayıcı not

1. **Mutabakat penceresi 5 değil 2 dönem.** KAFİF panelimiz 05.08.2025'te
   başlıyor; 01.07.2024 / 01.12.2024 / 01.05.2025 revizyonlarının
   bileşen listesi elimizde **var** ama karşılaştıracak kararımız **yok**.
   Tarihsel mutabakat fiilen **01.10.2025 ve 01.05.2026** üzerinden
   yürüyecek. Bu, 2.0'ın "derinlik geri doldurulamaz, yalnız birikir"
   bulgusunun mutabakat tarafındaki karşılığı.
2. **`son_revizyon()` veri odaklı hâle getirilmeli** (§2). Takvim
   düzensiz ve kesim noktası duyuru tarihi.
3. **Kesim ölçütü duyuru tarihi olunca `DONEM_UYUMSUZLUGU` 7 → 18'e
   çıkıyor** (§5b). Gerçek uyuşmazlık bu yönde ancak azalır; 4.2 yeniden
   ölçmeli.

**Hiçbir hipotez revize edilmedi.** H1–H5 olduğu gibi duruyor; bu adım
yalnız referans tarafını üretti.

---

## 8. Testler

**`tests/test_xktum_referans.py` — 13 test**, iki kademeli
(`test_pilot.py` disipliniyle):

- **Fixture kademesi (her zaman koşar):** bant ayrımı (2. sayfaya taşan
  XKTUM listesi + altındaki KATILIM 100 kirlenmesinin regresyonu),
  sütun çıpasının bölüme atanması, `PAY` yapısal sözcük elemesi, geriye
  yürümenin yönü, evrende olmayan kod için `HAYIR` yazılmaması,
  tutarsızlığın raporlanması, son dönem çıpasının KAP listesi olması.
- **Kural 7 kademesi:** XKTUM bandı bulunamazsa `ReferansOkunamadi`
  fırlatılıyor ("değişiklik yok" DEĞİL); `endeks_uyeligi.csv`'de XKTUM
  satırı yoksa aynı şekilde.
- **PDF kademesi (arşiv varsa):** 5 PDF yeniden ayrıştırılıp ölçülen
  giren/çıkan sayıları ve self-check durumu karşılaştırılıyor. Arşiv
  yoksa **atlandığını duyuruyor**, sessizce geçmiyor.
- **Self-check dondurulmuş:** NO sütunu mutabakatının koddan kaldırılması
  testi kırar.

**Toplam: 183 test geçiyor** (24 motor + 9 çekici + 24 evren + 8 derinlik
+ 16 bildirim + 7 rsc + 13 toplayıcı + 9 pilot + 28 panel + 20 özet +
12 mutabakat + **13 xktum**).

`pdfplumber` yeni bağımlılık — yalnız `arac/` betiği ve onun testi
kullanıyor, `katilim/` paketi ona bağlı değil.
