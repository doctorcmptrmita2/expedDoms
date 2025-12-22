"""
Script to parse all downloaded zone files and insert dropped domains into database.
This script processes all zone files found in data/zones/ and compares consecutive days.

Usage:
    python -m scripts.process_all_zones
"""
import sys
from pathlib import Path
from datetime import date, timedelta
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.tld import Tld
from app.services.zone_parser import extract_slds_from_zone
from app.services.drop_detector import (
    compute_dropped_slds,
    persist_drops
)


def get_all_zone_files():
    """
    Scan data/zones/ directory and return all zone files grouped by TLD.
    
    Returns:
        dict: {tld: [sorted list of dates]}
    """
    settings = get_settings()
    zones_dir = Path(settings.DATA_DIR) / "zones"
    
    if not zones_dir.exists():
        print(f"❌ Zones directory not found: {zones_dir}")
        return {}
    
    tld_zones = defaultdict(list)
    
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
                    tld_zones[tld_name].append((file_date, zone_file))
                except (ValueError, IndexError) as e:
                    print(f"⚠️  Skipping invalid zone file: {zone_file.name} ({e})")
                    continue
            
            # Sort by date
            tld_zones[tld_name].sort(key=lambda x: x[0])
    
    return tld_zones


def ensure_tld_exists(db, tld_name: str) -> Tld:
    """
    Ensure TLD exists in database, create if not.
    
    Args:
        db: Database session
        tld_name: TLD name
        
    Returns:
        Tld instance
    """
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


def process_tld_zones(db, tld_name: str, zone_files: list):
    """
    Process zone files for a TLD and detect drops.
    
    Args:
        db: Database session
        tld_name: TLD name
        zone_files: List of (date, path) tuples, sorted by date
    """
    if len(zone_files) < 2:
        print(f"  ⚠️  Need at least 2 zone files to detect drops. Found {len(zone_files)}")
        return
    
    tld_obj = ensure_tld_exists(db, tld_name)
    
    total_drops = 0
    total_persisted = 0
    
    # Process consecutive pairs
    for i in range(len(zone_files) - 1):
        prev_date, prev_path = zone_files[i]
        curr_date, curr_path = zone_files[i + 1]
        
        print(f"\n  📅 Comparing {prev_date.isoformat()} → {curr_date.isoformat()}")
        
        try:
            # Parse both zone files
            print(f"    Parsing {prev_path.name}...")
            prev_slds = extract_slds_from_zone(prev_path, tld_name)
            print(f"      ✓ Found {len(prev_slds)} SLDs")
            
            print(f"    Parsing {curr_path.name}...")
            curr_slds = extract_slds_from_zone(curr_path, tld_name)
            print(f"      ✓ Found {len(curr_slds)} SLDs")
            
            # Compute drops (domains that were in prev but not in curr)
            dropped_slds = compute_dropped_slds(prev_slds, curr_slds)
            print(f"    🎯 Detected {len(dropped_slds)} dropped domains")
            
            if dropped_slds:
                # Persist to database
                persisted = persist_drops(db, tld_obj, prev_date, dropped_slds)
                total_persisted += persisted
                total_drops += len(dropped_slds)
                print(f"    ✓ Persisted {persisted} domains to database")
            else:
                # Update TLD metadata even if no drops
                tld_obj.last_import_date = prev_date
                tld_obj.last_drop_count = 0
                db.commit()
                print(f"    ✓ No drops (updated metadata)")
                
        except Exception as e:
            print(f"    ❌ Error processing: {e}")
            import traceback
            traceback.print_exc()
            db.rollback()
            continue
    
    print(f"\n  📊 Summary for .{tld_name}:")
    print(f"    Total drops detected: {total_drops}")
    print(f"    Total persisted: {total_persisted}")


def main():
    """Main execution function."""
    print("=" * 70)
    print("Zone File Parser & Drop Detector")
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
    print("Processing zone files and detecting drops...")
    print("-" * 70)
    
    db = SessionLocal()
    try:
        for tld_name, zone_files in sorted(tld_zones.items()):
            print(f"\n🌐 Processing TLD: .{tld_name}")
            process_tld_zones(db, tld_name, zone_files)
        
        print("\n" + "=" * 70)
        print("✅ Processing complete!")
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











