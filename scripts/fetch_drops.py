"""
Daily script to fetch zone files and compute dropped domains.
Run this via cron once per day.

Usage:
    python -m scripts.fetch_drops
"""
import sys
from pathlib import Path
from datetime import date, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.tld import Tld
from app.services.czds_client import CZDSClient
from app.services.drop_detector import (
    load_sld_set_for_day,
    compute_dropped_slds,
    persist_drops
)


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
        print(f"Created TLD: {tld_name}")
    
    return tld


def main():
    """Main execution function."""
    settings = get_settings()
    db = SessionLocal()
    
    try:
        # Ensure all tracked TLDs exist
        for tld_name in settings.tracked_tlds_list:
            ensure_tld_exists(db, tld_name)
        
        # Get active TLDs
        active_tlds = db.query(Tld).filter(Tld.is_active == True).all()
        
        if not active_tlds:
            print("No active TLDs found. Exiting.")
            return
        
        # Determine dates
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        print(f"Processing drops for {yesterday} -> {today}")
        print("-" * 60)
        
        # Initialize CZDS client
        client = CZDSClient()
        
        # Process each TLD
        for tld in active_tlds:
            print(f"\nProcessing TLD: .{tld.name}")
            
            try:
                # Ensure zone files exist
                try:
                    yesterday_zone = client.download_zone(tld.name, yesterday)
                    print(f"  ✓ Yesterday zone: {yesterday_zone}")
                except FileNotFoundError as e:
                    print(f"  ✗ Yesterday zone not found: {e}")
                    continue
                
                try:
                    today_zone = client.download_zone(tld.name, today)
                    print(f"  ✓ Today zone: {today_zone}")
                except FileNotFoundError as e:
                    print(f"  ✗ Today zone not found (may not be ready yet): {e}")
                    continue
                
                # Load SLD sets
                prev_set = load_sld_set_for_day(tld.name, yesterday)
                current_set = load_sld_set_for_day(tld.name, today)
                
                print(f"  Yesterday SLDs: {len(prev_set)}")
                print(f"  Today SLDs: {len(current_set)}")
                
                # Compute drops
                dropped_slds = compute_dropped_slds(prev_set, current_set)
                print(f"  Dropped SLDs: {len(dropped_slds)}")
                
                if dropped_slds:
                    # Persist to database
                    persisted = persist_drops(db, tld, yesterday, dropped_slds)
                    print(f"  ✓ Persisted {persisted} dropped domains")
                else:
                    # Update TLD metadata even if no drops
                    tld.last_import_date = yesterday
                    tld.last_drop_count = 0
                    db.commit()
                    print(f"  ✓ No drops (updated metadata)")
                
            except Exception as e:
                print(f"  ✗ Error processing {tld.name}: {e}")
                db.rollback()
                continue
        
        print("\n" + "-" * 60)
        print("Processing complete!")
        
    except Exception as e:
        print(f"Fatal error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()











