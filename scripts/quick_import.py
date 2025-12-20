"""
Quick script to import all domains from zone files into database.
"""
import sys
from pathlib import Path
from datetime import date
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.tld import Tld
from app.models.drop import DroppedDomain
from app.services.zone_parser import extract_slds_from_zone, build_domain_name


def _determine_charset_type(sld: str) -> str:
    if sld.isalpha():
        return "letters"
    elif sld.isdigit():
        return "numbers"
    else:
        return "mixed"


def main():
    settings = get_settings()
    zones_dir = Path(settings.DATA_DIR) / "zones"
    
    if not zones_dir.exists():
        print(f"❌ Zones directory not found: {zones_dir}")
        return
    
    db = SessionLocal()
    total_imported = 0
    
    try:
        # Find all zone files
        for tld_dir in zones_dir.iterdir():
            if not tld_dir.is_dir():
                continue
                
            tld_name = tld_dir.name.lower()
            zone_files = sorted(tld_dir.glob("*.zone"))
            
            if not zone_files:
                continue
            
            print(f"\n🌐 Processing .{tld_name}...")
            
            # Get or create TLD
            tld_obj = db.query(Tld).filter(Tld.name == tld_name).first()
            if not tld_obj:
                tld_obj = Tld(name=tld_name, display_name=tld_name, is_active=True)
                db.add(tld_obj)
                db.commit()
                db.refresh(tld_obj)
                print(f"  ✓ Created TLD")
            
            # Process each zone file
            for zone_file in zone_files:
                try:
                    # Extract date
                    date_str = zone_file.stem
                    file_date = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
                    
                    print(f"  📄 {zone_file.name} ({file_date.isoformat()})...")
                    
                    # Parse zone file
                    slds = extract_slds_from_zone(zone_file, tld_name)
                    print(f"    ✓ Found {len(slds)} SLDs")
                    
                    # Import domains
                    imported = 0
                    skipped = 0
                    
                    for i, sld in enumerate(sorted(slds)):
                        if (i + 1) % 5000 == 0:
                            print(f"    Processing {i + 1}/{len(slds)}...")
                        
                        domain = build_domain_name(sld, tld_name)
                        
                        # Check if exists
                        exists = db.query(DroppedDomain).filter(
                            DroppedDomain.domain == domain,
                            DroppedDomain.drop_date == file_date
                        ).first()
                        
                        if exists:
                            skipped += 1
                            continue
                        
                        # Create record
                        dropped_domain = DroppedDomain(
                            domain=domain,
                            tld_id=tld_obj.id,
                            drop_date=file_date,
                            length=len(sld),
                            label_count=1,
                            charset_type=_determine_charset_type(sld)
                        )
                        
                        try:
                            db.add(dropped_domain)
                            db.commit()
                            imported += 1
                        except IntegrityError:
                            db.rollback()
                            skipped += 1
                    
                    # Update TLD metadata
                    tld_obj.last_import_date = file_date
                    tld_obj.last_drop_count = imported
                    db.commit()
                    
                    print(f"    ✅ Imported: {imported}, Skipped: {skipped}")
                    total_imported += imported
                    
                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    db.rollback()
                    import traceback
                    traceback.print_exc()
        
        print(f"\n✅ Total imported: {total_imported}")
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()









