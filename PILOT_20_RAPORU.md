# Parser Doğrulama — 20/20 Kapısı

**Plan adımı:** 1.3 — 20/20 parser kapısı
**Tarih:** 2026-08-08
**Betik:** `arac/pilot_20.py` (tek seferlik) · **Ağ isteği: 0**
**Kalıcı çıktı:** `tests/fixtures/pilot/` (20 JSON) · `tests/test_pilot.py` (9 test)
**Ham ölçüm:** `veri/onbellek/pilot_tarama.json` (1.276 form)

---

## 0. Sonuç

**Kapı geçildi.** 20 formun 13'ünde self-check GEÇTİ, 7'sinde KALDI — ve
**KALAN 7'nin 7'si de teşhis edildi.** Teşhis edilemeyen sapma yok, dolayısıyla
karantinada açıklanmamış kayıt yok.

Kritik nokta: **KALAN kayıtların sebebi parser değil.** Yedisinde de sapmanın
kaynağı, formun kendi TOPLAM satırının kendi kalemleriyle tutmaması. Yani
self-check, tasarlandığı işi yaptı: **formun kendi aritmetiğini denetledi**
(CLAUDE.md kural 3).

Örneklem 20 ile sınırlı değil: seçimden önce **arşivin tamamı (1.276 form)**
ayrıştırıldı, çünkü "solo mu", "düzeltme mi", "küçük mü" soruları ancak
ayrıştırdıktan sonra cevaplanabiliyor.

```
1.276 form · ayrıştırma HATASI: 0 · self-check GEÇTİ 1.254 / KALDI 22  (%98,3)
```

---

## 1. Örneklem — 20 form

Hepsinin şablon imzası aynı: `4A|4B|4C|4D|4E|5F|5G|5H|6I|6J|OZET|S1|S2|S3`
(§2). Sütun tekrarı olmasın diye tablodan çıkarıldı.

| Ticker | Dönem (bildirim) | Nitelik | Self-check | Karar |
|---|---|---|---|---|
| TSPOR | 2024/Yıllık | Konsolide | GEÇTİ | UYGUN_DEGIL [G4_DOGRUDAN_AYKIRI] |
| BOBET | 2025/3 Aylık | Konsolide | GEÇTİ | UYGUN_DEGIL [G5_GELIR] |
| ASELS | 2025/6 Aylık | Konsolide | GEÇTİ | UYGUN |
| THYAO | 2025/6 Aylık | Konsolide | GEÇTİ | UYGUN_DEGIL [G4_DOGRUDAN_AYKIRI] |
| ISBIR | 2025/6 Aylık | Konsolide | GEÇTİ | UYGUN |
| TRGYO | 2025/6 Aylık | Konsolide | GEÇTİ | UYGUN_DEGIL [G4_DOGRUDAN_AYKIRI] |
| EDATA | 2025/6 Aylık | Konsolide Olmayan | GEÇTİ | UYGUN |
| GMTAS | 2025/6 Aylık | Konsolide Olmayan | GEÇTİ | UYGUN_DEGIL [G4_DOGRUDAN_AYKIRI] |
| HATSN | 2025/6 Aylık | Konsolide Olmayan | GEÇTİ | UYGUN |
| IZENR | 2025/6 Aylık | Konsolide Olmayan | GEÇTİ | UYGUN_DEGIL [G2_IMTIYAZ] |
| KTSKR | 2025/6 Aylık | Konsolide Olmayan | GEÇTİ | UYGUN_DEGIL [G5_GELIR] |
| VRGYO | 2025/6 Aylık | Konsolide Olmayan | GEÇTİ | UYGUN |
| FMIZP | 2025/9 Aylık | Konsolide Olmayan | GEÇTİ | UYGUN_DEGIL [G6_VARLIK] |
| **AVOD** | 2025/6 Aylık | Konsolide | **KALDI** | UYGUN_DEGIL [G5_GELIR] |
| **DOHOL** | 2025/6 Aylık | Konsolide | **KALDI** | UYGUN_DEGIL [G1_ESAS_SOZLESME] |
| **PNLSN** | 2025/6 Aylık | Konsolide Olmayan | **KALDI** | UYGUN |
| **PNLSN** | 2025/6 Aylık *(düzeltme)* | Konsolide Olmayan | **KALDI** | UYGUN |
| **VBTYZ** | 2025/6 Aylık | Konsolide | **KALDI** | UYGUN_DEGIL [G5_GELIR] |
| **ISGYO** | 2025/Yıllık | Konsolide Olmayan | **KALDI** | UYGUN_DEGIL [G1_ESAS_SOZLESME] |
| **ISGYO** | 2026/6 Aylık | Konsolide Olmayan | **KALDI** | UYGUN_DEGIL [G1_ESAS_SOZLESME] |

