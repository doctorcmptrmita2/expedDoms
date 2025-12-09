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

### Migration Hatası: "Can't connect to MySQL" veya "Name or service not known"

**Sorun:** MySQL hostname'i (`mysql`) çözümlenemiyor.

**Çözüm Adımları:**

1. **MySQL Servis Adını Bulun:**
   - EasyPanel'de **Services** sekmesine gidin
   - MySQL servisinizin **Service Name** veya **Internal Name**'ini bulun
   - Örnek: `expireddomain-mysql`, `mysql`, `mysql-1`, vb.

2. **DATABASE_URL'i Güncelleyin:**
   - EasyPanel'de projenizin **Environment Variables** sekmesine gidin
   - `DATABASE_URL` değişkenini bulun
   - Hostname kısmını gerçek MySQL servis adıyla değiştirin
   - Format: `mysql+pymysql://user:password@SERVICE_NAME:3306/database`
   - Örnek: `mysql+pymysql://root:password@expireddomain-mysql:3306/expireddomain`

3. **Container'ı Yeniden Başlatın:**
   - Environment variable değişikliğinden sonra container'ı restart edin
   - EasyPanel'de "Restart" butonuna tıklayın

4. **Bağlantıyı Test Edin:**
   ```bash
   # Container içinde
   python3 check_db_connection.py
   ```

**Not:** Şifrede özel karakterler varsa URL-encode edin (`@` → `%40`, `#` → `%23`, vb.)

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

