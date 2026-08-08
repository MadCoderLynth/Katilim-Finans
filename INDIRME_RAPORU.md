# KAFİF Form Arşivi — İndirme Raporu

**Plan adımı:** 1.4a — Tam evren form çekimi (yalnız indirme, ayrıştırma yok)
**Tarih:** 2026-08-07 / 08
**Modül:** `katilim/toplayici.py` · CLI: `python -m katilim.cli indir`
**Çıktı:** `veri/ham/` (1.276 form, 239 MB) · `veri/ham/arsiv_indeksi.csv` ·
`veri/evren/beyan_durumu.csv`
**Bütçe:** onaylanan 2.600. **Harcanan 1.273 başarılı çekim + 373 yeniden
deneme ≈ 1.646 HTTP denemesi.** `BütçeAşıldı` tetiklenmedi, bütçe yükseltilmedi.

---

## 0. Özet

**1.276 formun 1.276'sı arşivde.** Eksik yok, kalıcı hata (404) yok.

```
bildirim_gecmisi.csv benzersiz kimlik : 1.276
diskte dosyası olan kimlik            : 1.276
EKSİK                                 : 0
FAZLA (kimliksiz dosya)               : 0
50 KB altı şüpheli dosya              : 0
sha256 yeniden doğrulama (30 örnek)   : hepsi tuttu
```

Bu adım **ayrıştırmadı.** Parser'a dokunulmadı, dolayısıyla 1.3'ün 20/20
kapısı beklenmedi — doğru sıra buydu: yanlış ayrıştırma arşivden bedavaya
düzeltilir, kaçırılan bildirim düzeltilemez.

---

## 1. Sayılar

```
form (benzersiz bildirim)   : 1.276
ticker satırı karşılığı     : 1.280   (4 satır çoklu kodlu 2 bildirimden)
arşiv boyutu                : 239 MB
dosya boyutu min/medyan/max : 186.226 / 187.318 / 192.060 B
gönderim aralığı            : 05.08.2025 19:16:18 .. 07.08.2026 18:32:48
```

Boyut dağılımının darlığı (186–192 KB, %3 yayılım) tek başına bir sağlık
işareti: KAP'ın "bulunamadı" sayfası bu boyutta olmaz. Sıfır bayt veya
50 KB altı dosya yok.

### Dönem dağılımı (arşivdeki)

| Dönem | Form |
|---|---|
| 6 Aylık | 650 |
| Yıllık | 614 |
| 9 Aylık | 7 |
| 3 Aylık | 5 |

### Beyan durumu — 795 pay kodu

| Durum | Sayı | Anlamı |
|---|---|---|
| `BEYAN_VAR` | 539 | en az bir KAFİF arşivde |
| `KAPSAM_DISI` | 150 | mali sektör muafı (spec §0.4), sorgulanmadı |
| `BEYAN_YOK` | 73 | muaf değil, yine de beyan vermemiş |
| `AYIRT_EDILEMEDI` | 33 | muafiyeti belirsiz **ve** beyanı yok |

**`AYIRT_EDILEMEDI` bilinçli olarak `MUAF` değil.** Bu rotadan muaf olan ile
beyan vermeyen ayırt edilemiyor: ikisi de KAFİF vermez. İkisinden birini
varsaymak yerine durum böyle işaretlendi — yanlış muafiyet şirketi panelden
sessizce düşürür. Ayrım 1.1b'nin sektör alanıyla kapanabilir.

---

## 2. Harcanan istek ve üç geçiş

| Geçiş | Aralık | Başarılı çekim | Yeniden deneme | Kalan hata |
|---|---|---|---|---|
| Duman testi (20 pay kodu) | 2,0 sn | 46 | 1 | 0 |
| 1. tam geçiş | 2,0 sn | 1.113 | 367 | 114 |
| 2. geçiş | 5,0 sn | 113 | 5 | 1 |
| 3. geçiş | 6,0 sn | 1 | 0 | **0** |
| **Toplam** | | **1.273** | **373** | **0** |

