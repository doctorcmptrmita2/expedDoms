# ExpiredDomain.dev - EasyPanel Deployment Guide

Bu doküman, ExpiredDomain.dev uygulamasını EasyPanel'e deploy etmek için adım adım talimatlar içerir.

## Ön Gereksinimler

- EasyPanel kurulu ve çalışıyor olmalı
- MySQL veritabanı erişimi (EasyPanel'de MySQL servisi veya harici MySQL)
- Domain adresi (opsiyonel, subdomain de kullanılabilir)

## Adım 1: Proje Dosyalarını Hazırlama

Proje dosyalarınız hazır:
- ✅ `Dockerfile` - Container image tanımı
- ✅ `.dockerignore` - Docker build'de ignore edilecek dosyalar
- ✅ `requirements.txt` - Python bağımlılıkları
- ✅ `docker-compose.yml` - Local test için (opsiyonel)

## Adım 2: Git Repository Hazırlama (Önerilen)

EasyPanel genellikle Git repository'den deploy eder:

```bash
# Git repository oluştur
git init
git add .
git commit -m "Initial commit"

# GitHub/GitLab'a push et
git remote add origin <your-repo-url>
git push -u origin main
```

## Adım 3: EasyPanel'de Proje Oluşturma

1. **EasyPanel Dashboard'a giriş yapın**
   - Tarayıcıda EasyPanel URL'inize gidin
   - Admin kullanıcı ile giriş yapın

2. **Yeni Proje Oluştur**
   - "Projects" veya "Applications" sekmesine gidin
   - "New Project" veya "Create Application" butonuna tıklayın

3. **Proje Bilgilerini Girin**
   - **Project Name**: `expireddomain` veya `expireddomain-dev`
   - **Description**: `Daily dropped domains explorer using ICANN CZDS zone files`

## Adım 4: Git Repository Bağlama

1. **Source Configuration**
   - **Source Type**: `Git Repository` seçin
   - **Repository URL**: Git repository URL'inizi girin
     - Örnek: `https://github.com/username/expireddomain.git`
   - **Branch**: `main` veya `master`
   - **Build Pack**: `Dockerfile` seçin

2. **Build Settings**
   - **Dockerfile Path**: `Dockerfile` (root'ta olduğu için boş bırakabilirsiniz)
   - **Build Context**: `.` (root directory)

## Adım 5: Environment Variables (Çevre Değişkenleri)

EasyPanel'de Environment Variables sekmesine gidin ve şunları ekleyin:

```
APP_NAME=ExpiredDomain.dev
ENV=production
DATABASE_URL=mysql+pymysql://root:PASSWORD@mysql:3306/expireddomain
CZDS_USERNAME=
CZDS_PASSWORD=
CZDS_AUTH_URL=https://account-api.icann.org/api/authenticate
CZDS_BASE_URL=https://czds-api.icann.org
CZDS_DOWNLOAD_BASE_URL=https://czds-download-api.icann.org
TRACKED_TLDS=zip,works,dev,app
DATA_DIR=/app/data
```

**Önemli**: `DATABASE_URL` içindeki `PASSWORD` kısmını gerçek MySQL şifrenizle değiştirin.

## Adım 6: MySQL Veritabanı Kurulumu

### Seçenek A: EasyPanel'de MySQL Servisi Oluşturma

1. EasyPanel'de "Services" veya "Databases" sekmesine gidin
2. "Add Service" → "MySQL" seçin
3. Ayarlar:
   - **Service Name**: `expireddomain-mysql`
   - **MySQL Version**: `8.0`
   - **Root Password**: Güçlü bir şifre belirleyin
   - **Database Name**: `expireddomain`
   - **Character Set**: `utf8mb4`
   - **Collation**: `utf8mb4_unicode_ci`

4. MySQL servisinin internal URL'ini not edin (örn: `mysql:3306`)

### Seçenek B: Harici MySQL Kullanma

Eğer harici MySQL kullanıyorsanız:
- `DATABASE_URL` environment variable'ını harici MySQL bilgileriyle güncelleyin
- Örnek: `mysql+pymysql://user:pass@external-mysql-host:3306/expireddomain`

## Adım 7: Volume/Storage Ayarları

Zone dosyaları için persistent storage ekleyin:

1. **Volumes** sekmesine gidin
2. **Add Volume**:
   - **Name**: `expireddomain-data`
   - **Mount Path**: `/app/data`
   - **Type**: `Persistent Volume`

Bu sayede zone dosyaları container yeniden başlatıldığında kaybolmaz.

## Adım 8: Port ve Domain Ayarları

1. **Ports** sekmesine gidin:
   - **Container Port**: `8000`
   - **Host Port**: Otomatik veya manuel (örn: `8000`)

2. **Domains** sekmesine gidin (opsiyonel):
   - **Domain**: `expireddomain.yourdomain.com`
   - **SSL**: Otomatik SSL sertifikası (Let's Encrypt) etkinleştirin

## Adım 9: Deploy ve Build

1. **Deploy** butonuna tıklayın
2. Build işlemi başlayacak (5-10 dakika sürebilir)
3. Build loglarını takip edin:
   - Başarılı: "Build completed successfully"
   - Hata varsa logları kontrol edin

## Adım 10: İlk Kurulum (Database Migration)

Container çalıştıktan sonra, database migration'ları çalıştırın:

### EasyPanel Terminal/Exec kullanarak:

1. EasyPanel'de projenize gidin
2. "Terminal" veya "Exec" sekmesine tıklayın
3. Şu komutları çalıştırın:

```bash
# Alembic migration'ları çalıştır
alembic upgrade head

# TLD'leri oluştur (opsiyonel)
python -c "from app.core.database import SessionLocal; from app.models.tld import Tld; from app.core.config import get_settings; db = SessionLocal(); settings = get_settings(); [db.add(Tld(name=t.lower(), display_name=t.lower(), is_active=True)) for t in settings.tracked_tlds_list if not db.query(Tld).filter(Tld.name == t.lower()).first()]; db.commit(); print('TLDs created')"
```

## Adım 11: Uygulamayı Test Etme

1. **Health Check**: `http://your-domain/health` adresine gidin
   - Beklenen: `{"status": "ok"}`

2. **Ana Sayfa**: `http://your-domain/` adresine gidin
   - Ana sayfa görünmeli

3. **Admin Panel**: `http://your-domain/admin` adresine gidin
   - CZDS credentials ile giriş yapabilmelisiniz

## Adım 12: Günlük Script Kurulumu (Cron Job)

EasyPanel'de cron job ekleyin:

1. **Cron Jobs** sekmesine gidin
2. **Add Cron Job**:
   - **Schedule**: `0 2 * * *` (Her gün saat 02:00'de)
   - **Command**: `python -m scripts.fetch_drops`
   - **Container**: Ana uygulama container'ı

## Sorun Giderme

### Database Bağlantı Hatası

- `DATABASE_URL` environment variable'ını kontrol edin
- MySQL servisinin çalıştığından emin olun
- Network ayarlarını kontrol edin (aynı network'te olmalılar)

### Port Çakışması

- Farklı bir host port kullanın
- Veya port mapping'i kaldırıp sadece domain üzerinden erişin

### Build Hatası

- Build loglarını kontrol edin
- `requirements.txt` dosyasındaki paketlerin doğru olduğundan emin olun
- Dockerfile'daki Python versiyonunu kontrol edin

### Migration Hatası

- Database'in oluşturulduğundan emin olun
- Alembic versiyonlarını kontrol edin
- `alembic.ini` dosyasındaki database URL'i kontrol edin

## Production Önerileri

1. **SSL Sertifikası**: Let's Encrypt ile otomatik SSL kullanın
2. **Backup**: MySQL veritabanını düzenli yedekleyin
3. **Monitoring**: Logları düzenli kontrol edin
4. **Updates**: Güvenlik güncellemelerini takip edin
5. **Resource Limits**: Container için CPU/Memory limitleri ayarlayın

## Destek

Sorun yaşarsanız:
1. EasyPanel loglarını kontrol edin
2. Container loglarını inceleyin
3. Database bağlantısını test edin
4. Environment variables'ları doğrulayın











