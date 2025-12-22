#!/bin/bash
# Script to fix debug.py syntax error in container
# Run this inside the container

echo "Fixing debug.py syntax error..."

cat > /app/app/web/debug.py << 'PYTHON_EOF'
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
from sqlalchemy.exc import OperationalError

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
    
    # Check zone files directly from filesystem (even if DB is not available)
    filesystem_tlds_info = {}
    if zones_dir.exists():
        for tld_dir in zones_dir.iterdir():
            if tld_dir.is_dir():
                tld_name = tld_dir.name
                zone_files = sorted(tld_dir.glob("*.zone"), reverse=True)
                if zone_files:
                    filesystem_tlds_info[tld_name] = {
                        "name": tld_name,
                        "display_name": tld_name,
                        "last_import_date": None,
                        "last_drop_count": 0,
                        "zone_files": [],
                        "drop_count": 0,
                        "from_filesystem": True
                    }
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
                            parse_status = "Not Parsed"
                            try:
                                slds = extract_slds_from_zone(zone_file, tld_name)
                                sld_count = len(slds)
                                parse_status = "Parsed"
                            except FileNotFoundError:
                                parse_status = "File Not Found (during parse)"
                            except Exception as e:
                                parse_status = f"Error: {str(e)[:50]}"

                            filesystem_tlds_info[tld_name]["zone_files"].append({
                                "path": str(zone_file),
                                "name": zone_file.name,
                                "size": file_size,
                                "size_mb": round(file_size / (1024 * 1024), 2),
                                "date": file_date.isoformat() if file_date else None,
                                "sld_count": sld_count,
                                "parse_status": parse_status
                            })
                        except Exception as e:
                            filesystem_tlds_info[tld_name]["zone_files"].append({
                                "path": str(zone_file),
                                "name": zone_file.name,
                                "error": str(e)[:100]
                            })
    status["tlds"] = list(filesystem_tlds_info.values())

    # Check TLDs and zone files from database (if available)
    db_available = True
    try:
        # Attempt a simple query to check DB connectivity
        db.query(Tld).first()
        
        tlds_from_db = db.query(Tld).filter(Tld.is_active == True).order_by(Tld.name).all()
        
        for tld in tlds_from_db:
            tld_info = {
                "name": tld.name,
                "display_name": tld.display_name,
                "last_import_date": tld.last_import_date.isoformat() if tld.last_import_date else None,
                "last_drop_count": tld.last_drop_count,
                "zone_files": [],
                "drop_count": 0,
                "from_filesystem": False
            }
            
            # Merge with filesystem info if available
            if tld.name in filesystem_tlds_info:
                tld_info["zone_files"] = filesystem_tlds_info[tld.name]["zone_files"]
                del filesystem_tlds_info[tld.name]

            # Count drops for this TLD
            drop_count = db.query(func.count(DroppedDomain.id)).filter(
                DroppedDomain.tld_id == tld.id
            ).scalar()
            tld_info["drop_count"] = drop_count
            
            # Replace or add TLD info
            found = False
            for i, existing_tld in enumerate(status["tlds"]):
                if existing_tld["name"] == tld.name:
                    status["tlds"][i] = tld_info
                    found = True
                    break
            if not found:
                status["tlds"].append(tld_info)

    except OperationalError as e:
        status["db_error"] = f"Database connection error: {str(e)}"
        db_available = False
    except Exception as e:
        status["db_error"] = f"Database query error: {str(e)}"
        db_available = False
    
    # Add any remaining filesystem-only TLDs
    for tld_name, info in filesystem_tlds_info.items():
        status["tlds"].append(info)

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
    else:
        status["db_stats"] = {
            "total_drops": 0,
            "latest_drop_date": None,
            "earliest_drop_date": None,
            "drops_by_date": []
        }
        status["recent_drops"] = []
    
    return templates.TemplateResponse("debug.html", {
        "request": request,
        "status": status
    })
PYTHON_EOF

echo "✅ debug.py fixed!"
echo "Testing syntax..."
python3 -m py_compile /app/app/web/debug.py && echo "✅ Syntax OK!" || echo "❌ Syntax error!"











