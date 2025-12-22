# EasyPanel "Service is not reachable" Çözümü

## ✅ Container İçinde Her Şey Çalışıyor!

Test sonuçları:
- ✓ App import: OK
- ✓ Database URL: Doğru
- ✓ Health endpoint: `{"status":"ok"}`

## 🔍 Sorun: EasyPanel Health Check

Sorun muhtemelen EasyPanel'in health check konfigürasyonunda.

## Çözüm Adımları

### 1. EasyPanel'de Health Check Ayarlarını Kontrol Edin

1. **Projenize gidin** → **Settings** veya **Configuration**
2. **Health Check** sekmesine gidin
3. Şu ayarları kontrol edin:
   - **Path**: `/health` (başında `/` olmalı)
   - **Port**: `8000` (container port)
   - **Interval**: `30` saniye
   - **Timeout**: `10` saniye
   - **Start Period**: `60` saniye (container başlangıcı için)

### 2. Port Mapping Kontrolü

1. **Ports** sekmesine gidin
2. Kontrol edin:
   - **Container Port**: `8000`
   - **Protocol**: `HTTP`
   - **Public Port**: Otomatik veya manuel (örn: `8000`)

### 3. Network Ayarları

1. **Network** sekmesine gidin
2. Kontrol edin:
   - Container ve MySQL aynı network'te mi?
   - Service discovery çalışıyor mu? (`mysql` hostname erişilebilir mi?)

### 4. Health Check'i Devre Dışı Bırak (Geçici Test)

Eğer health check sorun çıkarıyorsa, geçici olarak devre dışı bırakın:
1. **Settings** → **Health Check**
2. **Disable** veya **Skip** seçeneğini işaretleyin
3. Container'ın çalışıp çalışmadığını kontrol edin

### 5. Manuel Test

EasyPanel'in dışından test edin:
```bash
# Container IP'sini bulun ve test edin
curl http://CONTAINER_IP:8000/health
```

## Alternatif Çözümler

### Seçenek 1: Health Check Path'i Değiştir

EasyPanel'de health check path'ini `/` olarak ayarlayın (ana sayfa):
- Health check path: `/`
- Beklenen response: HTML (200 OK)

### Seçenek 2: Health Check'i Kaldır

Geçici olarak health check'i kaldırıp container'ın çalışıp çalışmadığını kontrol edin.

### Seçenek 3: Liveness ve Readiness Probe

EasyPanel'de hem liveness hem readiness probe varsa:
- **Liveness**: `/health` (container çalışıyor mu?)
- **Readiness**: `/health` (traffic alabilir mi?)

Her ikisini de `/health` olarak ayarlayın.

## Hızlı Test

Container içinde çalışan uygulamayı dışarıdan test edin:

1. **EasyPanel'de Domain/URL'i kontrol edin**
2. Tarayıcıdan açın: `https://expireddomain-expireddomainpro.lc58dd.easypanel.host/health`
3. Beklenen: `{"status":"ok"}`

Eğer bu çalışıyorsa, sorun sadece EasyPanel'in health check konfigürasyonunda.

## Son Kontrol

EasyPanel'de şunları kontrol edin:

- [ ] Container çalışıyor mu? (Status: Running)
- [ ] Port mapping doğru mu? (8000 → 8000)
- [ ] Health check path doğru mu? (`/health`)
- [ ] Health check timeout yeterli mi? (60 saniye start period)
- [ ] Domain/URL erişilebilir mi?

Eğer domain üzerinden `/health` endpoint'i çalışıyorsa, sorun sadece EasyPanel'in internal health check'inde.