### Örneklem "zoru" kapsıyor mu — plan 1.3 şartları

| Şart | Durum |
|---|---|
| en az 3 solo (konsolide olmayan) | ✔ **11** |
| en az 3 farklı sektör | ✔ **8** vekil sınıf (GYO, perakende, enerji, holding, gıda, teknoloji, ulaştırma, sanayi) |
| en az 2 küçük şirket (tablolar kısmen boş) | ⚠ **vekil ölçütle** — aşağıya bakın |
| en az 2 tanesi 2025/6 Aylık | ✔ **15** |
| en az 1 düzeltme bildirimi | ✔ **3** |
| *(eklendi)* özel hesap dönemi | ✔ 2024/Yıllık, 3 Aylık, 9 Aylık |
| *(eklendi)* farklı para birimi çarpanı | ✔ 1 · 1.000 · 1.000.000 |

**"Kalem sayısı az" ölçütü bu pencerede tanım gereği sağlanamıyor.** Ölçüm:
1.276 formun **1.276'sında 55 kalem** var — şablon boş kalemleri de 0 olarak
basıyor. Ölçüt vekil hâle getirildi: *dolu (sıfır olmayan) kalem sayısı*.
Örneklemdeki iki ISGYO kaydı **55 kalemin yalnız 1'i dolu** — "tabloları
kısmen boş" tanımının bu penceredeki en uç karşılığı bu.

**Sektör sınıflaması unvandan türetilmiş vekildir, resmî kaynak değildir.**
`sirketler.csv`'nin `sektor` alanı hâlâ boş (1.1b koşulmadı). Rapor bunu
"sektör doğrulandı" saymıyor; yalnız örneklem çeşitliliği için kullanıldı.

---

## 2. Şablon imzaları — tek revizyon

```
4A|4B|4C|4D|4E|5F|5G|5H|6I|6J|OZET|S1|S2|S3    ->  1.276 / 1.276
```

**Arşivin tamamında tek imza var.** 2.0'ın öngördüğü buydu: 1 yıllık pencere
tek şablon revizyonuna denk geliyor. 2.2 (şablon versiyonlama) bu veriyle
tek etiket üretecek — modül yine gerekli, çünkü sonraki revizyonda devreye
girecek.

`tests/test_pilot.py::test_tek_sablon_imzasi` bunu dondurdu: ikinci bir imza
çıkarsa test kırılır ve bu bir **bulgu** olarak ele alınır (imza silinmez).

---

## 3. Self-check kalan kayıtlar — teşhis

Arşiv genelinde 22, örneklemde 7. **Hepsi teşhis edildi, iki sınıfa ayrıldı.**

### 3.1 Formun kendi TOPLAM satırı kalemleriyle tutmuyor (19 kayıt)

Teşhis yöntemi: formun bastığı TOPLAM satırları **yalnız teşhis için**
okundu (üretimde kural 3 gereği okunmuyor) ve özet oran bu değerlerle
yeniden hesaplandı.

**19 kaydın 19'unda özet oran, formun TOPLAM satırlarıyla birebir tutuyor.**
Yani form, oranını kendi TOPLAM satırından hesaplamış; o satır ise kendi
kalemlerinin toplamı değil. Sapma her seferinde **yalnız 4E'de** (toplam
gelir); 4B/4C/4D tutarlı, varlık ve borç oranları da birebir tutuyor.

En açıklayıcı vaka — PNLSN 2025/6 Aylık (düzeltme çifti):

```
kalemler       : 1.185.326.913 + 100.284.619 + 5.627.500 + 59.342.077 = 1.350.581.109
formun TOPLAMı :                                                        1.345.259.702
fark           :                                                            5.321.407
```

Fark, aynı şirketin **düzeltme öncesi** formundaki "Finansman Gelirleri"
(306.093) ile düzeltme sonrası değeri (5.627.500) arasındaki farkın ta
kendisi: şirket kalemi düzeltmiş, **TOPLAM satırını güncellememiş.** Özet
oran eski toplamdan hesaplanmış.

