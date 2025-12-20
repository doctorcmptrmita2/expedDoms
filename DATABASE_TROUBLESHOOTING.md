# Database Connection Troubleshooting

## Hata: `Can't connect to MySQL server on '@mysql'`

Bu hata genellikle şu nedenlerden kaynaklanır:

### 1. DATABASE_URL Format Sorunu

**Kontrol:**
```bash
# Container içinde
python3 -c "from app.core.config import get_settings; s = get_settings(); print(s.DATABASE_URL)"
```

**Doğru Format:**
```
mysql+pymysql://root:PASSWORD@mysql:3306/expireddomain
```

**Yanlış Formatlar:**
- `mysql+pymysql://root:@mysql:3306/expireddomain` (şifre eksik)
- `mysql+pymysql://root:PASSWORD@mysql` (database adı eksik)
- `mysql+pymysql://root:PASSWORD@mysql:3306` (database adı eksik)

### 2. MySQL Hostname Sorunu

**Kontrol:**
```bash
# Container içinde hostname resolution testi
python3 -c "import socket; print(socket.gethostbyname('mysql'))"
```

**Çözüm:**
- MySQL servisinin adı `mysql` olmalı
- Container ve MySQL aynı network'te olmalı
- EasyPanel'de service discovery çalışmalı

### 3. MySQL Servisi Çalışmıyor

**Kontrol:**
- EasyPanel'de MySQL servisinin durumunu kontrol edin
- MySQL servisi "Running" durumunda olmalı

### 4. Network Ayarları

**Kontrol:**
- Container ve MySQL aynı network'te mi?
- Service discovery aktif mi?

## Çözüm Adımları

### Adım 1: DATABASE_URL'i Kontrol Et

EasyPanel'de Environment Variables sekmesine gidin ve kontrol edin:

```
DATABASE_URL=mysql+pymysql://root:ŞİFRENİZ@mysql:3306/expireddomain
```

**Önemli:**
- `ŞİFRENİZ` kısmını gerçek MySQL root şifresiyle değiştirin
- Şifrede özel karakterler varsa URL encode edin:
  - `@` → `%40`
  - `#` → `%23`
  - `$` → `%24`
  - `%` → `%25`
  - `&` → `%26`

### Adım 2: MySQL Servis Adını Kontrol Et

EasyPanel'de MySQL servisinin adını kontrol edin:
- Service name: `mysql` olmalı
- Eğer farklı bir ad kullanıyorsanız, DATABASE_URL'deki `mysql` kısmını değiştirin

### Adım 3: Network Kontrolü

Container ve MySQL'in aynı network'te olduğundan emin olun.

### Adım 4: MySQL Bağlantısını Test Et

Container içinde:
```bash
# Hostname resolution
python3 -c "import socket; print(socket.gethostbyname('mysql'))"

# Port connectivity
python3 -c "import socket; sock = socket.socket(); result = sock.connect_ex(('mysql', 3306)); sock.close(); print('OK' if result == 0 else 'FAILED')"
```

### Adım 5: DATABASE_URL'i Debug Et

Container içinde check script'i çalıştırın:
```bash
bash /app/check_db_connection.sh
```

## Örnek DATABASE_URL'ler

### Şifre Yoksa:
```
mysql+pymysql://root@mysql:3306/expireddomain
```

### Şifre Varsa:
```
mysql+pymysql://root:mypassword@mysql:3306/expireddomain
```

### Özel Karakterler Varsa (URL Encode):
```
mysql+pymysql://root:myp%40ssw%23rd@mysql:3306/expireddomain
```

## Hızlı Test

Container içinde:
```bash
# 1. DATABASE_URL'i göster
python3 -c "from app.core.config import get_settings; print(get_settings().DATABASE_URL)"

# 2. MySQL hostname'i çöz
python3 -c "import socket; print(socket.gethostbyname('mysql'))"

# 3. MySQL port'una bağlan
python3 -c "import socket; s = socket.socket(); s.connect(('mysql', 3306)); print('Connected'); s.close()"
```

## EasyPanel'de Düzeltme

1. **Environment Variables** sekmesine gidin
2. `DATABASE_URL`'i kontrol edin
3. Format doğru mu? (`mysql+pymysql://root:PASSWORD@mysql:3306/expireddomain`)
4. MySQL servis adı doğru mu? (`mysql`)
5. Container'ı restart edin
6. Tekrar deneyin: `alembic upgrade head`









