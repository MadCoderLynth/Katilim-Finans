# Düzeltme Çözümü ve Dönem Bazlı Zincir — Bulgu Notu

**Plan adımı:** 2.3 — Düzeltme mantığı
**Tarih:** 2026-08-10
**Modüller:** `katilim/toplayici.py::duzeltmeleri_coz` ·
`katilim/panel.py::panel_uret` (yeniden yazıldı) · `katilim/ayristirici.py`
**Çıktı:** `veri/panel/duzeltme_olaylari.csv` (181 satır) ·
`veri/panel/panel.csv` (yeniden üretildi)
**Ağ isteği: 0.**

> **Sıra ters işletilmişti.** 2.3, 3.1'in ön koşuluydu; 3.1 önce koştu ve
> panelde artefakt üretti. Bu adım hem düzeltmeyi çözdü hem paneli
> yeniden üretti hem de 4.0 mutabakatını yeniden koşturdu.

---

## 0. Sonuç — tek cümle

Zincir **dönem bazına** alınınca 3.1'in çevirdiği 5 satırın **4'ü artefakt
çıktı**; geriye kalan tek gerçek etki (KLMSN) bir uyuşmazlığı kapattı ve
**gerçek uyuşmazlık 2 → 1'e (%0,39 → %0,19) düştü.**

---

## 1. Hata neydi

`seri_degerlendir` bildirim listesi üzerinde yürüyordu. Aynı dönemin
düzeltilmiş bir bildirimi, kendi döneminin önceki kaydını **"önceki dönem"
sanıyordu.** Md. 3.5 ardışık *değerleme dönemlerini* düzenliyor; aynı
dönemin ikinci bildirimi yeni bir dönem değil.

Somut vaka — **DCTTR**, 2025/Yıllık'ı iki kez vermiş:

```
2025/6 Aylık  07.08.2025  UYGUN       gelir 0,75  borç 28,82
2025/Yıllık   10.03.2026  TOLERANSTA  gelir 4,97  borç 34,62   (DUZELTILEN)
2025/Yıllık   06.04.2026  TOLERANSTA  gelir 4,66  borç 35,85   (DUZENLENEN)
```

Eski kod üçüncü satırı değerlendirirken ikinciyi "önceki dönem" sayıyor,
"önceki dönem TOLERANSTA + bu dönem aşım → UYGUN_DEGIL" kuralını
işletiyordu. Sonuç: XKTUM üyesi bir şirketi eliyorduk — **sahte
uyuşmazlık.**

## 2. Düzeltme: zincir dönem bazında, look-ahead korunarak

`panel_uret` artık:

1. Şirketin dönemlerini **ilk gönderimlerine göre** sıralıyor (dönem
   etiketi kronoloji taşımıyor).
2. Bildirimleri **gönderim sırasıyla** işliyor.
3. Her bildirim yalnız **kendi döneminin** durumunu güncelliyor; zinciri
   ilerletmiyor.
4. P(n)'in gördüğü "önceki dönem durumu", P(n−1)'in **o ana kadar
   yayımlanmış en son kaydından** geliyor — bugünkü nihai kaydından değil.
   Gönderim sırasıyla ilerlemek bunu kendiliğinden sağlıyor.

Panel satırı her bildirim için ayrı kalıyor: o kayıt kendi penceresinde
canlı etiketti. `gecerli_kayit` sütunu dönemin en geç kaydını işaretliyor
(spec §3.2); eskiler **silinmiyor**.

