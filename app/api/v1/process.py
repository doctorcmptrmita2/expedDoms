"""
API endpoints for processing zone files and detecting drops.
"""
from datetime import date, timedelta
from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tld import Tld
from app.services.zone_parser import extract_slds_from_zone
from app.services.drop_detector import (
    load_sld_set_for_day,
    compute_dropped_slds,
    persist_drops
)
from app.core.config import get_settings
from pathlib import Path

router = APIRouter()


@router.post("/process/parse-zone")
async def parse_zone(
    tld: str,
    zone_date: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Parse a zone file and return statistics.
    
    Args:
        tld: Top-level domain name
        zone_date: Date in YYYY-MM-DD format (defaults to today)
    """
    try:
        if zone_date:
            target_date = date.fromisoformat(zone_date)
        else:
            target_date = date.today()
        
        settings = get_settings()
        date_str = target_date.strftime("%Y%m%d")
        zone_path = Path(settings.DATA_DIR) / "zones" / tld.lower() / f"{date_str}.zone"
        
        if not zone_path.exists():
            raise HTTPException(status_code=404, detail=f"Zone file not found: {zone_path}")
        
        # Parse zone file
        slds = extract_slds_from_zone(zone_path, tld)
        
        return {
            "success": True,
            "data": {
                "tld": tld,
                "date": target_date.isoformat(),
                "zone_path": str(zone_path),
                "sld_count": len(slds),
                "sample_slds": list(slds)[:10]  # First 10 as sample
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse failed: {str(e)}")


@router.post("/process/detect-drops")
async def detect_drops(
    tld: str,
    prev_date: Optional[str] = None,
    current_date: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Detect dropped domains by comparing two zone files.
    
    Args:
        tld: Top-level domain name
        prev_date: Previous date in YYYY-MM-DD format (defaults to yesterday)
        current_date: Current date in YYYY-MM-DD format (defaults to today)
    """
    try:
        # Parse dates
        if prev_date:
            prev = date.fromisoformat(prev_date)
        else:
            prev = date.today() - timedelta(days=1)
        
        if current_date:
            curr = date.fromisoformat(current_date)
        else:
            curr = date.today()
        
        # Get or create TLD
        tld_obj = db.query(Tld).filter(Tld.name == tld.lower()).first()
        if not tld_obj:
            tld_obj = Tld(
                name=tld.lower(),
                display_name=tld.lower(),
                is_active=True
            )
            db.add(tld_obj)
            db.commit()
            db.refresh(tld_obj)
        
        # Load SLD sets
        try:
            prev_set = load_sld_set_for_day(tld.lower(), prev)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Zone file not found for {prev.isoformat()}. Please download it first."
            )
        
        try:
            current_set = load_sld_set_for_day(tld.lower(), curr)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Zone file not found for {curr.isoformat()}. Please download it first."
            )
        
        # Compute drops
        dropped_slds = compute_dropped_slds(prev_set, current_set)
        
        # Persist to database
        persisted_count = 0
        if dropped_slds:
            persisted_count = persist_drops(db, tld_obj, prev, dropped_slds)
        
        return {
            "success": True,
            "data": {
                "tld": tld,
                "prev_date": prev.isoformat(),
                "current_date": curr.isoformat(),
                "prev_sld_count": len(prev_set),
                "current_sld_count": len(current_set),
                "dropped_count": len(dropped_slds),
                "persisted_count": persisted_count,
                "sample_drops": list(dropped_slds)[:10]  # First 10 as sample
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drop detection failed: {str(e)}")


@router.post("/process/process-downloaded-zone")
async def process_downloaded_zone(
    tld: str,
    zone_date: Optional[str] = None,
    auto_detect_drops: bool = True,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Process a downloaded zone file: parse it and optionally detect drops.
    
    Args:
        tld: Top-level domain name
        zone_date: Date in YYYY-MM-DD format (defaults to today)
        auto_detect_drops: If True, automatically detect drops by comparing with previous day
    """
    try:
        if zone_date:
            target_date = date.fromisoformat(zone_date)
        else:
            target_date = date.today()
        
        settings = get_settings()
        date_str = target_date.strftime("%Y%m%d")
        zone_path = Path(settings.DATA_DIR) / "zones" / tld.lower() / f"{date_str}.zone"
        
        if not zone_path.exists():
            raise HTTPException(status_code=404, detail=f"Zone file not found: {zone_path}")
        
        # Parse zone file
        slds = extract_slds_from_zone(zone_path, tld)
        
        result = {
            "success": True,
            "data": {
                "tld": tld,
                "date": target_date.isoformat(),
                "zone_path": str(zone_path),
                "sld_count": len(slds),
                "parsed": True
            }
        }
        
        # Auto-detect drops if requested
        if auto_detect_drops:
            try:
                prev_date = target_date - timedelta(days=1)
                prev_zone_path = Path(settings.DATA_DIR) / "zones" / tld.lower() / f"{prev_date.strftime('%Y%m%d')}.zone"
                
                if prev_zone_path.exists():
                    # Get or create TLD
                    tld_obj = db.query(Tld).filter(Tld.name == tld.lower()).first()
                    if not tld_obj:
                        tld_obj = Tld(
                            name=tld.lower(),
                            display_name=tld.lower(),
                            is_active=True
                        )
                        db.add(tld_obj)
                        db.commit()
                        db.refresh(tld_obj)
                    
                    # Load previous day's SLDs
                    prev_set = extract_slds_from_zone(prev_zone_path, tld.lower())
                    
                    # Compute drops
                    dropped_slds = compute_dropped_slds(prev_set, slds)
                    
                    # Persist drops
                    persisted_count = 0
                    if dropped_slds:
                        persisted_count = persist_drops(db, tld_obj, prev_date, dropped_slds)
                    
                    result["data"]["drops_detected"] = True
                    result["data"]["dropped_count"] = len(dropped_slds)
                    result["data"]["persisted_count"] = persisted_count
                else:
                    result["data"]["drops_detected"] = False
                    result["data"]["message"] = f"Previous day zone file not found: {prev_zone_path}"
            except Exception as e:
                result["data"]["drops_detected"] = False
                result["data"]["drop_error"] = str(e)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")











