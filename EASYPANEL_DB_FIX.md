# EasyPanel Database Bağlantı Sorunu Çözümü

## 🔍 Sorun

EasyPanel'de database bağlantısı çalışmıyor. `DATABASE_URL`'deki hostname yanlış.

## ✅ Çözüm Adımları

### Adım 1: MySQL Servis Adını Bulun

1. **EasyPanel Dashboard'a gidin**
2. **Services** veya **Databases** sekmesine tıklayın
3. **MySQL servisinizi bulun**
4. **Internal Host** veya **Service Name** değerini not edin

**Örnek formatlar:**
- `expireddomain_expireddomain-mysql`
- `expireddomain-mysql`
- `mysql-1`
- `mysql`

### Adım 2: MySQL Kullanıcı Bilgilerini Kontrol Edin

MySQL servis detaylarında:
- **User/Username**: Genellikle `root` veya `test`
- **Password**: MySQL şifreniz
- **Database**: `expireddomain`

### Adım 3: DATABASE_URL'i Güncelleyin

EasyPanel'de **Environment Variables** sekmesine gidin ve `DATABASE_URL`'i güncelleyin:

#### Mevcut (Yanlış):
```
DATABASE_URL=mysql+pymysql://mysqlx:Tk990303005@mysql:3306/expireddomain
```

#### Doğru Format:
```
DATABASE_URL=mysql+pymysql://KULLANICI:ŞİFRE@SERVİS_ADI:3306/expireddomain
```

**Örnek:**
```
DATABASE_URL=mysql+pymysql://root:Tk990303005@expireddomain_expireddomain-mysql:3306/expireddomain
```

**Önemli Notlar:**
- `KULLANICI`: MySQL kullanıcı adı (genellikle `root` veya `test`)
- `ŞİFRE`: MySQL şifresi (özel karakter varsa URL-encode edin)
- `SERVİS_ADI`: EasyPanel'deki MySQL servis adı (Adım 1'de bulduğunuz)

### Adım 4: Şifrede Özel Karakter Varsa

Şifrede `@`, `#`, `$` gibi özel karakterler varsa URL-encode edin:

| Karakter | Encoded |
|----------|---------|
| `@` | `%40` |
| `#` | `%23` |
| `$` | `%24` |
| `%` | `%25` |
| `&` | `%26` |

**Örnek:**
- Şifre: `Tk990303005@` → `Tk990303005%40`
- DATABASE_URL: `mysql+pymysql://root:Tk990303005%40@expireddomain_expireddomain-mysql:3306/expireddomain`

### Adım 5: Container'ı Restart Edin

1. Environment variable'ı kaydedin
2. **Restart** butonuna tıklayın
3. Container'ın yeniden başlamasını bekleyin

### Adım 6: Bağlantıyı Test Edin

EasyPanel'de **Terminal/Exec** sekmesinden:

```bash
# Bağlantıyı test et
python3 check_db_connection.py

# Migration çalıştır (eğer yapılmadıysa)
alembic upgrade head
```

## 🔧 Hızlı Kontrol Listesi

- [ ] MySQL servis adını buldum
- [ ] MySQL kullanıcı adını kontrol ettim
- [ ] DATABASE_URL'i güncelledim
- [ ] Şifrede özel karakter varsa URL-encode ettim
- [ ] Container'ı restart ettim
- [ ] Bağlantıyı test ettim

## 📝 Örnek DATABASE_URL'ler

### Senaryo 1: Root kullanıcı, basit şifre
```
DATABASE_URL=mysql+pymysql://root:password123@expireddomain_expireddomain-mysql:3306/expireddomain
```

### Senaryo 2: Test kullanıcı, özel karakterli şifre
```
DATABASE_URL=mysql+pymysql://test:Tk990303005%40@expireddomain_expireddomain-mysql:3306/expireddomain
```

### Senaryo 3: Farklı servis adı
```
DATABASE_URL=mysql+pymysql://root:password@mysql-1:3306/expireddomain
```

## 🚨 Yaygın Hatalar

### Hata 1: "Can't connect to MySQL server on 'mysql'"
**Çözüm:** Hostname'i EasyPanel'deki gerçek servis adıyla değiştirin.

### Hata 2: "Access denied for user"
**Çözüm:** Kullanıcı adı ve şifreyi kontrol edin.

### Hata 3: "Unknown database 'expireddomain'"
**Çözüm:** Database'in oluşturulduğundan emin olun.

## 💡 İpucu

EasyPanel'de MySQL servis detaylarında **Connection String** veya **Internal URL** gösteriliyorsa, onu kullanabilirsiniz. Sadece formatı `mysql+pymysql://` ile başlayacak şekilde düzenleyin.


