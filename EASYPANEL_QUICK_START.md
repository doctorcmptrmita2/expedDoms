# EasyPanel Hızlı Kurulum Rehberi

## 🚀 5 Dakikada EasyPanel'e Deploy

### Adım 1: Git Repository Hazırlama (2 dakika)

```bash
# Projeyi Git'e ekle
git init
git add .
git commit -m "Ready for EasyPanel"

# GitHub/GitLab'a push et
git remote add origin <your-repo-url>
git push -u origin main
```

### Adım 2: EasyPanel'de Proje Oluşturma (1 dakika)

1. EasyPanel dashboard'a giriş yap
2. **"New Project"** veya **"Create Application"** butonuna tıkla
3. **Proje Adı**: `expireddomain`
4. **Source Type**: `Git Repository`
5. **Repository URL**: Git repo URL'inizi yapıştır
6. **Branch**: `main`
7. **Build Pack**: `Dockerfile` seç

### Adım 3: Environment Variables (1 dakika)

EasyPanel'de **Environment Variables** sekmesine git ve ekle:

```
DATABASE_URL=mysql+pymysql://root:ŞİFRENİZ@mysql:3306/expireddomain
TRACKED_TLDS=zip,works,dev,app
ENV=production
```

**Önemli**: `ŞİFRENİZ` kısmını gerçek MySQL şifresiyle değiştir!

### Adım 4: MySQL Servisi Oluşturma (1 dakika)

1. EasyPanel'de **"Services"** veya **"Databases"** sekmesine git
2. **"Add Service"** → **"MySQL"** seç
3. Ayarlar:
   - **Service Name**: `expireddomain-mysql`
   - **Root Password**: Güçlü bir şifre (yukarıdaki DATABASE_URL'de kullan)
   - **Database Name**: `expireddomain`
   - **Character Set**: `utf8mb4`

### Adım 5: Volume Ekleme (30 saniye)

1. **Volumes** sekmesine git
2. **Add Volume**:
   - **Name**: `expireddomain-data`
   - **Mount Path**: `/app/data`
   - **Type**: `Persistent Volume`

### Adım 6: Deploy! (2 dakika)

1. **"Deploy"** butonuna tıkla
2. Build işlemini bekle (5-10 dakika)
3. Build tamamlandıktan sonra **Terminal/Exec** sekmesine git
4. Şu komutu çalıştır:

```bash
alembic upgrade head
```

### Adım 7: Test Et! (30 saniye)

1. Uygulamanın URL'ine git (EasyPanel'de gösterilir)
2. `/health` endpoint'ini test et: `http://your-domain/health`
3. Ana sayfayı aç: `http://your-domain/`
4. Admin paneli aç: `http://your-domain/admin`

## ✅ Tamamlandı!

Artık uygulamanız çalışıyor. İlk zone dosyalarını indirmek için:

1. `/admin` sayfasına git
2. CZDS credentials ile giriş yap
3. Zone dosyalarını indir
4. Otomatik olarak parse edilip dropped domainler bulunacak
5. `/drops` sayfasından dropped domainleri görüntüle

## 🔧 Sorun mu Var?

### Database Bağlantı Hatası
- `DATABASE_URL` environment variable'ını kontrol et
- MySQL servisinin çalıştığından emin ol
- MySQL servis adının `mysql` olduğundan emin ol

### Build Hatası
- Build loglarını kontrol et
- `Dockerfile` dosyasının root'ta olduğundan emin ol
- Git repository'nin doğru branch'inde olduğundan emin ol

### Migration Hatası
- Database'in oluşturulduğundan emin ol
- Terminal'den `alembic upgrade head` komutunu çalıştır
- Hata mesajlarını kontrol et

## 📚 Daha Fazla Bilgi

Detaylı deployment rehberi için `DEPLOY.md` dosyasına bakın.

