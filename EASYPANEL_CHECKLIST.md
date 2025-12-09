# EasyPanel Deployment Checklist

## ✅ Kontrol Listesi

### 1. Build Ayarları
- [ ] Git repository URL doğru mu?
- [ ] Branch: `main` seçili mi?
- [ ] Build Pack: `Dockerfile` seçili mi?
- [ ] Build context: `.` (root) mi?

### 2. Environment Variables
- [ ] `DATABASE_URL` ayarlandı mı?
  - Format: `mysql+pymysql://root:PASSWORD@mysql:3306/expireddomain`
  - `PASSWORD` kısmı MySQL root şifresiyle değiştirildi mi?
- [ ] `ENV=production` ayarlandı mı?
- [ ] `DATA_DIR=/app/data` ayarlandı mı?
- [ ] `TRACKED_TLDS` ayarlandı mı? (opsiyonel)

### 3. MySQL Servisi
- [ ] MySQL servisi oluşturuldu mu?
- [ ] Service name: `mysql` mi? (DATABASE_URL'de kullanılan)
- [ ] Database: `expireddomain` oluşturuldu mu?
- [ ] Character set: `utf8mb4` mi?
- [ ] MySQL servisi çalışıyor mu?

### 4. Port Ayarları
- [ ] Container port: `8000` mi?
- [ ] HTTP port mapping aktif mi?
- [ ] Port çakışması var mı?

### 5. Volume/Storage
- [ ] Persistent volume eklendi mi?
- [ ] Mount path: `/app/data` mi?
- [ ] Volume adı: `expireddomain-data` mi?

### 6. Domain (Opsiyonel)
- [ ] Domain eklendi mi?
- [ ] SSL sertifikası alındı mı?

### 7. Build ve Deploy
- [ ] Build başarıyla tamamlandı mı?
- [ ] Container çalışıyor mu?
- [ ] Loglar hatasız mı?

### 8. Database Migration
- [ ] Terminal/Exec'ten migration çalıştırıldı mı?
  ```bash
  alembic upgrade head
  ```
- [ ] Migration başarılı mı?
- [ ] Tablolar oluşturuldu mu?

### 9. Health Check
- [ ] `/health` endpoint çalışıyor mu?
  ```bash
  curl http://your-domain/health
  ```
- [ ] Beklenen: `{"status": "ok"}`

### 10. Uygulama Testi
- [ ] Ana sayfa açılıyor mu? (`/`)
- [ ] Admin panel açılıyor mu? (`/admin`)
- [ ] Drops sayfası açılıyor mu? (`/drops`)

## 🔍 Sorun Giderme

### Container Başlamıyor
1. **Logları kontrol et** - EasyPanel'de Logs sekmesi
2. **Build loglarını kontrol et** - Hangi adımda hata var?
3. **Environment variables kontrol et** - Tüm gerekli değişkenler var mı?

### Database Bağlantı Hatası
1. **MySQL servisi çalışıyor mu?** - Services sekmesinde kontrol et
2. **DATABASE_URL doğru mu?** - Format ve şifre kontrol et
3. **Network ayarları** - Aynı network'te mi?

### Health Check Başarısız
1. **Container çalışıyor mu?** - Status kontrol et
2. **Port mapping doğru mu?** - Container port 8000 mi?
3. **Health check endpoint çalışıyor mu?** - Terminal'den test et

### 502 Bad Gateway
1. **Container crash oluyor mu?** - Logları kontrol et
2. **Startup hatası var mı?** - Import hataları kontrol et
3. **Memory limit aşıldı mı?** - Resource limits kontrol et

## 📝 Hızlı Test Komutları

```bash
# Health check
curl http://localhost:8000/health

# Database bağlantısı
python -c "from app.core.database import engine; engine.connect(); print('OK')"

# Migration durumu
alembic current

# Migration çalıştır
alembic upgrade head
```

## 🚀 Yeniden Deploy

Değişiklik yaptıktan sonra:
1. Git'e push et
2. EasyPanel'de "Rebuild" veya "Redeploy" butonuna tıkla
3. Build loglarını takip et
4. Health check'i test et