**Bir ek düzeltme:** dönem bazlı zincirde `BELIRSIZ` bir dönem, durumu
"yok" bırakınca sonraki dönem için sessizce `False` üretiyordu — yani veri
eksikliği toleransı sıfırlıyordu. Artık BELİRSİZ dönem **önceki dönemin
durumunu devralıyor** (kural 2'nin zincir karşılığı). Testle donduruldu.

### Zincirin etkisi — öncesi ve sonrası

| | 3.1 (bildirim bazlı) | 2.3 (dönem bazlı) |
|---|---|---|
| zincirin çevirdiği satır | 5 | **1** |
| çevrilenler | ALVES, DCTTR, DOGUB, KLMSN, KONTR | **KLMSN** |
| `onceki_donem_tolerans` | 30 | 20 |
| gerçek uyuşmazlık (4.0) | 2 | **1** |

**Dördü artefaktmış.** 4.0'ın "zincir bir uyuşmazlığı kapatıp yenisini
açıyor, H4 desteklenmiyor" bulgusu **geçersiz**: DCTTR'nin elenmesi
zincirden değil düzeltmenin çözülmemiş olmasından geliyordu.

---

## 3. `is_duzeltme` — metin araması kaldırıldı

Parser artık sayfa metninde "düzeltme" **aramıyor**. Kaynak yapılandırılmış:
bildirim sorgusunun RSC yükündeki `isChanged` alanı. Alan
`bildirim_gecmisi.csv` → `arsiv_indeksi.csv` → panel hattında taşınıyor.

```
DUZENLENEN 164 · DUZELTILEN 138 · (yok) 978        1.280 panel satırı
```

**İkisi AYRI taşınıyor, birleştirilmedi** — aradaki fark KAP tarafından
belgelenmemiş. Gözlem, semantiğe dair bir ipucu veriyor: üç bildirimli
AHSGY 2025/6 Aylık'ta ilk kayıt işaretsiz, ikinci `DUZELTILEN`, üçüncü
`DUZENLENEN`. Yani alan **en son düzeltme çiftini** işaretliyor gibi
duruyor, zincirin tamamını değil. Doğrulanmadı.

`tests/test_panel.py::test_is_duzeltme_metin_aramasindan_gelmiyor` metin
aramasının geri gelmesini engelliyor.

---

## 4. Düzeltme olayları — `veri/panel/duzeltme_olaylari.csv`

```
olay                : 181   (163 dönem, 135 pay kodu)
dönem başına kayıt  : 2 -> 147 dönem · 3 -> 30 · 5 -> 4
geçerli kayıt       : 1.099 / 1.280 panel satırı
oranı değişen olay  : 160
beyanı değişen olay :  14
KARAR ÇEVİREN beyan :  14   <- hepsi HAYIR <-> EVET
```

163 dönem / 135 şirket, 1.2'nin bağımsız ölçümüyle **birebir aynı**.

### Karar çeviren 14 düzeltme

Bir beyanın HAYIR↔EVET dönmesi G1–G4 kesin kapılarını doğrudan tetikler.
Değişen alanlar:

| Beyan | Olay | Ne demek |
|---|---|---|
| `b1_1` | 6 | esas sözleşmede md. 1.2 faaliyeti |
| `b1_2` | 4 | esas sözleşmede md. 1.2 ortaklığı |
| `b4_5` | 3 | finans sektörü (katılım dışı) |
| `b4_4` | 1 | kumar |
| `b4_3` | 1 | tütün |
| `b2_1` | 1 | kâr payı imtiyazı |

Örnekler: ASUZU `b1_1` HAYIR→EVET (şirket kendini eledi), GENIL `b4_4`
EVET→HAYIR (kumar beyanı geri alındı), GMTAS `b4_3` EVET→HAYIR.

**Bu 14 kayıt Faz 5'in olay akışı için de aday**: uygunluk etiketini
çeviren bir düzeltme, fiyat etkisi ölçümünde ayrı bir olay tipidir.

`karar_ceviren_beyan` bayrağı **yalnız HAYIR↔EVET** için açılıyor.
`None`↔bool geçişi ayrı bir şey (veri eksikliği) ve bayrağı tetiklemiyor;
testle donduruldu.

---

## 5. Panelin yeni hâli

```
panel satırı      : 1.280   (539 pay kodu)
geçerli kayıt     : 1.099   (dönemin en geç bildirimi, spec §3.2)
karar (geçerli)   : 588 UYGUN_DEGIL · 484 UYGUN · 27 TOLERANSTA
zincirin çevirdiği: 1 satır (KLMSN 2025/Yıllık)
ZİNCİR BOŞLUĞU    : 0 satır
```

Zincir boşluğu ölçütü de dönem bazına geçti: artık **ardışık DÖNEMLER**
arasındaki sessizliğe bakıyor (>280 gün). Bu pencerede 0 — ve doğru bir
sıfır, çünkü 1 yıllık pencere bir dönem atlamasını barındıramıyor.

**AÇIK KARAR (değişmedi):** zincir boşluğunda tolerans durumu taşınsın mı?
Spec tanımsız; geçici davranış taşımak ve `ZINCIR_BOSLUGU` ile işaretlemek.

---

## 6. 4.0 yeniden koştu

```
UYUMLU 517 · KAPSAM 259 · PANELDE_YOK 11 · DÖNEM 7 · GERÇEK 1
GERÇEK uyuşmazlık 1 / 518 = %0,19        (önce: 2 / 518 = %0,39)
```

Kalan tek gerçek uyuşmazlık **PEKGY** — H3 (payda) adayı veya
modellenmemiş yeniden giriş kuralı. 4.3'ün konusu.

**H4 hakkında:** zincir artık doğru semantikle çalışıyor ve mutabakatı
**iyileştiriyor**. Bu H4'ü kanıtlamaz (n=1) ama 4.0'daki karşı kanıt
ortadan kalktı. Hipotez **revize edilmedi**; spec §2.3'e bu bulgu not
olarak düşüldü.

---

## 7. Testler

**168 geçiyor** (öncesi 162). Yeni/değişen:

- `test_pnlsn_ayni_donem_uc_bildirim_zinciri_ilerletmez` — gerçek veriden
  sabitlenmiş, arşivsiz koşar
- `test_dcttr_duzeltme_artefakti_kapandi` — artefaktın regresyonu
- `test_onceki_donem_durumu_nokta_zaman` — look-ahead disiplini
- `test_duzeltme_olayi_alanlari`, `test_beyan_none_a_donerse_karar_ceviren_sayilmaz`,
  `test_uc_bildirim_iki_olay_uretir`
- `test_is_duzeltme_metin_aramasindan_gelmiyor`
- `test_duzeltme_izi_csvde_tasiniyor`

3.1'de yazdığım 4 zincir testi **aynı dönemde** çok kayıt kuruyordu, yani
hatalı davranışı doğru sayıyorlardı; fixture'lar ayrı dönemlere çevrildi.
