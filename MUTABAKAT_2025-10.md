# Değişim Bazlı Mutabakat — 2025-10 revizyonu

**Plan adımı:** 4.2 — kararlarımız vs. resmî XKTUM listesi, **durum değil DEĞİŞİM**
**Endeks dönemi:** 01.10.2025 – 30.04.2026
**Kesim noktası:** 24.09.2025 (DUYURU tarihi — yürürlük 01.10.2025 değil)
**Önceki kesim:** 25.04.2025
**Kaynak:** katilim_endeksleri_20251001_20260430.pdf
**Ağ isteği: 0.**

> Bu adım 4.0'dan niteliksel olarak farklı. 4.0 nokta-zaman DURUM
> karşılaştırmasıydı ve kayıtların çoğu uygunluğun hiç değişmediği
> kararlı vakalardı. Buradaki örneklem yalnız **giriş/çıkış**
> olayları: resmî liste değiştiğinde bizim de değişip değişmediğimiz.

---

## 1. Karışıklık matrisi

| | BIST içeride (GİREN) | BIST dışarıda (ÇIKAN) |
|---|---|---|
| **biz UYGUN/TOLERANSTA** | 23 ✔ | **0 YANLIŞ POZİTİF** |
| **biz UYGUN_DEGIL** | 0 yanlış negatif | 26 ✔ |

**Uyuşmazlık oranı: 0 / 49 = %0.00**

Payda yalnız görüşümüz olan olaylar. `GORUS_YOK` ve olağanüstü çıkarma adayları paydaya konmadı — 4.0'da aynı hata düzeltilmişti.

Sınıf dağılımı: `{'ESLESTI': 49, 'GORUS_YOK': 3}`

Yön dağılımı: `{'OLCULEMEZ': 52}`

⚠ **Yön ÖLÇÜLEMEDİ.** Önceki kesim noktasında (25.04.2025) hiç panel kaydımız yok — panel 05.08.2025'te başlıyor. Bu sınırda yalnız *sonra* durumu sınanabiliyor; "değişim gösterdik mi" sorusu cevaplanamıyor ve eksik veri **eşleşmeme sayılmadı** (kural 2'nin karşılığı).

### Testin gücü — "0 uyuşmazlık" kendiliğinden bir şey söylemez

Kesim noktasında panelin geneli: **%47.2 UYGUN / %52.8 UYGUN_DEGIL** (n=470 pay kodu). Taban oran yazı-turaya yakın, yani "hep aynı yanıtı veren" bir motor bu örneklemi geçemez.

23 GİRİŞ'in tamamına UYGUN, 26 ÇIKIŞ'ın tamamına UYGUN_DEGIL demenin şans eseri olma olasılığı ≈ **10^-15**.

## 2. Yanlış pozitifler — pahalı olan hata

**Yok.** BIST'in çıkardığı payların hiçbirine UYGUN demedik.

## 3. Tüm uyuşmazlıklar

**Yok.** Görüşümüz olan olayların tamamı resmî listeyle uyuştu.

## 4. Hipotez bazında — hangisi fiilen sınandı

Bir hipotez hiç olay karara bağlamadıysa **sınanmamıştır**; "uyuşmazlık yok" onu desteklemez.

| Hipotez | Karara bağladığı olay | Eşleşen | Uyuşmazlık | Örnek |
|---|---|---|---|---|
| — | 28 | 28 | 0 | ASUZU, ATATP, BEYAZ, BNTAS |
| H3 | 19 | 19 | 0 | AKSEN, BORLS, BUCIM, CGCAM |
| H1 | 2 | 2 | 0 | ADESE, LRSHO |

## 5. Görüşümüz olmayan olaylar

- **GÖRÜŞ YOK (3):** AKCNS (CIKAN), ARENA (CIKAN), TKFEN (CIKAN)
- **OLAĞANÜSTÜ ÇIKARMA ADAYI (0):** —

Olağanüstü çıkarmalar dönemsel değişiklik PDF'lerinde görünmüyor (4.1 sınırı: EFORC, DAGHL, PEHOL). Bugünkü evrende olmayan bir kodun çıkışı kotasyon iptali/birleşme olabilir — **uyuşmazlık sayılmadan önce ayrı sınıflandı.**

## 6. İZ — karar çeviren düzeltme → endeks olayı

2.3'ün 14 karar çeviren düzeltmesi (bir beyan HAYIR↔EVET döndü) bir endeks olayıyla eşleşiyor mu? **Test simetrik:** eleyen düzeltme ÇIKIŞ, temizleyen düzeltme GİRİŞ bekler. Sıra şartı zorunlu — düzeltme olayın kesim noktasından önce olmalı.

```
karar çeviren düzeltme   : 14
beklenen yönde EŞLEŞEN   : 8
TERS yönde               : 0
olay düzeltmeden ÖNCE    : 4  (sayılmadı)
hiç olay yok             : 2
```

| Ticker | Yön | Değişen beyan | Endeks olayı |
|---|---|---|---|
| ASUZU | ELEYEN | `b1_1: False -> True` | CIKAN @ 2025-10-01 |
| BAYRK | TEMIZLEYEN | `b4_5: True -> False` | GIREN @ 2026-05-01 |
| BEYAZ | ELEYEN | `b1_1: False -> True` | CIKAN @ 2025-10-01 |
| DENGE | TEMIZLEYEN | `b1_1: True -> False` | GIREN @ 2025-10-01 |
| GMTAS | TEMIZLEYEN | `b4_3: True -> False` | GIREN @ 2026-05-01 |
| RGYAS | TEMIZLEYEN | `b4_5: True -> False` | GIREN @ 2025-10-01 |
| TARKM | TEMIZLEYEN | `b1_2: True -> False` | GIREN @ 2025-10-01 |
| TRHOL | ELEYEN | `b1_2: False -> True` | CIKAN @ 2025-10-01 |

