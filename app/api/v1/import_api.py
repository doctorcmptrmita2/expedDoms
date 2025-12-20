"""
API endpoint for importing all domains from zone files.
Enhanced with logging, throttling and better error handling.
"""
import time
import gc
from datetime import date
from typing import Dict, List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.database import get_db
from app.core.config import get_settings
from app.models.tld import Tld
from app.models.drop import DroppedDomain
from app.services.zone_parser import extract_slds_from_zone, build_domain_name
from app.services.import_logger import ImportLogger, logger

router = APIRouter()

# Configuration
BATCH_SIZE = 500  # Smaller batches for stability
THROTTLE_EVERY = 5000  # Pause every N records
THROTTLE_SECONDS = 1  # Pause duration
MAX_RETRIES = 3  # Max retries for DB operations


def _determine_charset_type(sld: str) -> str:
    """Determine charset type of an SLD."""
    if sld.isalpha():
        return "letters"
    elif sld.isdigit():
        return "numbers"
    else:
        return "mixed"


def _batch_insert_with_retry(db: Session, batch: list, import_log: ImportLogger) -> tuple:
    """Insert batch with retry logic. Returns (success_count, error_count)."""
    success = 0
    errors = 0
    
    for attempt in range(MAX_RETRIES):
        try:
            db.execute(DroppedDomain.__table__.insert(), batch)
            db.commit()
            return len(batch), 0
        except IntegrityError as e:
            db.rollback()
            import_log.log_warning(f"Batch insert failed (attempt {attempt + 1}), falling back to individual inserts")
            break
        except OperationalError as e:
            db.rollback()
            import_log.log_error(f"Database error (attempt {attempt + 1})", e)
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)  # Wait before retry
            else:
                return 0, len(batch)
        except Exception as e:
            db.rollback()
            import_log.log_error(f"Unexpected error in batch insert", e)
            break
    
    # Fall back to individual inserts
    for item in batch:
        try:
            db.add(DroppedDomain(**item))
            db.commit()
            success += 1
        except IntegrityError:
            db.rollback()
            errors += 1
        except Exception as e:
            db.rollback()
            errors += 1
            import_log.log_error(f"Failed to insert domain: {item.get('domain', 'unknown')}", e)
    
    return success, errors


