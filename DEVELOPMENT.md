# 🚀 ExpiredDomain.dev - Geliştirme Planı

✅ Oluşturulan Hesaplar
Hesap	Email	Şifre	Özellikler
Demo	demo@expireddomain.dev	demo123	Ücretsiz (3 watchlist, 100 favori)
Premium	premium@expireddomain.dev	premium123	Premium (20 watchlist, sınırsız favori)
Admin	admin@expireddomain.dev	admin123	Admin + Premium
Test	test@example.com	Test123456	Ücretsiz (kayıt testinden)

## 📋 Mevcut Durum Özeti
## 📋 Mevcut Durum Özeti

### ✅ Tamamlanan Özellikler

| Özellik | Açıklama | Durum |
|---------|----------|-------|
| ICANN CZDS Entegrasyonu | Zone dosyası indirme ve parsing | ✅ Tamamlandı |
| Drop Tespit Sistemi | Günlük düşen domain'leri tespit etme | ✅ Tamamlandı |
| Domain Listeleme | Filtreleme, arama, sayfalama | ✅ Tamamlandı |
| TLD Yönetimi | Aktif TLD'leri yönetme | ✅ Tamamlandı |
| Admin Paneli | CZDS kimlik doğrulama | ✅ Tamamlandı |
| Modern UI | Tailwind CSS, neon tema | ✅ Tamamlandı |
| RESTful API | v1 API endpoints | ✅ Tamamlandı |
| Docker Desteği | Container deployment | ✅ Tamamlandı |

### 📁 Mevcut Proje Yapısı

```
app/
├── api/v1/          # API endpoints (drops, tlds, czds, process, import)
├── core/            # Config, database
├── models/          # SQLAlchemy models (Drop, TLD)
├── schemas/         # Pydantic schemas
├── services/        # Business logic (CZDS client, drop detector)
├── web/             # Web routes (admin, domains, routes)
templates/           # Jinja2 templates
static/              # CSS, JS
data/zones/          # Zone dosyaları
```

---

## 🎯 Önerilen Yeni Özellikler

### 🔥 Yüksek Öncelikli (High Priority)

#### 1. 👤 Kullanıcı Yönetim Sistemi
**Süre:** 3-5 gün | **Zorluk:** Orta

```python
# Yeni modeller
class User(Base):
    id: int
    email: str
    password_hash: str
    is_active: bool
    is_premium: bool
    created_at: datetime

class UserWatchlist(Base):
    id: int
    user_id: int
    domain_pattern: str  # ör: "*.dev", "short*.com"
    tld_filter: str
    notify_email: bool
    notify_telegram: bool
```

**Özellikler:**
- 📝 Kayıt / Giriş / Şifre sıfırlama
- 🔐 JWT tabanlı kimlik doğrulama
- 👑 Premium / Free kullanıcı ayrımı
- 📊 Kullanıcı dashboard'u

---

#### 2. ⭐ Domain Favorileri & Watchlist
**Süre:** 2-3 gün | **Zorluk:** Kolay

```python
class Favorite(Base):
    id: int
    user_id: int
    domain_id: int
    notes: str
    created_at: datetime

class WatchlistAlert(Base):
    id: int
    user_id: int
    keyword: str
    min_length: int
    max_length: int
    tld_ids: List[int]
    is_active: bool
```

**Özellikler:**
- ⭐ Domain favorilere ekleme
- 🔔 Watchlist oluşturma (pattern matching)
- 📧 Eşleşme bildirimi

---

#### 3. 📊 Domain Kalite Skoru (Quality Score)
**Süre:** 3-4 gün | **Zorluk:** Orta

```python
def calculate_quality_score(domain: str, tld: str) -> int:
    """
    Quality score hesaplama (0-100)
    
    Faktörler:
    - Uzunluk (kısa = daha iyi)
    - Karakter tipi (sadece harf = daha iyi)
    - TLD değeri
    - Kelime içerme (dictionary word = bonus)
    - Rakam pozisyonu
    - Hyphens (-) varlığı
    """
    score = 50
    
    # Uzunluk bonusu
    if len(domain) <= 4:
        score += 30
    elif len(domain) <= 6:
        score += 20
    elif len(domain) <= 8:
        score += 10
    
    # Sadece harf bonusu
    if domain.isalpha():
        score += 15
    
    # Dictionary word check
    if is_dictionary_word(domain):
        score += 20
    
    return min(100, max(0, score))
```

**Eklentiler:**
- 🎯 Premium TLD ağırlıkları (.dev, .app, .io daha değerli)
- 📖 Sözlük kelime kontrolü
- 🔢 Brandable isim tespiti

---

#### 4. 🔔 Bildirim Sistemi
**Süre:** 3-4 gün | **Zorluk:** Orta

```python
class NotificationChannel(Enum):
    EMAIL = "email"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WEBHOOK = "webhook"

class Notification(Base):
    id: int
    user_id: int
    channel: NotificationChannel
    template: str
    sent_at: datetime
    status: str
```

**Desteklenen Kanallar:**
- 📧 Email (SMTP)
- 💬 Telegram Bot
- 🎮 Discord Webhook
- 🔗 Custom Webhook

