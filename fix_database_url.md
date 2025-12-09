# DATABASE_URL Düzeltme Rehberi

## Sorun

Hata: `Can't connect to MySQL server on '@mysql'`

Bu hata, DATABASE_URL'in yanlış parse edildiğini gösteriyor.

## Container İçinde Kontrol

EasyPanel Terminal/Exec'ten şu komutları çalıştırın:

```bash
# 1. DATABASE_URL'i göster
python3 -c "import os; print('DATABASE_URL:', os.environ.get('DATABASE_URL', 'NOT SET'))"

# 2. Settings'ten DATABASE_URL'i göster
python3 -c "from app.core.config import get_settings; s = get_settings(); print('DATABASE_URL:', s.DATABASE_URL)"

# 3. URL'i parse et
python3 -c "
from urllib.parse import urlparse
import os
db_url = os.environ.get('DATABASE_URL', '')
if db_url:
    parsed = urlparse(db_url)
    print(f'Scheme: {parsed.scheme}')
    print(f'Username: {parsed.username}')
    print(f'Password: {\"*\" * len(parsed.password) if parsed.password else \"(empty)\"}')
    print(f'Hostname: {parsed.hostname}')
    print(f'Port: {parsed.port}')
    print(f'Database: {parsed.path.lstrip(\"/\")}')
"
```

## EasyPanel'de Düzeltme

### Adım 1: Environment Variables Kontrolü

1. EasyPanel'de projenize gidin
2. **Environment Variables** sekmesine gidin
3. `DATABASE_URL` değerini kontrol edin

### Adım 2: Doğru Format

**Doğru Format:**
```
mysql+pymysql://root:PASSWORD@mysql:3306/expireddomain
```

**Örnekler:**

Şifre yoksa:
```
mysql+pymysql://root@mysql:3306/expireddomain
```

Şifre varsa:
```
mysql+pymysql://root:mypassword@mysql:3306/expireddomain
```

Şifrede özel karakterler varsa (URL encode):
- `@` → `%40`
- `#` → `%23`
- `$` → `%24`
- `%` → `%25`
- `&` → `%26`

Örnek: Şifre `pass@123` ise → `pass%40123`

### Adım 3: MySQL Servis Adını Kontrol Et

1. EasyPanel'de **Services** sekmesine gidin
2. MySQL servisinin adını kontrol edin
3. Eğer ad `mysql` değilse, DATABASE_URL'deki `mysql` kısmını değiştirin

### Adım 4: Container'ı Restart Et

1. Environment variable'ı düzelttikten sonra
2. Container'ı restart edin
3. Tekrar test edin

## Hızlı Test

Container içinde:

```bash
# MySQL hostname resolution
python3 -c "import socket; print(socket.gethostbyname('mysql'))"

# MySQL port connectivity
python3 -c "import socket; s = socket.socket(); result = s.connect_ex(('mysql', 3306)); s.close(); print('OK' if result == 0 else 'FAILED')"

# Database connection test
python3 -c "from app.core.database import engine; conn = engine.connect(); print('Connected!'); conn.close()"
```

## Yaygın Hatalar

### Hata 1: Şifre eksik
```
mysql+pymysql://root:@mysql:3306/expireddomain
```
**Çözüm:** Şifreyi ekleyin veya `:` işaretini kaldırın

### Hata 2: Hostname yanlış
```
mysql+pymysql://root:password@wronghost:3306/expireddomain
```
**Çözüm:** MySQL servis adını kontrol edin

### Hata 3: Port eksik
```
mysql+pymysql://root:password@mysql/expireddomain
```
**Çözüm:** Port ekleyin: `:3306`

### Hata 4: Database adı eksik
```
mysql+pymysql://root:password@mysql:3306
```
**Çözüm:** Database adını ekleyin: `/expireddomain`