@router.post("/import/all-zones")
async def import_all_zones(db: Session = Depends(get_db)) -> Dict:
    """
    Import all domains from all zone files found in data/zones/.
    This will parse each zone file and insert all domains into database.
    """
    settings = get_settings()
    zones_dir = Path(settings.DATA_DIR) / "zones"
    
    if not zones_dir.exists():
        raise HTTPException(status_code=404, detail=f"Zones directory not found: {zones_dir}")
    
    results = []
    total_imported = 0
    
    try:
        for tld_dir in sorted(zones_dir.iterdir()):
            if not tld_dir.is_dir():
                continue
            
            tld_name = tld_dir.name.lower()
            zone_files = sorted(tld_dir.glob("*.zone"))
            
            if not zone_files:
                continue
            
            # Get or create TLD
            tld_obj = db.query(Tld).filter(Tld.name == tld_name).first()
            if not tld_obj:
                tld_obj = Tld(name=tld_name, display_name=tld_name, is_active=True)
                db.add(tld_obj)
                db.commit()
                db.refresh(tld_obj)
            
            for zone_file in zone_files:
                import_log = ImportLogger(tld_name, "import_all")
                try:
                    date_str = zone_file.stem
                    file_date = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
                    
                    slds = extract_slds_from_zone(zone_file, tld_name)
                    import_log.start(len(slds))
                    
                    imported = 0
                    skipped = 0
                    
                    for sld in sorted(slds):
                        domain = build_domain_name(sld, tld_name)
                        
                        exists = db.query(DroppedDomain).filter(
                            DroppedDomain.domain == domain,
                            DroppedDomain.drop_date == file_date
                        ).first()
                        
                        if exists:
                            skipped += 1
                            continue
                        
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
                    
                    tld_obj.last_import_date = file_date
                    tld_obj.last_drop_count = imported
                    db.commit()
                    
                    import_log.set_stat("imported", imported)
                    import_log.set_stat("skipped", skipped)
                    import_log.complete(True)
                    
                    results.append({
                        "tld": tld_name,
                        "zone_file": zone_file.name,
                        "date": file_date.isoformat(),
                        "sld_count": len(slds),
                        "imported": imported,
                        "skipped": skipped
                    })
                    
                    total_imported += imported
                    
                except Exception as e:
                    import_log.log_error(f"Import failed for {zone_file.name}", e)
                    import_log.complete(False)
                    results.append({
                        "tld": tld_name,
                        "zone_file": zone_file.name,
                        "error": str(e)
                    })
                    db.rollback()
        
        return {
            "success": True,
            "total_imported": total_imported,
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/import/single-zone")
async def import_single_zone(
    tld: str = Query(..., description="Top-level domain name"),
    zone_date: str = Query(None, description="Date in YYYY-MM-DD format (optional, will use latest if not provided)"),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Import domains from a single zone file into database.
    Enhanced with logging, throttling and better error handling.
    """
    import_log = ImportLogger(tld.lower(), "single_zone_import")
    
    try:
        settings = get_settings()
        zones_dir = Path(settings.DATA_DIR) / "zones"
        tld_dir = zones_dir / tld.lower()
        
        import_log.log_info(f"Starting import for TLD: {tld}")
        
        # Find zone file
        if zone_date:
            file_date = date.fromisoformat(zone_date)
            date_str = file_date.strftime("%Y%m%d")
            zone_file = tld_dir / f"{date_str}.zone"
        else:
            if not tld_dir.exists():
                import_log.log_error(f"TLD directory not found: {tld_dir}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"TLD directory not found: {tld_dir}. Please download the zone file first using 'Download' or 'Download+Parse' button."
                )
            
            zone_files = sorted(tld_dir.glob("*.zone"), reverse=True)
            if not zone_files:
                import_log.log_error(f"No zone files found for TLD: {tld}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"No zone files found for TLD: {tld}. Please download the zone file first."
                )
            
            zone_file = zone_files[0]
            date_str = zone_file.stem
            try:
                file_date = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
            except:
                file_date = date.today()
        
        if not zone_file.exists():
            if tld_dir.exists():
                zone_files = sorted(tld_dir.glob("*.zone"), reverse=True)
                if zone_files:
                    zone_file = zone_files[0]
                    date_str = zone_file.stem
                    try:
                        file_date = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
                    except:
                        file_date = date.today()
                else:
                    import_log.log_error(f"No zone files found for TLD: {tld}")
                    raise HTTPException(status_code=404, detail=f"No zone files found for TLD: {tld}")
            else:
                import_log.log_error(f"Zone file not found: {zone_file}")
                raise HTTPException(status_code=404, detail=f"Zone file not found: {zone_file}")
        
        import_log.log_info(f"Found zone file: {zone_file.name}")
        
        # Get or create TLD
        tld_obj = db.query(Tld).filter(Tld.name == tld.lower()).first()
        if not tld_obj:
            tld_obj = Tld(name=tld.lower(), display_name=tld.lower(), is_active=True)
            db.add(tld_obj)
            db.commit()
            db.refresh(tld_obj)
            import_log.log_info(f"Created new TLD record: {tld.lower()}")
        
        # Parse zone file
        import_log.log_info(f"Parsing zone file...")
        parse_start = time.time()
        slds = extract_slds_from_zone(zone_file, tld.lower())
        parse_duration = time.time() - parse_start
        import_log.log_info(f"Parsed {len(slds)} SLDs in {parse_duration:.1f}s")
        import_log.start(len(slds))
        
        # Get existing domains
        import_log.log_info(f"Checking existing domains...")
        existing_domains = set()
        existing_query = db.query(DroppedDomain.domain).filter(
            DroppedDomain.tld_id == tld_obj.id,
            DroppedDomain.drop_date == file_date
        ).all()
        for (domain,) in existing_query:
            existing_domains.add(domain)
        import_log.log_info(f"Found {len(existing_domains)} existing domains for this date")
        
        # Prepare batch insert with throttling
        imported = 0
        skipped = 0
        errors = 0
        batch = []
        total_processed = 0
        
        import_log.log_info(f"Starting batch insert (batch_size={BATCH_SIZE}, throttle_every={THROTTLE_EVERY})")
        
        slds_list = list(slds)
        for i, sld in enumerate(slds_list):
            domain = build_domain_name(sld, tld.lower())
            
            if domain in existing_domains:
                skipped += 1
                continue
            
            batch.append({
                "domain": domain,
                "tld_id": tld_obj.id,
                "drop_date": file_date,
                "length": len(sld),
                "label_count": 1,
                "charset_type": _determine_charset_type(sld)
            })
            existing_domains.add(domain)
            
            # Insert batch when full
            if len(batch) >= BATCH_SIZE:
                success, err = _batch_insert_with_retry(db, batch, import_log)
                imported += success
                errors += err
                batch = []
                total_processed += BATCH_SIZE
                
                # Throttling - pause every N records
                if total_processed % THROTTLE_EVERY == 0:
                    import_log.log_info(f"Progress: {total_processed}/{len(slds_list)} ({(total_processed/len(slds_list)*100):.1f}%) - Imported: {imported}, Errors: {errors}")
                    time.sleep(THROTTLE_SECONDS)
                    gc.collect()  # Free memory
                
                import_log.update_progress(total_processed)
        
        # Insert remaining batch
        if batch:
            success, err = _batch_insert_with_retry(db, batch, import_log)
            imported += success
            errors += err
        
        # Update TLD metadata
        tld_obj.last_import_date = file_date
        tld_obj.last_drop_count = imported
        db.commit()
        
        # Log completion
        import_log.set_stat("imported", imported)
        import_log.set_stat("skipped", skipped)
        import_log.set_stat("errors", errors)
        import_log.set_stat("zone_file", zone_file.name)
        import_log.set_stat("file_date", file_date.isoformat())
        summary = import_log.complete(errors == 0 or imported > 0)
        
        return {
            "success": True,
            "tld": tld.lower(),
            "zone_file": zone_file.name,
            "date": file_date.isoformat(),
            "sld_count": len(slds),
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
            "duration_seconds": summary.get("duration_seconds", 0),
            "log_file": f"{tld.lower()}_single_zone_import_{summary['end_time'][:10].replace('-', '')}.json"
        }
        
    except HTTPException:
        import_log.complete(False)
        raise
    except Exception as e:
        import_log.log_error(f"Import failed", e)
        import_log.complete(False)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/import/logs")
async def get_import_logs(
    tld: str = Query(None, description="Filter by TLD"),
    limit: int = Query(20, description="Max logs to return")
) -> Dict:
    """Get recent import logs."""
    from app.services.import_logger import get_recent_logs
    logs = get_recent_logs(tld, limit)
    return {
        "success": True,
        "count": len(logs),
        "logs": logs
    }
