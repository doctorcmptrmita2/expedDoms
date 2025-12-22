"""
Quick status check script
"""
from pathlib import Path
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.drop import DroppedDomain
from app.models.tld import Tld
from sqlalchemy import func, desc

print("=" * 60)
print("📊 UYGULAMA DURUM RAPORU")
print("=" * 60)

# Database Status
print("\n🗄️  VERİTABANI DURUMU:")
db = SessionLocal()
try:
    total_drops = db.query(func.count(DroppedDomain.id)).scalar()
    print(f"  ✅ Toplam Dropped Domain: {total_drops}")
    
    # TLD bazında
    tlds = db.query(Tld).all()
    print(f"\n  📋 TLD'ler ({len(tlds)} adet):")
    for tld in tlds:
        tld_drops = db.query(func.count(DroppedDomain.id)).filter(
            DroppedDomain.tld_id == tld.id
        ).scalar()
        print(f"    - .{tld.name}: {tld_drops} domain")
    
    # Son 5 domain
    recent = db.query(DroppedDomain).order_by(desc(DroppedDomain.created_at)).limit(5).all()
    print(f"\n  🆕 Son 5 Domain:")
    for d in recent:
        print(f"    - {d.domain} (drop: {d.drop_date})")
        
except Exception as e:
    print(f"  ❌ DB Hatası: {e}")
finally:
    db.close()

# Zone Files Status
print("\n📁 ZONE DOSYALARI:")
settings = get_settings()
zones_dir = Path(settings.DATA_DIR) / "zones"
if zones_dir.exists():
    print(f"  ✅ Zones dizini: {zones_dir}")
    total_zones = 0
    for tld_dir in sorted(zones_dir.iterdir()):
        if tld_dir.is_dir():
            zone_files = list(tld_dir.glob("*.zone"))
            total_zones += len(zone_files)
            print(f"    - .{tld_dir.name}: {len(zone_files)} dosya")
    print(f"\n  📊 Toplam zone dosyası: {total_zones}")
else:
    print(f"  ❌ Zones dizini bulunamadı: {zones_dir}")

print("\n" + "=" * 60)
print("✅ Durum kontrolü tamamlandı!")
print("=" * 60)










