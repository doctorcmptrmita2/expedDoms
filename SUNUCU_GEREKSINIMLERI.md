# 🖥️ ExpiredDomain.dev - Sunucu/VPS Gereksinimleri

**Tarih:** 31 Aralık 2025  
**Proje:** ExpiredDomain.dev - Domain Monitoring SaaS Platform

---

## 📋 İÇİNDEKİLER

1. [Genel Bakış](#1-genel-bakış)
2. [Minimum Gereksinimler (Test/Development)](#2-minimum-gereksinimler-testdevelopment)
3. [Önerilen Gereksinimler (Küçük Ölçek Production)](#3-önerilen-gereksinimler-küçük-ölçek-production)
4. [Büyük Ölçek Production](#4-büyük-ölçek-production)
5. [Enterprise Ölçek](#5-enterprise-ölçek)
6. [Kaynak Kullanım Analizi](#6-kaynak-kullanım-analizi)
7. [VPS Sağlayıcı Önerileri](#7-vps-sağlayıcı-önerileri)
8. [Optimizasyon İpuçları](#8-optimizasyon-ipuçları)

---

## 1. GENEL BAKIŞ

### Proje Özellikleri

- **Backend:** FastAPI (Python 3.11+)
- **Veritabanı:** MySQL 8.x
- **İşlem Tipi:** Memory-intensive, CPU-intensive
- **Veri Boyutu:** Büyük zone dosyaları (GB'lar), milyonlarca domain kaydı
- **İşlemler:** Chunk-based processing, batch inserts, cron jobs

### Kritik Faktörler

1. **Zone Dosyaları:** Her TLD için günlük 100MB - 5GB arası
2. **Veritabanı:** Milyonlarca domain kaydı (sürekli büyüyor)
3. **Memory:** Parsing sırasında yüksek RAM kullanımı
4. **CPU:** Zone parsing ve drop detection CPU-intensive
5. **Disk:** Zone dosyaları ve veritabanı için yüksek depolama

---

## 2. MINIMUM GEREKSINIMLER (Test/Development)

### Kullanım Senaryosu
- 1-5 TLD takibi
- Günlük ~10,000-100,000 domain
- Test ve geliştirme amaçlı

### VPS Özellikleri

| Özellik | Minimum | Önerilen |
|---------|---------|----------|
| **CPU** | 1 vCore | 2 vCore |
| **RAM** | 2 GB | 4 GB |
| **HDD/SSD** | 50 GB | 100 GB SSD |
| **Bandwidth** | 100 GB/ay | 500 GB/ay |
| **İşletim Sistemi** | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Detaylı Açıklama

#### CPU (İşlemci)
- **1 vCore:** Temel işlemler için yeterli, ancak yavaş
- **2 vCore:** Önerilen - Parsing işlemleri için daha iyi performans

#### RAM (Bellek)
- **2 GB:** Minimum - Sadece uygulama çalıştırmak için
  - FastAPI: ~200-300 MB
  - MySQL: ~500-800 MB
  - Sistem: ~300-500 MB
  - Zone parsing: ~500-1000 MB (peak)
- **4 GB:** Önerilen - Rahat çalışma için

#### Disk (Depolama)
- **50 GB:** Minimum
  - İşletim sistemi: ~10 GB
  - MySQL veritabanı: ~5-10 GB (başlangıç)
  - Zone dosyaları: ~10-20 GB (1-2 TLD, 30 gün)
  - Uygulama: ~2 GB
  - Log dosyaları: ~5 GB
- **100 GB SSD:** Önerilen - Daha hızlı I/O

#### Network (Ağ)
- **100 GB/ay:** Zone dosyaları indirme için yeterli
- **Upload:** Zone dosyaları indirme için önemli

### Tahmini Maliyet
- **DigitalOcean:** $12-24/ay
- **Linode:** $12-24/ay
- **Vultr:** $12-24/ay
- **Hetzner:** €4-8/ay (en uygun)

---

## 3. ÖNERİLEN GEREKSINIMLER (Küçük Ölçek Production)

### Kullanım Senaryosu
- 10-20 TLD takibi
- Günlük ~100,000-1,000,000 domain
- 10-100 aktif kullanıcı
- Production ortamı

### VPS Özellikleri

| Özellik | Minimum | Önerilen | İdeal |
|---------|---------|----------|-------|
| **CPU** | 2 vCore | 4 vCore | 6-8 vCore |
| **RAM** | 4 GB | 8 GB | 16 GB |
| **HDD/SSD** | 100 GB SSD | 200 GB SSD | 500 GB SSD |
| **Bandwidth** | 1 TB/ay | 2 TB/ay | 5 TB/ay |
| **İşletim Sistemi** | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Detaylı Açıklama

#### CPU (İşlemci)
- **2 vCore:** Minimum - Temel işlemler
- **4 vCore:** Önerilen - Parsing ve drop detection için yeterli
- **6-8 vCore:** İdeal - Eşzamanlı işlemler için

#### RAM (Bellek)
- **4 GB:** Minimum - Sıkışık çalışma
  - FastAPI: ~300-500 MB
  - MySQL: ~1-1.5 GB
  - Sistem: ~500 MB
  - Zone parsing: ~1-2 GB (peak)
  - Cache: ~500 MB
- **8 GB:** Önerilen - Rahat çalışma
  - FastAPI: ~500 MB
  - MySQL: ~2-3 GB
  - Sistem: ~1 GB
  - Zone parsing: ~2-3 GB (peak)
  - Cache: ~1 GB
- **16 GB:** İdeal - Gelecek için hazır

#### Disk (Depolama)
- **100 GB SSD:** Minimum
  - İşletim sistemi: ~10 GB
  - MySQL veritabanı: ~20-30 GB (6 ay veri)
  - Zone dosyaları: ~30-50 GB (10 TLD, 30 gün)
  - Uygulama: ~2 GB
  - Log dosyaları: ~10 GB
  - Backup: ~20 GB
- **200 GB SSD:** Önerilen
  - MySQL veritabanı: ~50-80 GB (1 yıl veri)
  - Zone dosyaları: ~80-100 GB (20 TLD, 60 gün)
  - Backup: ~50 GB
- **500 GB SSD:** İdeal - Uzun vadeli depolama

#### Network (Ağ)
- **1 TB/ay:** Minimum - Zone dosyaları için
- **2 TB/ay:** Önerilen - Backup ve API kullanımı
- **5 TB/ay:** İdeal - Yüksek trafik

### Tahmini Maliyet
- **DigitalOcean:** $24-48/ay
- **Linode:** $24-48/ay
- **Vultr:** $24-48/ay
- **Hetzner:** €8-16/ay (en uygun)
- **AWS Lightsail:** $40-80/ay
- **Google Cloud:** $30-60/ay

---

## 4. BÜYÜK ÖLÇEK PRODUCTION

### Kullanım Senaryosu
- 30-50 TLD takibi
- Günlük ~1,000,000-10,000,000 domain
- 100-1000 aktif kullanıcı
- Yüksek trafik

### VPS/Cloud Özellikleri

| Özellik | Minimum | Önerilen | İdeal |
|---------|---------|----------|-------|
| **CPU** | 6 vCore | 8-12 vCore | 16+ vCore |
| **RAM** | 16 GB | 32 GB | 64 GB |
| **HDD/SSD** | 500 GB SSD | 1 TB SSD | 2 TB SSD |
| **Bandwidth** | 5 TB/ay | 10 TB/ay | Unlimited |
| **İşletim Sistemi** | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Detaylı Açıklama

#### CPU (İşlemci)
- **6 vCore:** Minimum - Temel işlemler
- **8-12 vCore:** Önerilen - Eşzamanlı parsing için
- **16+ vCore:** İdeal - Yüksek performans

#### RAM (Bellek)
- **16 GB:** Minimum
  - FastAPI: ~1 GB (multiple workers)
  - MySQL: ~4-6 GB
  - Sistem: ~2 GB
  - Zone parsing: ~4-6 GB (peak)
  - Cache: ~2 GB
- **32 GB:** Önerilen
  - FastAPI: ~2 GB
  - MySQL: ~8-12 GB
  - Sistem: ~2 GB
  - Zone parsing: ~8-10 GB (peak)
  - Cache: ~4 GB
- **64 GB:** İdeal - Gelecek için hazır

#### Disk (Depolama)
- **500 GB SSD:** Minimum
  - MySQL veritabanı: ~100-200 GB (1 yıl veri)
  - Zone dosyaları: ~200-300 GB (50 TLD, 90 gün)
- **1 TB SSD:** Önerilen
  - MySQL veritabanı: ~300-500 GB (2 yıl veri)
  - Zone dosyaları: ~400-500 GB (50 TLD, 180 gün)
- **2 TB SSD:** İdeal - Uzun vadeli depolama

### Önerilen Mimari

**Seçenek 1: Tek Sunucu (Monolith)**
- 1x VPS: 8 vCore, 32 GB RAM, 1 TB SSD
- Tüm servisler aynı sunucuda

**Seçenek 2: Ayrılmış Mimari (Önerilen)**
- **App Server:** 4 vCore, 8 GB RAM, 100 GB SSD
- **Database Server:** 4 vCore, 16 GB RAM, 500 GB SSD
- **Storage Server:** 2 vCore, 4 GB RAM, 1 TB SSD (zone dosyaları)

### Tahmini Maliyet
- **Tek Sunucu:** $80-160/ay
- **Ayrılmış Mimari:** $100-200/ay
- **AWS/GCP:** $150-300/ay
- **Hetzner Dedicated:** €50-100/ay (en uygun)

---

## 5. ENTERPRISE ÖLÇEK

### Kullanım Senaryosu
- 50+ TLD takibi
- Günlük ~10,000,000+ domain
- 1000+ aktif kullanıcı
- Yüksek availability gereksinimi

### Cloud Özellikleri

| Özellik | Minimum | Önerilen |
|---------|---------|----------|
| **CPU** | 16 vCore | 32+ vCore |
| **RAM** | 64 GB | 128+ GB |
| **HDD/SSD** | 2 TB SSD | 5+ TB SSD |
| **Bandwidth** | 20 TB/ay | Unlimited |
| **High Availability** | 2+ sunucu | 3+ sunucu (load balanced) |

### Önerilen Mimari

**Production-Ready Setup:**
- **Load Balancer:** 2 vCore, 4 GB RAM
- **App Servers (2-3x):** 8 vCore, 16 GB RAM, 200 GB SSD
- **Database (Primary + Replica):** 16 vCore, 64 GB RAM, 2 TB SSD
- **Redis Cache:** 4 vCore, 8 GB RAM, 50 GB SSD
- **Storage (Object Storage):** S3-compatible (zone dosyaları için)

### Tahmini Maliyet
- **AWS/GCP/Azure:** $500-2000/ay
- **Hetzner Dedicated:** €200-500/ay
- **DigitalOcean Managed:** $300-800/ay

---

## 6. KAYNAK KULLANIM ANALİZİ

### Zone Dosyası Boyutları

| TLD | Ortalama Boyut | Günlük Boyut | 30 Günlük |
|-----|----------------|--------------|-----------|
| .com | 2-5 GB | 2-5 GB | 60-150 GB |
| .org | 500 MB - 1 GB | 500 MB - 1 GB | 15-30 GB |
| .net | 500 MB - 1 GB | 500 MB - 1 GB | 15-30 GB |
| .zip | 50-200 MB | 50-200 MB | 1.5-6 GB |
| .dev | 100-500 MB | 100-500 MB | 3-15 GB |
| .app | 200-800 MB | 200-800 MB | 6-24 GB |

**Not:** Zone dosyaları sıkıştırılmış olarak indirilir, ancak parse edildikten sonra daha fazla yer kaplar.

### Veritabanı Boyutları

| Kayıt Sayısı | Tahmini Boyut |
|--------------|---------------|
| 1 milyon domain | ~500 MB - 1 GB |
| 10 milyon domain | ~5-10 GB |
| 100 milyon domain | ~50-100 GB |
| 1 milyar domain | ~500 GB - 1 TB |

**Not:** Index'ler ve ilişkiler boyutu artırır.

### Memory Kullanımı

| İşlem | RAM Kullanımı |
|-------|---------------|
| FastAPI (idle) | 200-300 MB |
| FastAPI (active) | 500 MB - 1 GB |
| MySQL (idle) | 500 MB - 1 GB |
| MySQL (active) | 2-4 GB |
| Zone Parsing (1 GB file) | 1-2 GB (peak) |
| Zone Parsing (5 GB file) | 3-5 GB (peak) |
| Drop Detection | 500 MB - 1 GB |

### CPU Kullanımı

| İşlem | CPU Kullanımı |
|-------|---------------|
| Zone Parsing | %50-100 (single core) |
| Drop Detection | %30-70 (single core) |
| Database Queries | %10-30 |
| API Requests | %5-20 |

---

## 7. VPS SAĞLAYICI ÖNERİLERİ

### Bütçe Dostu Seçenekler

#### 1. Hetzner (Önerilen - En Uygun)
- **Lokasyon:** Almanya, Finlandiya
- **Fiyat:** €4-50/ay
- **Özellikler:** Yüksek performans, düşük fiyat
- **Önerilen Plan:** CPX21 (4 vCore, 8 GB RAM, 160 GB SSD) - €8.11/ay

#### 2. DigitalOcean
- **Lokasyon:** Global
- **Fiyat:** $12-80/ay
- **Özellikler:** Kolay kullanım, iyi dokümantasyon
- **Önerilen Plan:** 4 vCore, 8 GB RAM, 160 GB SSD - $48/ay

#### 3. Vultr
- **Lokasyon:** Global
- **Fiyat:** $12-80/ay
- **Özellikler:** Yüksek performans, esnek fiyatlandırma
- **Önerilen Plan:** 4 vCore, 8 GB RAM, 160 GB SSD - $40/ay

#### 4. Linode (Akamai)
- **Lokasyon:** Global
- **Fiyat:** $12-80/ay
- **Özellikler:** Güvenilir, iyi destek
- **Önerilen Plan:** 4 vCore, 8 GB RAM, 160 GB SSD - $48/ay

### Enterprise Seçenekler

#### 1. AWS Lightsail
- **Lokasyon:** Global
- **Fiyat:** $40-160/ay
- **Özellikler:** AWS ekosistemi, kolay ölçeklendirme

#### 2. Google Cloud Platform
- **Lokasyon:** Global
- **Fiyat:** $30-150/ay
- **Özellikler:** Yüksek performans, iyi dokümantasyon

#### 3. Azure
- **Lokasyon:** Global
- **Fiyat:** $40-160/ay
- **Özellikler:** Enterprise özellikler

### Önerilen Başlangıç Konfigürasyonu

**Hetzner CPX21 (Önerilen)**
- 4 vCore AMD EPYC
- 8 GB RAM
- 160 GB NVMe SSD
- 20 TB Traffic
- **Fiyat:** €8.11/ay (~$9/ay)

Bu konfigürasyon 10-20 TLD takibi için yeterlidir.

---

## 8. OPTİMİZASYON İPUÇLARI

### Disk Optimizasyonu

1. **SSD Kullanın**
   - Zone dosyaları parsing için yüksek I/O gerektirir
   - SSD, HDD'den 10-100x daha hızlıdır

2. **Zone Dosyalarını Arşivleyin**
   - Eski zone dosyalarını sıkıştırın (gzip)
   - 90 günden eski dosyaları harici depolamaya taşıyın

3. **Veritabanı Optimizasyonu**
   - Eski kayıtları arşivleyin (1 yıldan eski)
   - Partition kullanın (drop_date bazlı)
   - Index'leri optimize edin

### Memory Optimizasyonu

1. **Chunk-based Processing**
   - Büyük dosyaları parçalara bölün (zaten implement edildi)
   - Memory kullanımını sınırlayın

2. **MySQL Buffer Pool**
   ```ini
   innodb_buffer_pool_size = 2G  # RAM'in %50-70'i
   ```

3. **Python Memory Management**
   - Garbage collection'ı optimize edin
   - Generator kullanın (zaten implement edildi)

### CPU Optimizasyonu

1. **Multi-threading**
   - Zone parsing'i paralel yapın (gelecek özellik)
   - Drop detection'ı paralel yapın

2. **Cron Job Scheduling**
   - İşlemleri gece saatlerinde çalıştırın
   - Yükü dağıtın

### Network Optimizasyonu

1. **CDN Kullanın**
   - Static dosyalar için CDN (Cloudflare ücretsiz)

2. **Zone Dosyalarını Cache'leyin**
   - İndirilen zone dosyalarını cache'leyin
   - Tekrar indirmeyi önleyin

### Database Optimizasyonu

1. **Connection Pooling**
   ```python
   # SQLAlchemy connection pool
   pool_size=10
   max_overflow=20
   ```

2. **Query Optimization**
   - Index'leri kullanın
   - N+1 query problemini önleyin
   - Pagination kullanın

3. **Read Replicas**
   - Büyük ölçekte read replica kullanın
   - Write'ları primary'e, read'leri replica'ya yönlendirin

---

## 📊 ÖZET TABLO

| Senaryo | CPU | RAM | Disk | Bandwidth | Maliyet/ay |
|---------|-----|-----|------|-----------|------------|
| **Test/Dev** | 2 vCore | 4 GB | 100 GB SSD | 500 GB | $12-24 |
| **Küçük Prod** | 4 vCore | 8 GB | 200 GB SSD | 2 TB | $24-48 |
| **Orta Prod** | 6-8 vCore | 16 GB | 500 GB SSD | 5 TB | $60-120 |
| **Büyük Prod** | 8-12 vCore | 32 GB | 1 TB SSD | 10 TB | $120-240 |
| **Enterprise** | 16+ vCore | 64+ GB | 2+ TB SSD | Unlimited | $500+ |

---

## 🎯 ÖNERİLER

### Başlangıç İçin
1. **Hetzner CPX21** (€8.11/ay) ile başlayın
2. 10-20 TLD ile test edin
3. Performansı izleyin
4. Gerektiğinde ölçeklendirin

### Production İçin
1. **4 vCore, 8 GB RAM, 200 GB SSD** minimum
2. **SSD kullanın** (zorunlu)
3. **Backup stratejisi** oluşturun
4. **Monitoring** kurun (Prometheus, Grafana)

### Ölçeklendirme
1. Önce RAM artırın
2. Sonra CPU artırın
3. Disk'i son olarak artırın
4. Database'i ayrı sunucuya taşıyın

---

## 📝 NOTLAR

- **SSD zorunludur** - HDD ile çalışmaz (çok yavaş)
- **Zone dosyaları büyük** - Disk alanını planlayın
- **Memory önemli** - Parsing sırasında yüksek kullanım
- **Backup önemli** - Veritabanı ve zone dosyalarını yedekleyin
- **Monitoring önemli** - Kaynak kullanımını izleyin

---

*Bu doküman 31 Aralık 2025 tarihinde güncellenmiştir.*


