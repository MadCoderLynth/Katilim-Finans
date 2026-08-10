# Değişim Bazlı Mutabakat — 2026-05 revizyonu

**Plan adımı:** 4.2 — kararlarımız vs. resmî XKTUM listesi, **durum değil DEĞİŞİM**
**Endeks dönemi:** 01.05.2026 – 30.09.2026
**Kesim noktası:** 27.04.2026 (DUYURU tarihi — yürürlük 01.05.2026 değil)
**Önceki kesim:** 24.09.2025
**Kaynak:** katilim_endeksleri_20260501_20260930.pdf
**Ağ isteği: 0.**

> Bu adım 4.0'dan niteliksel olarak farklı. 4.0 nokta-zaman DURUM
> karşılaştırmasıydı ve kayıtların çoğu uygunluğun hiç değişmediği
> kararlı vakalardı. Buradaki örneklem yalnız **giriş/çıkış**
> olayları: resmî liste değiştiğinde bizim de değişip değişmediğimiz.

---

## 1. Karışıklık matrisi

| | BIST içeride (GİREN) | BIST dışarıda (ÇIKAN) |
|---|---|---|
| **biz UYGUN/TOLERANSTA** | 27 ✔ | **0 YANLIŞ POZİTİF** |
| **biz UYGUN_DEGIL** | 0 yanlış negatif | 19 ✔ |

**Uyuşmazlık oranı: 0 / 46 = %0.00**

Payda yalnız görüşümüz olan olaylar. `GORUS_YOK` ve olağanüstü çıkarma adayları paydaya konmadı — 4.0'da aynı hata düzeltilmişti.

Sınıf dağılımı: `{'ESLESTI': 46}`

Yön dağılımı: `{'AYNI_YON': 39, 'OLCULEMEZ': 3, 'DEGISIM_YOK': 4}`

### Testin gücü — "0 uyuşmazlık" kendiliğinden bir şey söylemez

Kesim noktasında panelin geneli: **%46.1 UYGUN / %53.9 UYGUN_DEGIL** (n=536 pay kodu). Taban oran yazı-turaya yakın, yani "hep aynı yanıtı veren" bir motor bu örneklemi geçemez.

27 GİRİŞ'in tamamına UYGUN, 19 ÇIKIŞ'ın tamamına UYGUN_DEGIL demenin şans eseri olma olasılığı ≈ **10^-14**.

## 2. Yanlış pozitifler — pahalı olan hata

**Yok.** BIST'in çıkardığı payların hiçbirine UYGUN demedik.

## 3. Tüm uyuşmazlıklar

**Yok.** Görüşümüz olan olayların tamamı resmî listeyle uyuştu.

## 4. Hipotez bazında — hangisi fiilen sınandı

Bir hipotez hiç olay karara bağlamadıysa **sınanmamıştır**; "uyuşmazlık yok" onu desteklemez.

| Hipotez | Karara bağladığı olay | Eşleşen | Uyuşmazlık | Örnek |
|---|---|---|---|---|
| — | 24 | 24 | 0 | ALFAS, ARENA, BAYRK, BUCIM |
| H3 | 14 | 14 | 0 | AKSA, AKYHO, BANVT, BNTAS |
| H4 | 8 | 8 | 0 | DGNMO, DNISI, KLSER, KONTR |

### Zamanlama sapması — kararımız sınırın iki yanında AYNI

Bu olaylarda A kademesi tuttu (sonra durumu doğru) ama kararımız zaten o durumdaydı: **BIST'ten bir dönem erken davranmışız.** `onceki_cikis` doluysa bu bir YENİDEN GİRİŞ ve gecikme, spec §2.3'teki H6 adayını (gecikmeli yeniden giriş) doğrudan ilgilendirir.

| Ticker | Olay | Önceki kesimde | Şimdi | Önceki çıkış | Okuma |
|---|---|---|---|---|---|
| DNISI | GIREN | TOLERANSTA | UYGUN | — | ilk kez giriyor; gecikme likidite/dolaşım şartı olabilir |
| KLSER | GIREN | TOLERANSTA | UYGUN | 2024-07-01 | YENİDEN GİRİŞ — H6 adayı |
| PNSUT | GIREN | TOLERANSTA | UYGUN | 2025-05-01 | YENİDEN GİRİŞ — H6 adayı |
| PRKME | GIREN | UYGUN | UYGUN | — | ilk kez giriyor; gecikme likidite/dolaşım şartı olabilir |

⚠ **H6 REVİZE EDİLMEDİ.** Spec §2.3'te aday olarak duruyor ve kodda karşılığı yok; burada yalnız kanıt birikiyor.

## 5. Görüşümüz olmayan olaylar

- **GÖRÜŞ YOK (0):** —
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

