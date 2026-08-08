# Snapshot Panel — Ayrıştırma Raporu

**Plan adımı:** 1.4b — Ayrıştırma ve panel
**Tarih:** 2026-08-08
**Modül:** `katilim/panel.py` · CLI: `python -m katilim.cli panel`
**Çıktı:** `veri/panel/snapshot_20260808.csv` (1.280 satır × 25 sütun)
**Ağ isteği: 0.** Her şey diskten; yanlış çıkarsa düzeltilip yeniden koşulur.

---

## 0. Özet

```
arşivdeki form            : 1.276     ayrıştırma HATASI: 0   dosyası yok: 0
panel satırı (ticker × bildirim) : 1.280
panelde satırı olan pay kodu     :   539
self-check                : GEÇTİ 1.258 / KALDI 22  -> karantina 22
şablon imzası             : tek (4A|4B|4C|4D|4E|5F|5G|5H|6I|6J|OZET|S1|S2|S3)
gönderim aralığı          : 05.08.2025 19:16 .. 07.08.2026 18:32
```

Panel satırı (1.280) ile bildirim sayısı (1.276) farkı çoklu pay kodundan:
iki bildirim üçer koda dağıtıldı. **İndirme tekti, panel satırı üç** —
panel ekseni ticker, indirme ekseni bildirim (1.1'in iki eksen kuralı).

---

## 1. Şirket ve bildirim sayıları

| Ölçüt | Sayı |
|---|---|
| Evrendeki pay kodu | 795 |
| Panelde satırı olan (en az bir KAFİF) | **539** |
| `BEYAN_YOK` — muaf değil, beyan vermemiş | **73** |
| `AYIRT_EDILEMEDI` — muafiyeti belirsiz **ve** beyanı yok | **33** |
| `KAPSAM_DISI` — mali sektör muafı, sorgulanmadı | 150 |

Kaynak: `veri/evren/beyan_durumu.csv` (1.4a). Toplam 795 = 539 + 73 + 33 + 150.

**`AYIRT_EDILEMEDI` hâlâ `MUAF` değil.** Bu rotadan muaf olan ile beyan
vermeyen ayırt edilemiyor; ikisinden birini varsaymak yerine durum böyle
duruyor. Ayrım 1.1b'nin sektör alanıyla kapanabilir.

Panelde `KAPSAM_DISI` kararı **hiç yok**: KAFİF veren 539 pay kodunun
hiçbiri muaf işaretli değil. Yani muafiyet sınıflaması ile beyan davranışı
bu turda çelişmedi.

### Dönem dağılımı

| Dönem | Satır |
|---|---|
| 2025/Yıllık | 610 |
| 2025/6 Aylık | 571 |
| 2026/6 Aylık | 81 |
| 2025/9 Aylık | 7 |
| 2024/Yıllık | 6 |
| 2026/3 Aylık | 4 |
| 2025/3 Aylık | 1 |

Nitelik: 875 Konsolide · 405 Konsolide Olmayan. Düzeltme bildirimi: 190.

---

## 2. Karar dağılımı — iki sütun

`karar` **ÖZET alanından** üretiliyor (H5 varsayılanı), `karar_kalem_bazli`
kalemlerden. İkisi yan yana duruyor ki 4.0 hangisinin BIST'le uyuştuğunu
sorabilsin.

| Karar | ÖZET (`karar`) | kalem (`karar_kalem_bazli`) |
|---|---|---|
| UYGUN_DEGIL | 655 | 655 |
| UYGUN | 582 | 583 |
| TOLERANSTA | 43 | 42 |
| BELIRSIZ | 0 | 0 |
| KAPSAM_DISI | 0 | 0 |

**Tolerans zinciri YOK.** Bu bir snapshot: her kayıt kendi başına
değerlendirildi, `onceki_donem_toleransta` hep `False`. Dönemler arası
tolerans taşınması 3.1'in işi ve `karar.py:187`'deki bozuk sıralama
anahtarı orada düzeltilecek.

`BELIRSIZ` sayısının sıfır olması, 1.276 formun hepsinde 13/13 beyanın
dolu olmasından (1.3 ölçümü). Eksik beyan çıksaydı kural 2 gereği
`BELIRSIZ` üretilecekti.

---

## 3. H5 — iki oranın ayrıştığı kayıtlar

```
oran_ayrisiyor  : 22   (self-check'in kaldığı her kayıt)
h5_ayirt_edici  : 19   (iki oran da TANIMLI ve TOLERANS'ı aşan fark var)
karar çeviren   :  1
```

**Ayrım önemli.** 22 kaydın 3'ünde kalem oranı `None` (4E = 0, oran
tanımsız; form 0 basıyor). Bunlar karantinaya girer ama **H5'i sınamaz**:
biri tanımsızken "BIST hangi oranı kullanıyor" sorusuna cevap veremezler.
`h5_ayirt_edici` bu yüzden 22 değil 19.