---

### 🔶 Orta Öncelikli (Medium Priority)

#### 5. 🔍 SEO Metrikleri Entegrasyonu
**Süre:** 4-5 gün | **Zorluk:** Yüksek

```python
class DomainMetrics(Base):
    id: int
    domain_id: int
    # Moz Metrics
    moz_da: int  # Domain Authority
    moz_pa: int  # Page Authority
    moz_spam_score: int
    # Majestic Metrics
    majestic_tf: int  # Trust Flow
    majestic_cf: int  # Citation Flow
    # Backlinks
    backlink_count: int
    referring_domains: int
    # Timestamps
    fetched_at: datetime
```

**Entegrasyonlar:**
- 🔵 Moz API
- 🟣 Majestic API
- 🟢 Ahrefs API (opsiyonel)

---

#### 6. 📜 Whois & Domain Geçmişi
**Süre:** 3-4 gün | **Zorluk:** Orta

```python
class DomainHistory(Base):
    id: int
    domain: str
    wayback_snapshots: int
    first_registered: date
    previous_owners: List[str]
    archive_url: str
```

**Özellikler:**
- 📅 Wayback Machine entegrasyonu
- 👤 Önceki sahip bilgisi
- 📊 Domain yaşı hesaplama

---

#### 7. 📈 İstatistik Dashboard'u
**Süre:** 2-3 gün | **Zorluk:** Kolay

```javascript
// Chart.js ile grafikler
- Günlük drop sayıları (line chart)
- TLD bazlı dağılım (pie chart)
- Uzunluk dağılımı (bar chart)
- Charset tipi dağılımı (doughnut chart)
- Haftalık/Aylık trend analizi
```

**Grafikler:**
- 📉 Zaman serisi analizi
- 🥧 TLD dağılımı
- 📊 Uzunluk histogramı

---

#### 8. 📤 Dışa Aktarma (Export)
**Süre:** 1-2 gün | **Zorluk:** Kolay

```python
@router.get("/api/v1/export/csv")
def export_csv(
    date_filter: date,
    tld: str = None,
    min_length: int = None,
    max_length: int = None
) -> StreamingResponse:
    """CSV formatında dışa aktar"""
    
@router.get("/api/v1/export/json")
def export_json(...) -> JSONResponse:
    """JSON formatında dışa aktar"""
```

**Formatlar:**
- 📄 CSV
- 📋 JSON
- 📊 Excel (openpyxl)

---

### 🔷 Düşük Öncelikli (Low Priority)

#### 9. 🏷️ Domain Kategorileme
**Süre:** 2-3 gün | **Zorluk:** Orta

```python
class DomainCategory(Enum):
    BRANDABLE = "brandable"      # Marka olabilecek
    KEYWORD = "keyword"          # Anahtar kelime içeren
    NUMERIC = "numeric"          # Sayısal
    SHORT = "short"              # Kısa (<=4 karakter)
    PREMIUM = "premium"          # Premium TLD
    DICTIONARY = "dictionary"    # Sözlük kelimesi
```

---

#### 10. 💰 Registrar Fiyat Karşılaştırması
**Süre:** 3-4 gün | **Zorluk:** Orta

```python
class RegistrarPrice(Base):
    id: int
    tld: str
    registrar: str  # namecheap, godaddy, cloudflare, porkbun
    register_price: Decimal
    renew_price: Decimal
    transfer_price: Decimal
    updated_at: datetime
```

**Registrar'lar:**
- Namecheap
- GoDaddy
- Cloudflare
- Porkbun
- Google Domains

---

#### 11. 🔄 Availability Check
**Süre:** 2-3 gün | **Zorluk:** Orta

```python
async def check_availability(domain: str, tld: str) -> dict:
    """
    Domain müsaitlik kontrolü
    
    Returns:
        {
            "domain": "example.dev",
            "available": True,
            "registrar_prices": {...},
            "checked_at": "2025-12-11T10:00:00Z"
        }
    """
```

---

#### 12. 🔑 API Key Sistemi
**Süre:** 2-3 gün | **Zorluk:** Kolay

```python
class APIKey(Base):
    id: int
    user_id: int
    key: str  # sha256 hash
    name: str
    rate_limit: int  # requests per minute
    is_active: bool
    last_used_at: datetime
    created_at: datetime
```

**Özellikler:**
- 🔐 API key oluşturma/silme
- ⚡ Rate limiting
- 📊 Kullanım istatistikleri

---

#### 13. ⏰ Cron Job / Scheduler
**Süre:** 1-2 gün | **Zorluk:** Kolay

```python
# APScheduler veya Celery ile
SCHEDULED_TASKS = {
    "fetch_zones": "0 2 * * *",      # Her gün 02:00
    "process_drops": "0 3 * * *",     # Her gün 03:00
    "send_notifications": "0 4 * * *", # Her gün 04:00
    "cleanup_old_data": "0 0 * * 0",  # Her Pazar gece yarısı
}
```

---

