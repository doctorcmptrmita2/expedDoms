# DATABASE_URL Düzeltme Rehberi

## Sorun

MySQL bağlantı hatası: `Can't connect to MySQL server on 'mysql'`

## Çözüm

Ekran görüntüsündeki bilgilere göre:

### Mevcut Bilgiler (EasyPanel'den):
- **Internal Host:** `expireddomain_expireddomain-mysql`
- **User:** `test`
- **Password:** `Tk990303005@`
- **Database:** `expireddomain`
- **Port:** `3306`

### Doğru DATABASE_URL:

```
mysql+pymysql://test:Tk990303005%40@expireddomain_expireddomain-mysql:3306/expireddomain
```

**Önemli:** Password'deki `@` karakteri `%40` olarak URL-encode edilmelidir!

## EasyPanel'de Güncelleme Adımları

1. **Projenize gidin** → Environment Variables sekmesi
2. **`DATABASE_URL` değişkenini bulun**
3. **Değeri şu şekilde güncelleyin:**

```
mysql+pymysql://test:Tk990303005%40@expireddomain_expireddomain-mysql:3306/expireddomain
```

4. **Kaydedin**
5. **Container'ı restart edin** (Restart butonuna tıklayın)

## Test Etme

Container içinde:

```bash
# Bağlantıyı test et
python3 check_db_connection.py

# Migration çalıştır
alembic upgrade head
```

## Karakter Encoding Tablosu

Şifrede özel karakterler varsa şu şekilde encode edin:

- `@` → `%40`
- `#` → `%23`
- `$` → `%24`
- `%` → `%25`
- `&` → `%26`
- `+` → `%2B`
- `=` → `%3D`
- `?` → `%3F`

## Örnek DATABASE_URL Formatları

### Basit Şifre:
```
mysql+pymysql://user:password@host:3306/database
```

### Özel Karakter İçeren Şifre:
```
mysql+pymysql://user:pass%40word@host:3306/database
```

### Root Kullanıcı ile:
```
mysql+pymysql://root:root%40password@expireddomain_expireddomain-mysql:3306/expireddomain
```










