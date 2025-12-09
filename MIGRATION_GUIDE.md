# Alembic Migration Rehberi

## Veritabanı Tablolarını Oluşturma

Veritabanı boşsa, Alembic migration'larını çalıştırarak tabloları oluşturmanız gerekiyor.

## EasyPanel'de Migration Çalıştırma

### Yöntem 1: Container Shell Üzerinden (Önerilen)

1. **EasyPanel'e giriş yapın**
2. **Projenize gidin** → Container detaylarına girin
3. **"Shell" veya "Terminal"** sekmesine tıklayın
4. **Container içinde şu komutları çalıştırın:**

```bash
# Container içine giriş yapın
cd /app

# Alembic migration'ları çalıştırın
alembic upgrade head
```

### Yöntem 2: Docker Exec ile

Eğer EasyPanel shell erişimi yoksa, Docker exec kullanabilirsiniz:

```bash
# Container ID'sini bulun
docker ps

# Container içinde migration çalıştırın
docker exec -it <container_id> alembic upgrade head
```

## Migration Sonrası Kontrol

Migration başarılı olduktan sonra:

1. **phpMyAdmin'de kontrol edin:**
   - `tlds` tablosu oluşmuş olmalı
   - `dropped_domains` tablosu oluşmuş olmalı

2. **Debug sayfasında kontrol edin:**
   - `/debug` sayfasına gidin
   - Database Statistics bölümünde hata olmamalı

## Sorun Giderme

### Migration Hatası: "Can't connect to MySQL"

**Çözüm:** `DATABASE_URL` environment variable'ını kontrol edin:
- Format: `mysql+pymysql://user:password@host:port/database`
- EasyPanel'de MySQL servis adı genellikle `mysql` olur
- Şifrede özel karakterler varsa URL-encode edin (`@` → `%40`)

### Migration Hatası: "Table already exists"

**Çözüm:** Eğer tablolar zaten varsa:
```bash
# Migration durumunu kontrol edin
alembic current

# Eğer migration uygulanmamışsa, stamp yapın
alembic stamp head
```

### Migration Hatası: "Invalid interpolation syntax"

**Çözüm:** `DATABASE_URL` içindeki `%` karakterlerini kontrol edin. Şifrede `%40` gibi URL-encoded karakterler varsa, bu normaldir.

## İlk Migration İçeriği

İlk migration şunları oluşturur:

1. **`tlds` tablosu:**
   - `id` (Primary Key)
   - `name` (Unique)
   - `display_name`
   - `is_active`
   - `last_import_date`
   - `last_drop_count`
   - `created_at`, `updated_at`

2. **`dropped_domains` tablosu:**
   - `id` (Primary Key)
   - `domain` (Indexed)
   - `tld_id` (Foreign Key → tlds.id)
   - `drop_date` (Indexed)
   - `length`
   - `label_count`
   - `charset_type`
   - `quality_score`
   - `created_at`
   - Unique constraint: `(domain, drop_date)`

## Test Etme

Migration sonrası test için:

```bash
# Container içinde Python shell açın
python3

# Test scripti
from app.core.database import SessionLocal
from app.models.tld import Tld
from app.models.drop import DroppedDomain

db = SessionLocal()
tlds = db.query(Tld).all()
print(f"TLDs found: {len(tlds)}")

drops = db.query(DroppedDomain).all()
print(f"Drops found: {len(drops)}")
db.close()
```

## Otomatik Migration (Opsiyonel)

Eğer her deploy'da otomatik migration çalıştırmak isterseniz, `Dockerfile`'a ekleyebilirsiniz:

```dockerfile
# Dockerfile sonuna ekleyin
RUN echo "alembic upgrade head" >> /app/start.sh
```

Ancak bu production'da riskli olabilir, manuel kontrol önerilir.

