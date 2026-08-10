# Nokta-Zaman Ön Mutabakat — Kararlarımız vs. XKTUM

**Plan adımı:** 4.0 — Nokta-zaman ön mutabakat
**Tarih:** 2026-08-10
**Modül:** `katilim/mutabakat.py` · CLI: `python -m katilim.cli mutabakat`
**Girdiler:** `veri/panel/snapshot_20260808.csv` · `veri/evren/endeks_uyeligi.csv`
· `veri/evren/beyan_durumu.csv` (hepsi yerel)
**Ağ isteği:** ana karşılaştırma **0**. Ek olarak onayınızla **8 + 3 = 11**
istek harcandı (aşağıda §3).

> **Bu adım hipotez REVİZE ETMEZ.** Aday listesi çıkarır; revizyon 4.3'te,
> tarihsel veriyle birlikte yapılır.

---

## 0. Sonuç — tek cümle

**Gerçek uyuşmazlık 2/518 (%0,39)** — spec §4'ün <%5 eşiğinin çok altında;
ama bu bir *nokta-zaman* ölçümdür, H1–H4'ü sınamaz ve panelin araştırma
çıktısı olma niteliğini değiştirmez.

```
UYUMLU              516
KAPSAM              259     <- uygunluk yargısı içermeyen kayıtlar
PANELDE_YOK          11     <- XKTUM üyesi, bizde kaydı yok  (§3'te çözüldü)
DONEM_UYUMSUZLUGU     7
GERCEK_UYUSMAZLIK     2     <- KLMSN, PEKGY   (ikisi de yanlış pozitif)
                    ---
                    795 pay kodu
```

---

## 1. Ön ölçüm yeniden üretildi

Sohbet içinde yapılan ön ölçümün 2×2 matrisi birebir doğrulandı
(panelde satırı olan 539 pay kodu):

| | XKTUM içinde | XKTUM dışında |
|---|---|---|
| biz UYGUN/TOLERANSTA | **230** | **21** |
| biz UYGUN_DEGIL | **2** | **286** |

21'in ayrışması: **14 KAPSAM** (pazar ön şartı yok) · **5 DÖNEM** ·
**2 GERÇEK**. 2'nin ayrışması: **DOGUB ve KCAER, ikisi de DÖNEM
UYUMSUZLUĞU** — KAFİF'leri 30.07.2026 ve 06.08.2026, son endeks
revizyonu 01.05.2026. Ön ölçümün öngörüsü doğrulandı.

---

## 2. Dört sınıf — üçü uyuşmazlık değil

Sınıflandırma sırası kodda anlamlı ve bir düzeltme içeriyor:

**KAPSAM denetimi, uyum denetiminden ÖNCE geliyor.** İlk yazımda
`BEYAN_YOK` bir şirketin XKTUM dışında olması "kararımız tuttu" sayılıyor
ve UYUMLU'ya yazılıyordu. Bu, mutabakat oranını sahte biçimde iyileştirir:
görüşümüz olmayan bir kayıt ne uyumlu ne uyumsuzdur. Düzeltmeden sonra
UYUMLU 761 → **516**, KAPSAM 14 → **259**. Testle donduruldu
(`test_kapsam_karari_gercek_uyusmazlik_sayilmaz`).

| Sınıf | Sayı | Ne demek |
|---|---|---|
| UYUMLU | 516 | karar ile üyelik örtüşüyor |
| KAPSAM | 259 | `KAPSAM_DISI`/`BEYAN_YOK`/`AYIRT_EDILEMEDI`/`BELIRSIZ`, ya da XKTUM pazar ön şartı yok |
| DÖNEM UYUMSUZLUĞU | 7 | KAFİF 01.05.2026'dan sonra yayımlandı; endeks henüz görmemiş olabilir |
| KOD AYRIŞMASI | 0 | bu turda hiç çıkmadı |
| GERÇEK UYUŞMAZLIK | 2 | üç açıklamanın hiçbiri geçerli değil |

**Uyuşmazlık oranının paydası yalnız karşılaştırılabilir kayıtlar**
(UYUMLU + GERÇEK = 518). Kapsam, dönem ve kod ayrışmasını paydaya koymak
oranı sahte biçimde düşürürdü.

---

## 3. ASIL İŞ — panelde hiç olmayan 11 XKTUM üyesi

### 3.1 Çözülen üç: MUAF ≠ ELENMİŞ

| Ticker | Durum | Çözüm |
|---|---|---|
| ALBRK, ALK | `KAPSAM_DISI` | Albaraka — katılım bankası |
| KTLEV | `KAPSAM_DISI` | Katılımevim — katılım esaslı tasarruf finansman |

Muafiyet **uygunsuzluk değil kapsam dışılıktır** ve endeks üyeliğini
engellemez. Spec §0.4 bu turda güncellenmişti; **kod aynı commit'te
takip etti**: `evren.py`'de `tasarruf finansman` kalıbı `_BELIRSIZ`'den
`_MUAF`'a taşındı, KTLEV `AYIRT_EDILEMEDI` → `KAPSAM_DISI` oldu.
`beyan_durumu.csv` yeniden üretildi (AYIRT_EDILEMEDI 33 → 26).

