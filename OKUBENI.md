# BIST Katılım Uygunluk Motoru — Faz 0

KAP'ta yayımlanan Katılım Finans İlkeleri Bilgi Formu (KAFİF) bildirimlerinden
katılım uygunluk kararı üretir. Spec: `BIST_Katilim_Uygunluk_Motoru_Spesifikasyonu_v0.1.md`

## Klasör yapısı

```
katilim_motor/
├── katilim/              # paket
│   ├── metin.py          # Türkçe sayı/etiket normalizasyonu
│   ├── model.py          # veri modeli
│   ├── ayristirici.py    # HTML → model
│   ├── oranlar.py        # oran hesabı + self-check
│   ├── karar.py          # G0–G7 kapıları + tolerans durum makinesi
│   └── cli.py            # komut satırı
├── tests/
│   ├── test_motor.py     # 22 test, pytest gerektirmez
│   └── fixtures/
│       ├── thy_2025_yillik.json   # altın standart
│       └── olustur_thy.py
├── veri/
│   ├── ham/              # ← indirdiğiniz KAP HTML'leri buraya
│   └── panel/            # ← üretilen CSV buraya
├── requirements.txt
├── pyproject.toml
├── Makefile
└── .gitignore
```

`veri/` klasörü `.gitignore`'da. Ham HTML arşivi yerelde durur (Spec §3.2),
depoyu şişirmez.

## Kurulum

Tek bağımlılık: `beautifulsoup4`. Test için ek paket gerekmez.

**macOS / Linux**
```bash
cd katilim_motor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 tests/test_motor.py          # 22/22 geçmeli
```

**Windows (PowerShell)**
```powershell
cd katilim_motor
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python tests\test_motor.py
```

`make` varsa kısayollar: `make kur`, `make test`, `make panel`.

## Git

```bash
git init
git add .
git commit -m "Faz 0: KAFİF ayrıştırıcı, oran self-check, karar motoru"
```

Spec dosyasını (`BIST_Katilim_Uygunluk_Motoru_Spesifikasyonu_v0.1.md`) da
depoya koyun — kod ile spec birlikte versiyonlanmalı, aksi halde H1–H4
hipotezleri revize edilince hangi kodun hangi varsayıma dayandığı kaybolur.

## Kullanım

```bash
# Bir bildirimi ayrıştır, self-check çalıştır, karar üret
python3 -m katilim.cli dogrula THYAO_2025_yillik.html

# Ayrıştırma tutmazsa: tabloları imzalarıyla dök
python3 -m katilim.cli dok THYAO_2025_yillik.html

# Yapılandırılmış çıktı
python3 -m katilim.cli json THYAO_2025_yillik.html

# Klasördeki tüm bildirimlerden panel üret (tolerans durum makinesi dahil)
python3 -m katilim.cli toplu ./html --csv panel.csv
```

HTML'i almak için: `https://kap.org.tr/tr/Bildirim/{id}` sayfasını kaydedin.
Dosya adı konvansiyonu: `TICKER_YIL_DONEM.html`

Çıkış kodları: `0` temiz, `1` self-check kaldı / karantina var, `2` ayrıştırılamadı.

## Modüller

| Dosya | Sorumluluk |
|---|---|
| `metin.py` | Türkçe sayı ve etiket normalizasyonu |
| `model.py` | KafifBildirim veri modeli, 13 beyan alanı, 9 tutar tablosu |
| `ayristirici.py` | HTML → model. Tabloları **içerik imzasına** göre tanır |
| `oranlar.py` | Üç oranı yeniden hesaplar, özet alanlarıyla karşılaştırır |
| `karar.py` | G0–G7 kapıları + tolerans durum makinesi |
| `cli.py` | Komut satırı |

## Tasarım kararları

**Tablolar konuma göre değil içerik imzasına göre tanınır.** 4A tablosu, içinde
"alkollü içki" geçen tablodur. Şablon revizyonlarında satır sayısı değişse de
(2024'te 1. bölüm 3 sorudan 2'ye indi) çalışmaya devam eder.

**TOPLAM satırları okunmaz, toplam hesaplanır.** Böylece formun kendi toplam
satırı da dolaylı olarak doğrulanmış olur.

**Self-check geçmezse karar güvenilmez sayılır.** Alt tablolardan yeniden
hesaplanan üç oran, formun özet alanlarıyla ±0,01 içinde eşleşmezse kayıt
karantinaya alınır — sessizce kabul edilmez.

**Eksik beyan ≠ hayır beyanı.** Okunamayan bir evet/hayır alanı `None` kalır ve
karar `BELIRSIZ` olur. Eksik veriyi "temiz" saymak en tehlikeli sessiz hatadır.

## Testlerin iki katmanı — fark önemli

**A) Gerçek veri (kanıt).** THY 2025/Yıllık bildiriminin yayımlanmış rakamları.
Üç oran formülü ve karar motoru KAP'ın kendi çıktısına karşı doğrulanmıştır.

**B) Sentetik HTML (duman testi).** KAP'ın tablo yapısını taklit eden bir HTML.
Parser mekaniğinin çalıştığını gösterir ama **gerçek KAP HTML'inin bu yapıda
olduğunu kanıtlamaz.** Gerçek doğrulama, elinizdeki bir `.html` dosyasıyla
`dogrula` komutunu çalıştırdığınızda olur.

## Bilinen açıklar

- `is_duzeltme` tespiti sayfa metninde "düzeltme" araması yapıyor; gerçek bir
  düzeltme bildirimiyle doğrulanmadı.
- Ticker, dosya adından tahmin ediliyor; toplama katmanı (Faz 1) gelince
  KAP member kimliğinden alınacak.
- BIST'in max(ort. PD, toplam varlık) paydası uygulanmıyor. KAFİF oranı bu
  oranın üst sınırı olduğu için %33 altındaki kararlar güvenli; %33–36,3
  bandında ikinci hesap gerekiyor (Spec §2.2).
- H1–H4 hipotezleri kural olarak kodlu ama doğrulanmadı. Faz 4 mutabakatı şart.
