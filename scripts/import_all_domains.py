"""
Script to parse all zone files and import ALL domains (not just drops) into database.
This is useful when you have zone files but want to import all current domains.

Usage:
    python -m scripts.import_all_domains
"""
import sys
from pathlib import Path
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.tld import Tld
from app.models.drop import DroppedDomain
from app.services.zone_parser import extract_slds_from_zone, build_domain_name


def _determine_charset_type(sld: str) -> str:
    """Determine charset type of an SLD."""
    if sld.isalpha():
        return "letters"
    elif sld.isdigit():
        return "numbers"
    else:
        return "mixed"


def import_domains_from_zone(db: Session, tld_obj: Tld, zone_path: Path, zone_date: date):
    """
    Import all domains from a zone file into database.
    
    Args:
        db: Database session
        tld_obj: TLD model instance
        zone_path: Path to zone file
        zone_date: Date of the zone file
    """
    print(f"  📄 Parsing {zone_path.name}...")
    
    try:
        # Parse zone file
        slds = extract_slds_from_zone(zone_path, tld_obj.name)
        print(f"    ✓ Found {len(slds)} SLDs")
        
        imported_count = 0
        skipped_count = 0
        
        print(f"  💾 Importing domains...")
        for i, sld in enumerate(sorted(slds)):
            if (i + 1) % 1000 == 0:
                print(f"    Processing {i + 1}/{len(slds)}...")
            
            domain = build_domain_name(sld, tld_obj.name)
            
            # Check if already exists
            existing = db.query(DroppedDomain).filter(
                DroppedDomain.domain == domain,
                DroppedDomain.drop_date == zone_date
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            # Create domain record
            dropped_domain = DroppedDomain(
                domain=domain,
                tld_id=tld_obj.id,
                drop_date=zone_date,
                length=len(sld),
                label_count=1,
                charset_type=_determine_charset_type(sld)
            )
            
            try:
                db.add(dropped_domain)
                db.commit()
                imported_count += 1
            except IntegrityError:
                db.rollback()
                skipped_count += 1
                continue
        
        # Update TLD metadata
        tld_obj.last_import_date = zone_date
        tld_obj.last_drop_count = imported_count
        db.commit()
        
        print(f"    ✅ Imported: {imported_count}, Skipped: {skipped_count}")
        return imported_count
        
    except Exception as e:
        print(f"    ❌ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        return 0


def get_all_zone_files():
    """Scan data/zones/ directory and return all zone files."""
    settings = get_settings()
    zones_dir = Path(settings.DATA_DIR) / "zones"
    
    if not zones_dir.exists():
        print(f"❌ Zones directory not found: {zones_dir}")
        return {}
    
    tld_zones = {}
    
    for tld_dir in zones_dir.iterdir():
        if tld_dir.is_dir():
            tld_name = tld_dir.name.lower()
            zone_files = sorted(tld_dir.glob("*.zone"))
            
            for zone_file in zone_files:
                # Extract date from filename (YYYYMMDD.zone)
                try:
                    date_str = zone_file.stem
                    file_date = date(
                        int(date_str[:4]),
                        int(date_str[4:6]),
                        int(date_str[6:8])
                    )
                    
                    if tld_name not in tld_zones:
                        tld_zones[tld_name] = []
                    tld_zones[tld_name].append((file_date, zone_file))
                except (ValueError, IndexError) as e:
                    print(f"⚠️  Skipping invalid zone file: {zone_file.name} ({e})")
                    continue
    
    return tld_zones


def ensure_tld_exists(db: Session, tld_name: str) -> Tld:
    """Ensure TLD exists in database, create if not."""
    tld = db.query(Tld).filter(Tld.name == tld_name.lower()).first()
    
    if not tld:
        tld = Tld(
            name=tld_name.lower(),
            display_name=tld_name.lower(),
            is_active=True
        )
        db.add(tld)
        db.commit()
        db.refresh(tld)
        print(f"  ✓ Created TLD: {tld_name}")
    
    return tld


def main():
    """Main execution function."""
    print("=" * 70)
    print("Zone File Domain Importer")
    print("=" * 70)
    print()
    
    # Get all zone files
    print("🔍 Scanning for zone files...")
    tld_zones = get_all_zone_files()
    
    if not tld_zones:
        print("❌ No zone files found!")
        return
    
    print(f"✓ Found zone files for {len(tld_zones)} TLD(s):")
    for tld_name, files in tld_zones.items():
        print(f"  .{tld_name}: {len(files)} file(s)")
    
    print("\n" + "-" * 70)
    print("Importing domains from zone files...")
    print("-" * 70)
    
    db = SessionLocal()
    try:
        total_imported = 0
        
        for tld_name, zone_files in sorted(tld_zones.items()):
            print(f"\n🌐 Processing TLD: .{tld_name}")
            tld_obj = ensure_tld_exists(db, tld_name)
            
            for zone_date, zone_path in zone_files:
                imported = import_domains_from_zone(db, tld_obj, zone_path, zone_date)
                total_imported += imported
        
        print("\n" + "=" * 70)
        print(f"✅ Import complete! Total domains imported: {total_imported}")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()