### 3.2 Açık sekiz: sonda sonucu **8/8 DOLU FORM**

Onayınızla `/tr/kfif/{id}-{slug}` rotasına **8 istek** yapıldı. Rota veri
kaynağı olarak hâlâ yasak; burada yalnız *"beyan var mı yok mu"* ikili
sorusu soruldu.

```
AAGYO · BETAE · GENKM · GOLDA · LXGYO · MCARD · SOHOE · SSAAT
        -> 8/8 DOLU FORM  (~125 KB, "Katılım Finansı İlkelerine Uygun Olmayan" imzası)
        -> "Bilgi Mevcut Değil" dönen: 0
```

**Bu şirketlerin KAFİF'i VAR.** Yani spec §0.4 kutusundaki (c) "kural
boşluğu" okuması — *vermediler, BIST yine de aldı* — **yanlışlandı**.

### 3.3 Mekanizma: üç okumanın hiçbiri değil, dördüncüsü

Onayınızla **3 ek istek** ile AAGYO, GENKM, SSAAT için bildirim sorgusu
**FİLTRESİZ** çekildi:

```
AAGYO : filtresiz 54 kayıt (sunucu 54) -> KAFİF 0
GENKM : filtresiz 87 kayıt (sunucu 87) -> KAFİF 0
SSAAT : filtresiz 38 kayıt (sunucu 38) -> KAFİF 0
```

Bu iki adayı birden eler:

- **DG filtresi suçlu değil** — filtresiz sorguda da KAFİF yok.
- **Bayatlık suçlu değil** — bugün (10.08) bakıldığında da yok; 1.2
  koşusundan sonra yayımlanmış bir bildirim olsaydı görünürdü.

Geriye tek açıklama kalıyor ve bu **üç okumanın hiçbiri değil**:

> **KAFİF formu var ama ona karşılık gelen BİLDİRİM yok.** Form yalnız
> şirketin kfif sayfasında yayımlanmış; bildirim akışına hiç düşmemiş.

Destekleyen bağımsız kanıt — bu 8 şirketin bildirim geçmişi **tamamen
halka arz evrakı**: İzahname (10–22 adet), Fiyat Tespit Raporu, Tasarruf
Sahiplerine Satış Duyurusu, Halka Arz Sonuçları. Hepsi **yeni halka
açılmış** şirketler. Slug kimlikleri de bunu doğruluyor: 8'in 5'i evrenin
**%98–99 diliminde** (id ≥ 6000), oysa evrenin tamamında bu dilim yalnız
%8,8 — yaklaşık 7 kat zenginleşme.

### 3.4 Bunun toplama katmanına faturası — **karar noktası**

Bildirim tabanlı toplama (1.2 → 1.4a) bu şirketleri **yapısal olarak**
göremiyor. Elimizdeki tek rota `/tr/kfif/{id}-{slug}` ve o rota:

- **gönderim zaman damgası vermiyor** → look-ahead disiplini (spec §5.1) çöker
- **4A'nın son üç satırını render etmiyor** → `b4_5/6/7` `None` kalır → her
  karar `BELIRSIZ` (ROTA_KESFI_RAPORU §6)

Yani bu 8 şirket için **karar üretilebilir bir veri yolu yok**. Seçenekler
(hiçbirini kendi başıma seçmedim):

- **(a) Kapsam sınırı olarak kabul et:** panel "bildirim yayımlamış
  şirketleri" kapsar, bunu belgele. XKTUM'un 243 üyesinin 8'i (%3,3)
  panel dışında kalır.
- **(b) kfif rotasından kısıtlı kayıt üret:** oranlar ve 10 beyan alınır,
  3 beyan `None` kalır, karar `BELIRSIZ` olur. Zaman damgası olmadığı için
  **tarihsel panele giremez**, yalnız "bugün" tablosunda durur.
- **(c) Kaynak ara:** bu formların bildirim karşılığı gerçekten yok mu,
  yoksa başka bir rotada mı (ör. halka arz izahname eki) — ek keşif.

---

## 4. İki gerçek uyuşmazlık

Her ikisi de **yanlış pozitif**: biz uygun diyoruz, BIST dışarıda
bırakmış. Bu, kaçırılan fırsattan pahalı olan hata sınıfı.

### KLMSN — tolerans zincirinin yokluğu

```
2025/6 Aylık  13.08.2025  TOLERANSTA  [G5_GELIR_TOLERANS, G7_BORC_TOLERANS]  borç 33,17
2025/Yıllık   11.03.2026  TOLERANSTA  [G7_BORC_TOLERANS]                     borç 34,98
```

Spec §2.1: *"aşım var (herhangi bir miktarda) ve önceki dönem TOLERANSTA
→ UYGUN_DEGIL."* KLMSN **iki dönem üst üste TOLERANSTA.** Zincir
uygulansaydı ikinci dönem `UYGUN_DEGIL` olurdu ve **BIST'le uyuşurdu.**

