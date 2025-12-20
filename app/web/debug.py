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
# from app.services.zone_parser import extract_slds_from_zone  # Not used in debug page to avoid timeout

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/debug", response_class=HTMLResponse)
def debug_page(request: Request, db: Session = Depends(get_db)):
    """
    Debug page showing download, parse, and database status.
    """
    try:
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
            "recent_drops": [],
            "errors": []
        }
    except Exception as e:
        # If initialization fails, return error page
        return templates.TemplateResponse("debug.html", {
            "request": request,
            "status": {
                "data_dir_exists": False,
                "data_dir_path": "Unknown",
                "zones_dir_exists": False,
                "zones_dir_path": "Unknown",
                "tlds": [],
                "zone_files": [],
                "db_stats": {},
                "recent_drops": [],
                "errors": [f"Initialization error: {str(e)}"]
            }
        })
    
    # Check zone files directly from filesystem (even if DB is not available)
    zone_files_found = {}
    if zones_dir.exists():
        for tld_dir in zones_dir.iterdir():
            if tld_dir.is_dir():
                tld_name = tld_dir.name
                zone_files = sorted(tld_dir.glob("*.zone"), reverse=True)
                if zone_files:
                    zone_files_found[tld_name] = []
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
                            
                            # Don't parse zone files in debug page (too slow)
                            # Parse can be done via API endpoint /api/v1/import/all-zones
                            sld_count = "Not parsed (use import API)"
                            
                            zone_files_found[tld_name].append({
                                "path": str(zone_file),
                                "name": zone_file.name,
                                "size": file_size,
                                "size_mb": round(file_size / (1024 * 1024), 2),
                                "date": file_date.isoformat() if file_date else None,
                                "sld_count": sld_count
                            })
                        except Exception as e:
                            zone_files_found[tld_name].append({
                                "path": str(zone_file),
                                "name": zone_file.name,
                                "error": str(e)[:100]
                            })
    
    # Check TLDs and zone files from database (if available)
    db_available = True
    try:
        # Limit query to avoid timeout
        tlds = db.query(Tld).filter(Tld.is_active == True).order_by(Tld.name).limit(20).all()
        
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
                        
                        # Check if this zone file has been parsed by looking at DB records
                        sld_count = "Not parsed (use import API)"
                        is_parsed = False
                        
                        if file_date:
                            # Check if there are any dropped domains for this date and TLD
                            domain_count = db.query(func.count(DroppedDomain.id)).filter(
                                DroppedDomain.tld_id == tld.id,
                                DroppedDomain.drop_date == file_date
                            ).scalar()
                            
                            if domain_count and domain_count > 0:
                                sld_count = domain_count
                                is_parsed = True
                            elif tld.last_import_date and tld.last_import_date >= file_date:
                                # TLD was imported on or after this date, might have 0 drops
                                sld_count = 0
                                is_parsed = True
                        
                        tld_info["zone_files"].append({
                            "path": str(zone_file),
                            "name": zone_file.name,
                            "size": file_size,
                            "size_mb": round(file_size / (1024 * 1024), 2),
                            "date": file_date.isoformat() if file_date else None,
                            "sld_count": sld_count,
                            "is_parsed": is_parsed
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
        db_available = False
    
    # If no TLDs from DB, use filesystem zone files
    if not status["tlds"] and zone_files_found:
        for tld_name, files in zone_files_found.items():
            status["tlds"].append({
                "name": tld_name,
                "display_name": tld_name,
                "last_import_date": None,
                "last_drop_count": 0,
                "zone_files": files,
                "drop_count": 0,
                "from_filesystem": True
            })
    
    # Database statistics (only if DB is available)
    status["db_available"] = db_available
    if db_available:
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
            
            # Recent drops - get samples from each TLD
            recent_drops = []
            
            # Get all active TLDs that have drops
            tlds_with_drops = db.query(Tld).filter(
                Tld.is_active == True,
                Tld.last_import_date != None
            ).all()
            
            # Get recent drops from each TLD (limit per TLD to get variety)
            drops_per_tld = max(5, 50 // max(len(tlds_with_drops), 1))
            
            for tld_item in tlds_with_drops:
                tld_drops = db.query(DroppedDomain).filter(
                    DroppedDomain.tld_id == tld_item.id
                ).order_by(desc(DroppedDomain.created_at)).limit(drops_per_tld).all()
                recent_drops.extend(tld_drops)
            
            # Sort all by created_at and limit to 50
            recent_drops.sort(key=lambda x: x.created_at or x.drop_date, reverse=True)
            recent_drops = recent_drops[:50]
            
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
                    "created_at": drop.created_at.isoformat() if drop.created_at else None,
                    "length": drop.length,
                    "charset_type": drop.charset_type
                }
                for drop in recent_drops
            ]
        except Exception as e:
            status["db_stats_error"] = str(e)
            status["db_stats"] = {
                "total_drops": 0,
                "latest_drop_date": None,
                "earliest_drop_date": None,
                "drops_by_date": []
            }
            status["recent_drops"] = []
    else:
        # Database not available, set default values
        status["db_stats"] = {
            "total_drops": 0,
            "latest_drop_date": None,
            "earliest_drop_date": None,
            "drops_by_date": []
        }
        status["recent_drops"] = []
    
    try:
        return templates.TemplateResponse("debug.html", {
            "request": request,
            "status": status
        })
    except Exception as e:
        # If template rendering fails, return simple error response
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            f"Debug page error: {str(e)}\n\nStatus data: {status}",
            status_code=500
        )