**Bu, parser hatası değil, kaynaktaki veri tutarsızlığıdır** — ve kural 3'ün
("TOPLAM satırları okunmaz, toplam hesaplanır") tam olarak yakalamak için
var olduğu şeydir. TOPLAM satırını parse ediyor olsaydık bu 19 form sessizce
"tutarlı" görünecekti.

| Ticker | Dönem | Bizim (kalem) | Formun özeti | 4E kalem−TOPLAM farkı |
|---|---|---|---|---|
| AVOD | 2025/6 Aylık | 10,11 | 11,92 | 145.827.318 |
| AYCES | 2025/Yıllık | 0,91 | 0,94 | 1.700.000 |
| BRYAT | 2025/Yıllık | 2,50 | 0,71 | −4.226.273.978 |
| DOFER | 2025/6 Aylık | 1,61 | 1,65 | 63.721.367 |
| DOHOL | 2025/6 Aylık | 35,14 | 35,08 | −98.671 |
| DOHOL | 2025/Yıllık | 35,83 | 35,85 | 80.994 |
| DURKN | 2025/6 Aylık | 13,13 | 13,30 | 7.910.658 |
| GIPTA | 2025/Yıllık | 22,60 | 22,76 | 21.305.708 |
| LUKSK | 2025/6 Aylık | 18,28 | 20,80 | 34.778.215 |
| PNLSN | 2025/6 Aylık | 4,67 | 5,30 | 159.626.696 |
| PNLSN | 2025/6 Aylık | 4,75 | 4,77 | 5.321.407 |
| PNLSN | 2025/Yıllık | 17,05 | 17,09 | 7.668.580 |
| TAVHL | 2026/6 Aylık | 11,73 | 12,79 | 4.048.088.000 |
| TOASO | 2026/3 Aylık | 7,49 | 6,07 | −24.640.004 |
| TRENJ | 2025/Yıllık | 11,83 | 11,87 | 76.830 |
| TRMET | 2025/Yıllık | 10,99 | 11,03 | 76.937 |
| TSGYO | 2026/6 Aylık | 24,79 | 24,83 | 638.366 |
| ULAS | 2025/6 Aylık | 1,56 | 1,46 | −4.023.874 |
| VBTYZ | 2025/6 Aylık | 7,63 | 7,80 | 25.648.372 |

### 3.2 4E = 0, oran tanımsız (3 kayıt)

CASA 2025/6 Aylık · ISGYO 2025/Yıllık · ISGYO 2026/6 Aylık.

Toplam gelir tablosu tamamen sıfır → oran **tanımsız**; parser `None`
üretiyor, form ise `0` basıyor. Self-check `None ≠ 0` dediği için KALDI.

**Davranış bilinçli olarak değiştirilmedi.** "Tanımsız" ile "sıfır" aynı şey
değil; `None`'ı 0 saymak, kural 2'nin (eksik beyan ≠ hayır beyanı) oran
tarafındaki karşılığını çiğnerdi. Bu üç kayıt karantinada kalır ve kararları
zaten başka kapıdan veriliyor (ISGYO ikisinde de G1).

### 3.3 TOLERANS gevşetilmedi

`TOLERANS = 0,01` yerinde. `tests/test_pilot.py::test_tolerans_gevsetilmemis`
sabiti dondurdu; değiştirilirse test kırılır.

---

## 4. `is_duzeltme` DOĞRULANDI (OKUBENI açığı kapandı)

OKUBENI "bilinen açıklar": *"`is_duzeltme` tespiti sayfa metninde 'düzeltme'
araması yapıyor; gerçek bir düzeltme bildirimiyle doğrulanmadı."*

