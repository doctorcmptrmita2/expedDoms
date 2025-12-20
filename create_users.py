"""
Create demo and admin users
"""
from app.core.database import SessionLocal
from app.services.auth_service import create_user, hash_password, get_user_by_email
from app.models.user import User

db = SessionLocal()

# Demo User
demo_email = "demo@expireddomain.dev"
demo_user = get_user_by_email(db, demo_email)

if not demo_user:
    demo_user = User(
        email=demo_email,
        username="demo",
        password_hash=hash_password("demo123"),
        full_name="Demo User",
        is_active=True,
        is_verified=True,
        is_premium=False,
        is_admin=False
    )
    db.add(demo_user)
    db.commit()
    print(f"[OK] Demo user created: {demo_email} / demo123")
else:
    print(f"[INFO] Demo user already exists: {demo_email}")

# Admin User
admin_email = "admin@expireddomain.dev"
admin_user = get_user_by_email(db, admin_email)

if not admin_user:
    admin_user = User(
        email=admin_email,
        username="admin",
        password_hash=hash_password("admin123"),
        full_name="Administrator",
        is_active=True,
        is_verified=True,
        is_premium=True,
        is_admin=True
    )
    db.add(admin_user)
    db.commit()
    print(f"[OK] Admin user created: {admin_email} / admin123")
else:
    print(f"[INFO] Admin user already exists: {admin_email}")

# Premium Demo User
premium_email = "premium@expireddomain.dev"
premium_user = get_user_by_email(db, premium_email)

if not premium_user:
    premium_user = User(
        email=premium_email,
        username="premium",
        password_hash=hash_password("premium123"),
        full_name="Premium User",
        is_active=True,
        is_verified=True,
        is_premium=True,
        is_admin=False
    )
    db.add(premium_user)
    db.commit()
    print(f"[OK] Premium user created: {premium_email} / premium123")
else:
    print(f"[INFO] Premium user already exists: {premium_email}")

db.close()

print("\nKullanici Bilgileri:")
print("=" * 50)
print("Demo Hesap:")
print("  Email: demo@expireddomain.dev")
print("  Şifre: demo123")
print("  Tip: Ücretsiz Kullanıcı")
print()
print("Premium Hesap:")
print("  Email: premium@expireddomain.dev")
print("  Şifre: premium123")
print("  Tip: Premium Kullanıcı")
print()
print("Admin Hesap:")
print("  Email: admin@expireddomain.dev")
print("  Şifre: admin123")
print("  Tip: Administrator + Premium")
print("=" * 50)

