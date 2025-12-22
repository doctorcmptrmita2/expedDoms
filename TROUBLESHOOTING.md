# EasyPanel Sorun Giderme Rehberi

## "Service is not reachable" Hatası

Bu hata genellikle şu nedenlerden kaynaklanır:

### 1. Container Başlatma Hatası

**Kontrol:**
- EasyPanel'de **Logs** sekmesine gidin
- Container başlatma loglarını kontrol edin
- Hata mesajlarını arayın

**Yaygın Hatalar:**
- `ModuleNotFoundError`: Eksik Python paketi
- `Database connection error`: MySQL bağlantı sorunu
- `Port already in use`: Port çakışması

### 2. Database Bağlantı Sorunu

**Kontrol:**
- `DATABASE_URL` environment variable'ını kontrol edin
- MySQL servisinin çalıştığından emin olun
- Network ayarlarını kontrol edin (aynı network'te olmalılar)

**Çözüm:**
```bash
# Terminal'den test edin
python -c "from app.core.database import engine; engine.connect(); print('DB OK')"
```

### 3. Port Mapping Sorunu

**Kontrol:**
- Container port: `8000` olmalı
- Host port: Otomatik veya manuel ayarlanmış olmalı
- Port çakışması olmamalı

### 4. Health Check Başarısız

**Kontrol:**
- `/health` endpoint'i çalışıyor mu?
- Health check timeout süresi yeterli mi?

**Test:**
```bash
curl http://localhost:8000/health
# Beklenen: {"status": "ok"}
```

### 5. Static Files Mount Hatası

**Kontrol:**
- `static/` dizini mevcut mu?
- Dosya izinleri doğru mu?

**Çözüm:**
- Static dosyalar opsiyonel, uygulama çalışmalı
- Eğer hata veriyorsa, mount'u kaldırın

### 6. Environment Variables Eksik

**Gerekli Variables:**
```
DATABASE_URL=mysql+pymysql://root:PASSWORD@mysql:3306/expireddomain
ENV=production
DATA_DIR=/app/data
```

### 7. Migration Hatası

**Kontrol:**
- Database oluşturulmuş mu?
- Migration'lar çalıştırılmış mı?

**Çözüm:**
```bash
# Terminal'den migration çalıştır
alembic upgrade head
```

## Adım Adım Debug

1. **Logları Kontrol Et**
   - EasyPanel'de **Logs** sekmesine git
   - Son 100 satırı kontrol et
   - Hata mesajlarını ara

2. **Container Durumunu Kontrol Et**
   - Container çalışıyor mu?
   - Restart loop'ta mı?
   - Memory/CPU limitleri aşılmış mı?

3. **Health Check'i Test Et**
   - Terminal'den: `curl http://localhost:8000/health`
   - Beklenen: `{"status": "ok"}`

4. **Database Bağlantısını Test Et**
   - Terminal'den database bağlantısını test et
   - MySQL servisinin çalıştığından emin ol

5. **Port'u Kontrol Et**
   - Container port 8000'de dinliyor mu?
   - Host port mapping doğru mu?

## Hızlı Çözümler

### Container Yeniden Başlatma
```bash
# EasyPanel'de "Restart" butonuna tıkla
```

### Logları Temizle ve Yeniden Başlat
1. Logları kontrol et
2. Hataları not et
3. Container'ı restart et
4. Yeni logları kontrol et

### Database Migration'ı Yeniden Çalıştır
```bash
# Terminal'den
alembic downgrade base
alembic upgrade head
```

### Environment Variables'ı Kontrol Et
- Tüm gerekli variables'ların ayarlandığından emin ol
- Özellikle `DATABASE_URL` doğru mu?

## Destek

Sorun devam ederse:
1. Logları kaydedin
2. Environment variables'ları kontrol edin (şifreleri gizleyerek)
3. Container durumunu kontrol edin
4. Network ayarlarını kontrol edin