#### 14. 🌍 Çoklu Dil Desteği (i18n)
**Süre:** 2-3 gün | **Zorluk:** Kolay

```python
# Flask-Babel veya custom i18n
SUPPORTED_LANGUAGES = ["en", "tr", "de", "es", "fr"]
```

---

## 📅 Önerilen Geliştirme Yol Haritası

### Faz 1: Temel Özellikler (2-3 Hafta)
```
Hafta 1:
├── ✅ Kullanıcı sistemi (kayıt/giriş)
├── ✅ JWT authentication
└── ✅ Temel dashboard

Hafta 2:
├── ✅ Favoriler sistemi
├── ✅ Watchlist oluşturma
└── ✅ Quality score hesaplama

Hafta 3:
├── ✅ Email bildirimleri
├── ✅ İstatistik grafikleri
└── ✅ CSV/JSON export
```

### Faz 2: Gelişmiş Özellikler (3-4 Hafta)
```
Hafta 4-5:
├── 🔄 SEO metrikleri entegrasyonu
├── 🔄 Whois/Domain geçmişi
└── 🔄 Telegram bildirimleri

Hafta 6-7:
├── 🔄 Availability check
├── 🔄 Registrar fiyatları
└── 🔄 API key sistemi
```

### Faz 3: Premium Özellikler (2-3 Hafta)
```
Hafta 8-10:
├── 📋 Premium kullanıcı özellikleri
├── 📋 Gelişmiş filtreleme
├── 📋 Backorder entegrasyonu
└── 📋 Webhook desteği
```

---

## 💡 Teknik Öneriler

### Veritabanı İndeksleri
```sql
-- Performans için önerilen indeksler
CREATE INDEX idx_drops_date_tld ON dropped_domains(drop_date, tld_id);
CREATE INDEX idx_drops_domain_search ON dropped_domains(domain varchar_pattern_ops);
CREATE INDEX idx_drops_quality ON dropped_domains(quality_score DESC);
CREATE INDEX idx_drops_length ON dropped_domains(length);
```

### Cache Stratejisi
```python
# Redis ile cache
CACHE_SETTINGS = {
    "drops_list": 300,      # 5 dakika
    "tld_stats": 3600,      # 1 saat
    "quality_scores": 86400, # 24 saat
}
```

### Rate Limiting
```python
# slowapi ile rate limiting
@limiter.limit("100/minute")
@router.get("/api/v1/drops")
async def list_drops():
    pass
```

---

## 🛠️ Önerilen Teknolojiler

| Kategori | Mevcut | Önerilen Eklenti |
|----------|--------|------------------|
| Cache | - | Redis |
| Task Queue | - | Celery / RQ |
| Scheduler | - | APScheduler |
| Email | - | SendGrid / Mailgun |
| Monitoring | - | Sentry |
| Analytics | - | PostHog / Plausible |
| Search | - | Elasticsearch (opsiyonel) |

---

## 📊 Tahmini İş Gücü

| Özellik | Süre | Öncelik |
|---------|------|---------|
| Kullanıcı Sistemi | 5 gün | 🔴 Yüksek |
| Favoriler & Watchlist | 3 gün | 🔴 Yüksek |
| Quality Score | 3 gün | 🔴 Yüksek |
| Bildirimler | 4 gün | 🔴 Yüksek |
| SEO Metrikleri | 5 gün | 🟡 Orta |
| Whois Entegrasyonu | 3 gün | 🟡 Orta |
| Dashboard Grafikleri | 2 gün | 🟡 Orta |
| Export Özelliği | 2 gün | 🟡 Orta |
| API Key Sistemi | 2 gün | 🟢 Düşük |
| Availability Check | 3 gün | 🟢 Düşük |
| **TOPLAM** | **~32 gün** | - |

---

## 🚀 Hızlı Başlangıç Önerileri

### 1. Hemen Başlanabilecek Küçük İyileştirmeler

```python
# 1. Domain kopyalama butonu (✅ mevcut, toast ekle)
# 2. Sayfa başına sonuç sayısı seçimi (✅ mevcut)
# 3. Klavye kısayolları
# 4. Dark/Light mode toggle
# 5. Responsive iyileştirmeler
```

### 2. Önerilen İlk Adımlar

1. **Kullanıcı tablosu oluştur** (migration)
2. **JWT middleware ekle**
3. **Login/Register sayfaları**
4. **Favoriler API endpoint'i**
5. **Quality score algoritması**

---

## 📝 Sonuç

ExpiredDomain.dev şu anda temel işlevselliğe sahip, çalışan bir uygulama. Yukarıdaki özellikler eklendiğinde:

- 🎯 **Kullanıcı bağlılığı** artacak
- 💰 **Monetizasyon** fırsatları (premium üyelik)
- 📈 **Rekabet avantajı** sağlanacak
- 🔄 **Tekrar ziyaret** oranı yükselecek

**Önerilen öncelik sırası:**
1. Kullanıcı sistemi + Favoriler
2. Quality Score + Bildirimler
3. SEO Metrikleri + Export
4. Premium özellikler

---

*Son güncelleme: 2025-12-11*
*Versiyon: 1.0.0*

