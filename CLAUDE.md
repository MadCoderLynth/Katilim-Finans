# BIST Katılım Uygunluk Motoru

KAP'ta yayımlanan Katılım Finans İlkeleri Bilgi Formu (KAFİF) bildirimlerinden
katılım endeksi uygunluk kararı üretir. Kullanım amacı: swing trading sistemine
bağlanacak, look-ahead'sız tarihsel uygunluk paneli.

Detaylar: @BIST_Katilim_Uygunluk_Motoru_Spesifikasyonu_v0.1.md ve @OKUBENI.md

**Dil: tüm çıktılar, yorumlar ve commit mesajları Türkçe.**

## Komutlar

```bash
python3 tests/test_motor.py                              # 22 test, pytest gerektirmez
python3 tests/test_cekici.py                             # 6 test, çekim katmanı (ağa çıkmaz)
python3 -m katilim.cli dogrula veri/ham/DOSYA.html        # ayrıştır + self-check + karar
python3 -m katilim.cli dok veri/ham/DOSYA.html            # tanı: tabloları imzalarıyla dök
python3 -m katilim.cli toplu veri/ham --csv veri/panel/panel.csv
```

## Değiştirilemez kurallar

Bunlar keyfi tercih değil; her biri sessiz veri bozulmasına karşı bir savunma.
Test kırıldığında **kuralı değil kodu düzeltin.**

1. **Self-check her şeyi kapılar.** Alt tablolardan yeniden hesaplanan üç oran,
   formun özet alanlarıyla ±0,01 içinde eşleşmezse kayıt karantinaya alınır.
   `TOLERANS` sabitini testi geçirmek için gevşetmek yasak — sapma varsa ya
   parser bozuk ya şablon değişmiş, ikisi de araştırılmalı.

2. **Eksik beyan ≠ hayır beyanı.** Okunamayan evet/hayır alanı `None` kalır ve
   karar `BELIRSIZ` olur. `None`'ı `False`'a çevirmek en tehlikeli sessiz hata:
   uygunsuz şirketi uygun gösterir.

3. **TOPLAM satırları okunmaz, toplam hesaplanır.** Formun toplam satırını
   parse etmek, formun kendi aritmetiğini doğrulama imkânını yok eder.

4. **Tablolar konuma göre değil içerik imzasına göre tanınır.** 4A tablosu =
   içinde "alkollü içki" geçen tablo. Şablon revizyonlarında satır sayısı
   değişiyor (2024'te 1. bölüm 3 sorudan 2'ye indi), konum bazlı parser kırılır.

5. **Türkçe normalizasyonda `ı` tuzağı.** Noktasız `ı` Unicode'da ayrıştırılamaz;
   sadece NFKD'ye güvenilirse `ortaklarının` → `ortaklar n` olur ve etiket
   eşlemesi **hata vermeden** başarısız olur. `metin._TR_MAP` bunun için var,
   kaldırmayın.

6. **Ham HTML her zaman saklanır** (`veri/ham/`, sha256 ile). Şablon değişince
   geçmişi yeniden ayrıştırmanın tek yolu bu.

## Doğrulanmamış varsayımlar

Karar motorunda kural olarak kodlu ama **kanıtlanmamış** (spec §2.3):

- **H1:** 4A'daki herhangi bir EVET kesin elemedir. → Tek gözlem: THY 2025.
- **H2:** Kâr payı imtiyazı, tasfiye payı imtiyazıyla aynı ağırlıkta eler.
- **H3:** BIST payda olarak max(ort. PD, toplam varlık) kullanıyor.
- **H4:** Tolerans durumu şirket bazında, kriter bazında değil.

Bunlar ancak **Faz 4** (kararlarımız vs. resmi XKTUM bileşen listeleri) ile
sınanabilir. Faz 4 öncesinde üretilen panel araştırma çıktısıdır, karar dayanağı
değildir. Bir hipotez revize edilirse spec ve kod aynı commit'te güncellenir.

## Test katmanları — karıştırmayın

- **Gerçek veri testleri** (THY 2025/Yıllık fixture): kanıttır. Oran formülleri
  ve karar motoru KAP'ın kendi çıktısına karşı doğrulanmıştır.
- **Sentetik HTML testi**: duman testidir. Parser mekaniğinin çalıştığını
  gösterir, gerçek KAP HTML'inin o yapıda olduğunu **kanıtlamaz**.

Sentetik HTML'i, gerçek HTML'e uydurmak için değiştirmek anlamsızdır — gerçek
doğrulama `dogrula` komutunu gerçek bir dosyayla çalıştırmaktır.

## Sıradaki iş

**Faz 0 bitti — parser gerçek KAP HTML'inde doğrulandı.**
`veri/ham/THYAO_2025_yillik.html` üzerinde `dogrula`: `SELF-CHECK: GEÇTİ`
(üç oranda da fark 0,00) + `KARAR: UYGUN_DEGIL [G4_DOGRUDAN_AYKIRI]`.
Tespit edilen şablon imzası: `4A|4B|4C|4D|4E|5F|5G|5H|6I|6J|OZET|S1|S2|S3`.
Yani `TABLO_IMZALARI` / `BEYAN_IMZALARI` haritaları gerçek şablona uyuyor —
artık sentetik HTML'e değil, bu dosyaya karşı regresyon bakılır.

**Faz 1: toplama katmanı (spec §3).** Alt katman hazır: `katilim/cekici.py`
(önbellek → asgari aralık+jitter → oturum bütçesi → geri çekilme). Eksik olan,
onun üstüne oturacak rotalar:

1. **Şirket listesi** — `/tr/bist-sirketler` → ticker, unvan, pazar, member uuid.
2. **Bildirim geçmişi** — `/tr/bildirim-sorgu-sonuc?member={uuid}` → KAFİF
   bildirim_id listesi. Sayfalama ve filtre parametreleri bilinmiyor.
3. Tekil bildirim `/tr/Bildirim/{id}` zaten `dogrula` ile tüketilebiliyor.

Ayrı bir iş: `/tr/kfif/{sayısal_id}-{slug}` ile `member={uuid}` **farklı
anahtarlar** (spec §1.1); eşleme kendi başına bir adım, rota keşfiyle
karıştırmayın.

**Rota keşfinde bütçe düşük tutulur.** İlk tur `HızSınırlayıcı(oturum_butcesi=50)`
ile koşulur. Amaç evreni doldurmak değil, ölçmek: sayfa başına kaç kayıt
dönüyor, sunucu tarafı render `requests` ile yetiyor mu yoksa `playwright`
gerekiyor mu (spec §3.2), bildirim sorgusu sayfalanıyor mu. Bu turda kaç
istekle ne elde edildiği yazılır, **sonra** bütçe bilinçli yükseltilir.
`BütçeAşıldı` bir arıza değil karar noktasıdır — kodun içinden otomatik
büyütmeyin.