Kalan 3 form URL önbelleğinden geldi (1.0/1.2 turlarında zaten çekilmişti):
1.273 + 3 = 1.276.

**Hata deseni: sunucu dalgalar hâlinde sıkıştırıyor.** 114 başarısızlığın
hepsi `3 denemede alınamadı` (geçici), hiçbiri kalıcı hata değil —
`veri/onbellek/negatif.tsv` boş kaldı. Bu kritik: geçici hata negatif
önbelleğe yazılsaydı o 114 form kalıcı olarak "yok" sayılacaktı.

Her geçişte `min_aralik` **yükseltildi** (2 → 5 → 6 sn). Yön tek taraflı:
sıkışma görünce yavaşlanır, hızlanılmaz.

---

## 3. "Pencere keşfi öldürüyor, erişimi değil" — ölçüm

1.2'de n=1 gözlenmişti (1472632). Bu koşu onu **n=15**'e çıkardı.

**Ölçüm kümesi 1.276 değil 15 — ve bu ayrım önemli.** Kimliklerin 1.261'i
hâlâ bugünkü keşif penceresinde; onların inmesi pencere dışı erişim hakkında
hiçbir şey söylemez. Hipotezi sınayan tek küme, `gonderim_ts < bugün − 1 yıl`
olan, yani **bugün sorgu sonucunda görünmeyecek** kimlikler:

```
pencere dışı kimlik : 15
indi                : 15   (%100)
404                 :  0
```

| Ticker | Bildirim | gonderim_ts | Dönem |
|---|---|---|---|
| THYAO | 1472632 | 05.08.2025 19:16 | 6 Aylık |
| ASELS | 1472641 | 05.08.2025 19:40 | 6 Aylık |
| PEKGY | 1474003 | 07.08.2025 18:10 | 6 Aylık |
| VRGYO | 1474009 | 07.08.2025 18:10 | 6 Aylık |
| DCTTR | 1474028 | 07.08.2025 18:14 | 6 Aylık |
| KTSKR | 1474032 | 07.08.2025 18:15 | 6 Aylık |
| EDATA | 1474037 | 07.08.2025 18:16 | 6 Aylık |
| HATSN | 1474048 | 07.08.2025 18:19 | 6 Aylık |
| BRISA | 1474056 | 07.08.2025 18:22 | 6 Aylık |
| INTEM | 1474071 | 07.08.2025 18:32 | 6 Aylık |
| OYAKC | 1474149 | 07.08.2025 19:41 | 6 Aylık |
| CEOEM | 1474186 | 07.08.2025 19:47 | 6 Aylık |
| DOGUB | 1474293 | 07.08.2025 21:59 | 6 Aylık |
| *(+2, koşu sırasında tarih dönünce pencereden düşen)* | | | |

Küme koşu sırasında 13'ten 15'e çıktı: pencere gerçek zamanlı kayıyor ve
2.0'ın "1 gün/gün" ölçümü canlı olarak yeniden doğrulandı.

**200 dönmesi yetmez — içerik de doğrulandı.** Üç pencere dışı form
`dogrula` ile açıldı:

```
THYAO 1472632  SELF-CHECK GEÇTİ   KARAR UYGUN_DEGIL [G4_DOGRUDAN_AYKIRI]
DOGUB 1474293  SELF-CHECK GEÇTİ   KARAR UYGUN_DEGIL [G5_GELIR]
CEOEM 1474186  SELF-CHECK GEÇTİ   KARAR UYGUN_DEGIL [G1_ESAS_SOZLESME]
```

Üçü de gerçek form, üçü de farklı kapıdan eleniyor. Yani bunlar "yumuşak
404" (200 dönen bulunamadı sayfası) değil.

### Sonuç ve politika etkisi — **karar sizin**

**15/15, 404 yok.** `/tr/Bildirim/{id}` rotasında keşif penceresine bağlı
bir erişim ufku **bulunamadı.** Bunun üç sonucu var:

1. **Arşiv kimliklerden yeniden kurulabilir.** `bildirim_gecmisi.csv`
   (1.276 satır, ~90 KB) elde olduğu sürece 239 MB'lık `veri/ham/`
   yeniden indirilebilir. Yani **asıl yedeklenmesi gereken şey kimlik
   listesi**, HTML yığını değil. Bu, yedekleme politikasını
   basitleştiriyor: kimlik CSV'si git'e girebilecek kadar küçük.
2. **Ama bu bir garanti değil.** Ölçüm bugünün davranışı; KAP yarın
   `/tr/Bildirim/{id}`'e de bir ufuk koyabilir ve o gün geriye dönüş
   olmaz. HTML arşivi bu yüzden **yine de silinmemeli** — ucuz sigorta.
3. **Kritik bakım işi 1.2'nin düzenli koşulması.** Kaybedilen tek şey
   "böyle bir form var" bilgisi; onu da yalnız sorgu penceresi veriyor.

**Ölçülemeyen sınır:** en eski erişilen form 05.08.2025 tarihli. Daha
eskisine ait **kimliğimiz yok**, dolayısıyla "erişim ufku 1 yıldan
derin mi" sorusu bu veriyle cevaplanamaz. Erişim ufku ancak 2024 veya
öncesine ait bir kimlik ele geçerse sınanabilir (ör. BIST dönemsel
değişiklik PDF'lerinden — plan 4.1).

---

## 4. Arşiv disiplini — kodda ne var

- **İdempotanlık `bildirim_id` üzerinden, sha256 ile DEĞİL.** Kimlik dosya
  adının **sonunda** duruyor (`..._1472632.html`); tarama `iterdir` ile
  dosya adından okuyor, içerik açmıyor. Ticker veya dönem etiketi ileride
  değişse bile idempotanlık bozulmaz. Sha yalnızca bütünlük damgası
  (kural 6): aynı bildirimi iki kez çekmek iki farklı sha üretiyor.
- **Gövde URL önbelleğine yazılmıyor** (`Çekici.getir(onbellekle=False)`).
  Arşiv `veri/ham/`'da; aynı 239 MB'ı iki yerde tutmanın anlamı yok.
  Okuma yine önbellekten yapılıyor, yani daha önce çekilmiş 3 form ağa
  çıkmadan geldi.
- **Temizleme komutu yok, toplu `--zorla` yok.** `veri/ham/` ve
  `veri/onbellek/` artık tek kopyası olan arşiv.
- **İlerleme her 50 ağ isteğinde diske yazılıyor** (`arsiv_indeksi.csv`).
  Koşu kesilirse kaldığı yerden devam ediyor — 2. ve 3. geçiş tam olarak
  bunu yaptı, 1.162 dosyayı yeniden indirmedi.
- **Sayfalama döngüsü yok** (2.0: 92 = 92).

**Testler: 97 geçiyor** (22 motor + 9 çekici + 23 evren + 8 derinlik +
15 bildirim + 7 rsc + 13 toplayıcı). Yeni: `tests/test_toplayici.py` —
idempotanlık, dosya adlandırma, 404 ile geçici hatanın ayrılması, pencere
dışı işaretleme, kontrol noktası, `BEYAN_YOK`/`AYIRT_EDILEMEDI` ayrımı.

---

## 5. 1.4b ve 1.3 için devir

- Arşiv **ayrıştırılmaya hazır**; 1.3'ün 20/20 örneklemi artık ağa çıkmadan
  seçilebilir. Örneklem şartlarının hepsi arşivde mevcut: 5 adet 3/9 Aylık
  (özel hesap dönemi), 163 düzeltme grubu (1.2 §7), 6 adet 2024/Yıllık.
- `arsiv_indeksi.csv` her form için `bildirim_id, ticker, tum_tickerlar,
  yil, periyot, gonderim_ts, dosya, bayt, sha256, pencere_disi` taşıyor.
  1.4b bu indeksten yürüyebilir, dizin taramasına gerek yok.
- `bildirim_gecmisi.csv`'de `indirildi_mi` artık 1.280/1.280 satırda EVET.
  1.2 yeniden koşulursa bu işaretler korunuyor (`indirilenleri_koru`).