Snapshot panelinde tolerans zinciri yok (1.4b, bilinçli: 3.1'in işi).

**Ölçüm — zincir uygulansa ne olurdu:** 5 kayıt `TOLERANSTA` → `UYGUN_DEGIL`
olurdu (ALVES, DCTTR, DOGUB, KLMSN, KONTR). Bunlardan **2'si şirketin en
güncel kaydı**:

| Ticker | Zincirsiz | Zincirli | XKTUM | Etki |
|---|---|---|---|---|
| KLMSN | TOLERANSTA | UYGUN_DEGIL | dışında | uyuşmazlık **çözülür** |
| DCTTR | TOLERANSTA | UYGUN_DEGIL | **içinde** | **yeni uyuşmazlık doğar** |

Yani zincir bir uyuşmazlığı kapatıp bir yenisini açıyor; net sayı değişmiyor.
**H4 (tolerans şirket bazında) bu veriyle onaylanmış sayılmaz** — 3.1
koştuktan sonra 4.2'de tarihsel veriyle yeniden bakılmalı.

### PEKGY — H3 adayı veya modellenmemiş yeniden giriş kuralı

```
2025/6 Aylık  07.08.2025  UYGUN_DEGIL [G7_BORC]  borç 36,73   (tolerans bandı %36,3'ü aşıyor)
2025/Yıllık   18.03.2026  UYGUN                  borç 20,88
2025/Yıllık   03.04.2026  UYGUN  (düzeltme)      borç 20,88
```

6 Aylık formda borç oranı bandın da üstünde → 01.10.2025 revizyonunda
elenmiş olması beklenir. Yıllık formda oran %20,88'e inmiş; 01.05.2026
revizyonunda **yeniden girmesi** beklenirdi, girmemiş.

İki aday açıklama, ikisi de 4.3'ün konusu:
- **H3** — BIST paydası `max(ort. PD, toplam varlık)`; farklı payda farklı
  oran verir (spec §0.2).
- **Modellenmemiş yeniden giriş kuralı** — endeksten çıkan payın geri
  alınması ek koşula bağlı olabilir. Spec'te böyle bir kural yok.

---

## 5. H5 sınanmadı — ve sınanamaz

`h5_ayirt_edici` işaretli 19 kaydın yalnız 1'i farklı *karar* üretiyor
(PNLSN 2025/6 Aylık) ve o da geçersiz kılınmış bir düzeltme; §3.2 gereği
geçerli olan en geç kayıtta iki oran aynı kararı veriyor. **Ayırt edici
örneklem n=0.** H5 bu veriyle sınanamıyor; varsayılan (özet alanı)
yanlışlanmamış bir yargı çağrısı olarak duruyor.

### Bunun yerine ölçülen: oran ayrışması ↔ düzeltme

| Ölçüt | Değer |
|---|---|
| `oran_ayrisiyor` kayıt | 22 |
| bunların düzeltme olanı | 5 (**%22,7**) |
| panel genelinde düzeltme oranı | %14,8 |

Ayrışan kayıtlarda düzeltme oranı ~1,5 kat yüksek. **Ama n=22 ve beklenen
sayı 3,3 iken gözlenen 5 — bu fark tesadüfle açıklanabilir.** PNLSN'de
mekanizma doğrulanmıştı (şirket kalemi düzeltmiş, TOPLAM satırını
güncellememiş); bu örüntünün **genel olduğu gösterilemedi.**

2.3 için not: düzeltme çözümlenirken "formun özeti bayat olabilir"
ihtimali hesaba katılmalı; kanıt henüz zayıf.

---

## 6. Harcanan istek

| Amaç | İstek | Onay |
|---|---|---|
| Ana karşılaştırma | 0 | — |
| kfif ikili sondası (8 isim) | 8 | onaylandı |
| Filtresiz bildirim sorgusu (3 isim) | 3 | onaylandı |
| **Toplam** | **11** | |

`BütçeAşıldı` tetiklenmedi. Sonda gövdeleri önbelleğe **yazılmadı**
(`onbellekle=False`): yasak rotanın gövdesi arşive karışmasın diye.

---

## 7. 4.3'e taşınan aday listesi

Bu adım hiçbir hipotezi revize etmedi. Adaylar:

| Aday | Kanıt | Nereye |
|---|---|---|
| **H4** (tolerans şirket bazında) | Zincir KLMSN'i düzeltiyor, DCTTR'yi bozuyor | 3.1 koştuktan sonra 4.2 |
| **H3** (payda) | PEKGY yeniden girmedi | 4.3, PD verisiyle |
| **Yeniden giriş kuralı** modellenmemiş olabilir | PEKGY | spec'e aday madde |
| **Kapsam sınırı**: bildirimsiz form | 8 şirket, 8/8 dolu form | karar noktası §3.4 |
| H5 | örneklem yok | 4.3'te değil, panel derinleştikçe |

**Testler: 151 geçiyor** (önceki 138 + 12 mutabakat + 1 evren).