Referans: aynı (ticker, yıl, periyot) grubunda **ilk olmayan** bildirim
(1.2 §7'nin 163 tekrar grubu).

```
referans (grubunun ilki olmayan)  : 181
parser is_duzeltme=True & referans: 181     <- KAÇIRILAN: 0
parser True ama referansta yok    :   9
```

**Kaçırma yok.** 9 "fazla" işaretin hepsi 2025/6 Aylık ve pencerenin en eski
ucunda (07.08–15.09.2025). Bunlar yanlış pozitif değil: düzelttikleri asıl
bildirim keşif penceresinin dışında kaldığı için grup referansımızda
görünmüyorlar. Sayfanın kendi metni bunu doğruluyor:

```
"... Düzeltilmiş Bildirim ... Düzeltme Nedeni: Sehven yapılan hataların düzeltilmesi ..."
```

**Yan bulgu:** KAP formda ayrıca **"Düzeltme Nedeni"** serbest metni basıyor
("Revize", "Sehven yapılan hataların düzeltilmesi", …). 2.3 için değerli;
şu an modelde alan yok.

---

## 5. Kapsam dışı — sınandı sayılmayanlar

- **2024 öncesi şablon SINANMADI.** Bu pencereden çekilemiyor (2.0: erişim
  1 yılla sınırlı, geri doldurma yolu yok). CLAUDE.md kural 4'teki
  "1. bölüm 3 sorudan 2'ye indi" revizyonu **bu turda test edilemedi**;
  arşivdeki en eski form 05.08.2025 tarihli ve hepsi tek imzayı taşıyor.
  Eski şablon ancak ikincil kaynakla (plan 4.1, BIST dönemsel değişiklik
  PDF'leri) veya KAP başka bir rota açarsa sınanabilir.
- **Sektör sınıflaması resmî değil** (§1). 1.1b koşulunca gerçek sektörle
  yeniden bakılmalı.
- **Karar doğruluğu sınanmadı.** Bu adım parser'ı doğruladı; kararların
  BIST'in fiilî seçimleriyle uyumu Faz 4'ün işi. H1–H4 hâlâ doğrulanmamış.

---

## 6. Aşağı akışı bağlayan iki bulgu

### 6.1 Formun dönem sözlüğü, bildirim meta verisinden farklı olabiliyor

```
1.276 formun 20'sinde formun kendi etiketi ile bildirim meta verisi ayrışıyor:
  meta "Yıllık"  -> form "4. 3 Aylık Bildirim"   13 form
  meta "6 Aylık" -> form "2. 3 Aylık Bildirim"    7 form
YIL uyuşmazlığı: 0
```

İkisi de aynı dönemi kastediyor (4. çeyrek = yıllık, 2. çeyrek = 6 aylık),
ama panel anahtarı tek olmalı. **Öneri: panel dönem anahtarı bildirim meta
verisinden (`bildirim_gecmisi.csv`) alınsın**, formun iç etiketinden değil —
meta veri 1.276 formda tutarlı. Kod değişikliği 1.4b'de, karar sizin.

### 6.2 Hangi oran karara girecek — **karar noktası**

§3.1'deki 19 kayıtta iki oran var: bizim kalemlerden hesapladığımız ve
formun özetinde yazan. Çoğunda fark kararı değiştirmiyor, **ama en az
birinde değiştiriyor:**

```
PNLSN 2025/6 Aylık   bizim 4,67 %  -> UYGUN        (limit %5'in altında)
                     form  5,30 %  -> aşım         (%5–5,5 bandı: TOLERANSTA)
```

BIST muhtemelen formun **özet alanını** kullanıyor (beyan esaslı sistem).
Biz kalemlerden hesaplıyoruz ve aritmetiği daha doğru; ama "daha doğru
olan" ile "endeksin fiilen kullandığı" farklı şeyler olabilir. Bu, Faz 4
mutabakatında sınanacak bir ayrışma kaynağıdır ve **şimdi kod içinde
seçilmemeli.** Panelde her iki oranı da taşımak (hesaplanan + özet) en
güvenli yol; öneriyorum ama uygulamadım.

---

## 7. Kalıcı çıktı ve test katmanı

`tests/fixtures/pilot/` — 20 JSON, her biri: ayrıştırılmış tam bildirim +
beklenen üç oran + özet oranlar + karar + şablon imzası + seçim gerekçesi.

`tests/test_pilot.py` (9 test) **iki kademe** çalışır:

1. **Fixture kademesi (her zaman):** oranlar JSON'dan yeniden hesaplanır,
   karar motoru yeniden koşulur, self-check durumu ve TOLERANS dondurulur.
   `veri/ham/` olmadan da anlamlı — taze klonda da koşar.
2. **Arşiv kademesi (arşiv varsa):** 20 ham HTML yeniden ayrıştırılıp
   fixture ile karşılaştırılır. Ayrıştırıcı gerilemesini yalnız bu yakalar.
   Arşiv yoksa test **atlandığını duyurur**, sessizce geçmez.

Bu koşuda ikinci kademe de çalıştı: **20/20 ham HTML'den yeniden ayrıştırıldı.**

**Testler: 106 geçiyor** (22 motor + 9 çekici + 23 evren + 8 derinlik +
15 bildirim + 7 rsc + 13 toplayıcı + 9 pilot).
