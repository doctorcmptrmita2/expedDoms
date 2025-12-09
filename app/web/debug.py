"""
Debug/Test page for checking download, parse, and database status.
"""
from datetime import date, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.database import get_db
from app.core.config import get_settings
from app.models.tld import Tld
from app.models.drop import DroppedDomain
from app.services.zone_parser import extract_slds_from_zone

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/debug", response_class=HTMLResponse)
def debug_page(request: Request, db: Session = Depends(get_db)):
    """
    Debug page showing download, parse, and database status.
    """
    settings = get_settings()
    data_dir = Path(settings.DATA_DIR)
    zones_dir = data_dir / "zones"
    
    # Initialize status
    status = {
        "data_dir_exists": data_dir.exists(),
        "data_dir_path": str(data_dir),
        "zones_dir_exists": zones_dir.exists(),
        "zones_dir_path": str(zones_dir),
        "tlds": [],
        "zone_files": [],
        "db_stats": {},
        "recent_drops": []
    }
    
    # Check TLDs and zone files
    try:
        tlds = db.query(Tld).filter(Tld.is_active == True).order_by(Tld.name).all()
        
        for tld in tlds:
            tld_info = {
                "name": tld.name,
                "display_name": tld.display_name,
                "last_import_date": tld.last_import_date.isoformat() if tld.last_import_date else None,
                "last_drop_count": tld.last_drop_count,
                "zone_files": [],
                "drop_count": 0
            }
            
            # Check zone files for this TLD
            tld_zones_dir = zones_dir / tld.name.lower()
            if tld_zones_dir.exists():
                zone_files = sorted(tld_zones_dir.glob("*.zone"), reverse=True)
                for zone_file in zone_files[:10]:  # Last 10 files
                    try:
                        file_size = zone_file.stat().st_size
                        file_date_str = zone_file.stem  # YYYYMMDD
                        try:
                            file_date = date(
                                int(file_date_str[:4]),
                                int(file_date_str[4:6]),
                                int(file_date_str[6:8])
                            )
                        except:
                            file_date = None
                        
                        # Try to parse and count SLDs
                        sld_count = None
                        try:
                            slds = extract_slds_from_zone(zone_file, tld.name)
                            sld_count = len(slds)
                        except Exception as e:
                            sld_count = f"Error: {str(e)[:50]}"
                        
                        tld_info["zone_files"].append({
                            "path": str(zone_file),
                            "name": zone_file.name,
                            "size": file_size,
                            "size_mb": round(file_size / (1024 * 1024), 2),
                            "date": file_date.isoformat() if file_date else None,
                            "sld_count": sld_count
                        })
                    except Exception as e:
                        tld_info["zone_files"].append({
                            "path": str(zone_file),
                            "name": zone_file.name,
                            "error": str(e)[:100]
                        })
            
            # Count drops for this TLD
            drop_count = db.query(func.count(DroppedDomain.id)).filter(
                DroppedDomain.tld_id == tld.id
            ).scalar()
            tld_info["drop_count"] = drop_count
            
            status["tlds"].append(tld_info)
    except Exception as e:
        status["db_error"] = str(e)
    
    # Database statistics
    try:
        total_drops = db.query(func.count(DroppedDomain.id)).scalar()
        latest_drop_date = db.query(func.max(DroppedDomain.drop_date)).scalar()
        earliest_drop_date = db.query(func.min(DroppedDomain.drop_date)).scalar()
        
        # Drops by date (last 7 days)
        drops_by_date = []
        if latest_drop_date:
            for i in range(7):
                check_date = latest_drop_date - timedelta(days=i)
                count = db.query(func.count(DroppedDomain.id)).filter(
                    DroppedDomain.drop_date == check_date
                ).scalar()
                drops_by_date.append({
                    "date": check_date.isoformat(),
                    "count": count
                })
        
        # Recent drops
        recent_drops = db.query(DroppedDomain).join(Tld).order_by(
            desc(DroppedDomain.created_at)
        ).limit(20).all()
        
        status["db_stats"] = {
            "total_drops": total_drops,
            "latest_drop_date": latest_drop_date.isoformat() if latest_drop_date else None,
            "earliest_drop_date": earliest_drop_date.isoformat() if earliest_drop_date else None,
            "drops_by_date": drops_by_date
        }
        
        status["recent_drops"] = [
            {
                "id": drop.id,
                "domain": drop.domain,
                "tld": drop.tld.name,
                "drop_date": drop.drop_date.isoformat(),
                "created_at": drop.created_at.isoformat() if drop.created_at else None
            }
            for drop in recent_drops
        ]
    except Exception as e:
        status["db_stats_error"] = str(e)
    
    return templates.TemplateResponse("debug.html", {
        "request": request,
        "status": status
    })