**Kararı fiilen çeviren tek kayıt:**

```
PNLSN 2025/6 Aylık   özet %5,30 -> TOLERANSTA      (H5 kabul edilirse)
                     kalem %4,67 -> UYGUN          (aritmetiği doğru olan)
```

Yani H5'in sınanabileceği fiili örneklem **n=1**. 4.0'da bu tek satır
BIST'in XKTUM üyeliğiyle karşılaştırılacak; tek gözlemle H5 "doğrulandı"
sayılmayacak (spec §2.3'ün uyarısı).

### Karantinaya alınan 22 kayıt

`karantina=EVET` sütunuyla panelde **duruyorlar, silinmediler.** Silmek 22
şirketi sessizce düşürmek olurdu; işaretsiz bırakmak kural 1'i çiğnerdi.
Aşağı akış bu sütunla süzer.

| Ticker | Dönem | H5 ayırt edici | kalem % | özet % | karar (özet) | karar (kalem) |
|---|---|---|---|---|---|---|
| AVOD | 2025/6 Aylık | EVET | 10,11 | 11,92 | UYGUN_DEGIL | UYGUN_DEGIL |
| AYCES | 2025/Yıllık | EVET | 0,91 | 0,94 | UYGUN_DEGIL | UYGUN_DEGIL |
| BRYAT | 2025/Yıllık | EVET | 2,50 | 0,71 | UYGUN_DEGIL | UYGUN_DEGIL |
| CASA | 2025/6 Aylık | HAYIR | — | 0 | UYGUN | UYGUN |
| DOFER | 2025/6 Aylık | EVET | 1,61 | 1,65 | UYGUN | UYGUN |
| DOHOL | 2025/6 Aylık | EVET | 35,14 | 35,08 | UYGUN_DEGIL | UYGUN_DEGIL |
| DOHOL | 2025/Yıllık | EVET | 35,83 | 35,85 | UYGUN_DEGIL | UYGUN_DEGIL |
| DURKN | 2025/6 Aylık | EVET | 13,13 | 13,30 | UYGUN_DEGIL | UYGUN_DEGIL |
| GIPTA | 2025/Yıllık | EVET | 22,60 | 22,76 | UYGUN_DEGIL | UYGUN_DEGIL |
| ISGYO | 2025/Yıllık | HAYIR | — | 0 | UYGUN_DEGIL | UYGUN_DEGIL |
| ISGYO | 2026/6 Aylık | HAYIR | — | 0 | UYGUN_DEGIL | UYGUN_DEGIL |
| LUKSK | 2025/6 Aylık | EVET | 18,28 | 20,80 | UYGUN_DEGIL | UYGUN_DEGIL |
| **PNLSN** | **2025/6 Aylık** | **EVET** | **4,67** | **5,30** | **TOLERANSTA** | **UYGUN** |
| PNLSN | 2025/6 Aylık | EVET | 4,75 | 4,77 | UYGUN | UYGUN |
| PNLSN | 2025/Yıllık | EVET | 17,05 | 17,09 | UYGUN_DEGIL | UYGUN_DEGIL |
| TAVHL | 2026/6 Aylık | EVET | 11,73 | 12,79 | UYGUN_DEGIL | UYGUN_DEGIL |
| TOASO | 2026/3 Aylık | EVET | 7,49 | 6,07 | UYGUN_DEGIL | UYGUN_DEGIL |
| TRENJ | 2025/Yıllık | EVET | 11,83 | 11,87 | UYGUN_DEGIL | UYGUN_DEGIL |
| TRMET | 2025/Yıllık | EVET | 10,99 | 11,03 | UYGUN_DEGIL | UYGUN_DEGIL |
| TSGYO | 2026/6 Aylık | EVET | 24,79 | 24,83 | UYGUN_DEGIL | UYGUN_DEGIL |
| ULAS | 2025/6 Aylık | EVET | 1,56 | 1,46 | UYGUN | UYGUN |
| VBTYZ | 2025/6 Aylık | EVET | 7,63 | 7,80 | UYGUN_DEGIL | UYGUN_DEGIL |

Sebep 1.3'te teşhis edildi: 19'unda **formun kendi 4E TOPLAM satırı kendi
kalemleriyle tutmuyor**, 3'ünde 4E = 0. Parser hatası yok. `TOLERANS`
gevşetilmedi (`tests/test_pilot.py::test_tolerans_gevsetilmemis` donduruyor).

---

## 4. Şablon imzası dağılımı

```
4A|4B|4C|4D|4E|5F|5G|5H|6I|6J|OZET|S1|S2|S3   ->  1.280 / 1.280
```

**Tek imza.** 2.2 (şablon versiyonlama) bu veriyle tek etiket üretecek;
modül yine gerekli, çünkü sonraki revizyonda devreye girecek. **2024
öncesi şablon bu pencerede yok**, dolayısıyla sınanmadı (1.3 §5).

---

## 5. Dönem anahtarı — meta veriden

`yil` ve `periyot` sütunları **bildirim meta verisinden** (arşiv indeksi)
geliyor. Formun kendi etiketi ayrı bir sütunda taşınıyor:

```
form_donem_etiketi meta veriden ayrışan satır: 20 / 1.280
  "Yıllık"  -> "4. 3 Aylık Bildirim"   13
  "6 Aylık" -> "2. 3 Aylık Bildirim"    7
YIL uyuşmazlığı: 0
```

Anahtar tek olduğu için panel bu 20 kayıtta da tutarlı. Sıralama
`gonderim_ts` ile yapılıyor — dönem etiketi kronoloji taşımıyor (futbol
kulüpleri "2024/Yıllık"ı Ağustos 2025'te veriyor).

---

## 6. Kodda kalan davranış

- **Ticker artık dosya adından tahmin edilmiyor.** Arşiv indeksi bildirim
  başına tüm pay kodlarını taşıyor ve bunlar evren tablosundan geliyor;
  `ayristir_arsiv` ayrıca evrende olmayan kodu raporluyor (bu koşuda 0).
  **OKUBENI'nin "ticker dosya adından tahmin ediliyor" açığı kapandı.**
- **Dosya listesi dizin taramasından değil indeksten.** İndekste olup
  diskte olmayan dosya sessizce atlanmıyor, `dosyasi_yok` olarak
  raporlanıyor (bu koşuda 0). İndeks yoksa `ArsivOkunamadi` fırlatılıyor —
  "kayıt yok" ile "arşiv okunamadı" ayrı (kural 7).
- **Karantina silmez, işaretler.** `karantina` + `karantina_sebebi`
  sütunları.
- **Muafiyet `None` iken muaf sayılmıyor** (1.1'in asimetri kuralı).
- **Tolerans zinciri yok** — snapshot; 3.1'in işi.

**Testler: 118 geçiyor** (22 motor + 9 çekici + 23 evren + 8 derinlik +
15 bildirim + 7 rsc + 13 toplayıcı + 9 pilot + 12 panel). Yeni:
`tests/test_panel.py` — H5 iki karar, tanımsız oranın ayırt edici
sayılmaması, karantinanın silinmemesi, dönem anahtarının meta veriden
gelmesi, çoklu kodun iki satır üretmesi, indeks yokluğunda hata.

---

## 7. Sıradaki adım için not

Panel **araştırma çıktısıdır, karar dayanağı değildir** (spec §4): H1–H5
hâlâ doğrulanmamış. 4.0 (nokta-zaman ön mutabakat) artık koşulabilir —
girdisi olan `endeks_uyeligi.csv` 1.1b'den gelecek.

`h5_ayirt_edici=EVET` olan 19 satır ve özellikle karar çeviren tek PNLSN
kaydı, 4.0'ın doğrudan sorgulayacağı alt küme.
