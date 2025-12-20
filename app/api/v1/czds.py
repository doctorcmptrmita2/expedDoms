"""
API endpoints for CZDS management.
"""
from typing import Optional, Dict, List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.czds_client import CZDSClient


router = APIRouter()


class AuthRequest(BaseModel):
    """Authentication request model."""
    username: str
    password: str


class ZonesRequest(BaseModel):
    """Zones list request model."""
    username: str
    password: str


class DownloadRequest(BaseModel):
    """Zone download request model."""
    zone_url: str
    tld: Optional[str] = None
    target_date: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


@router.post("/czds/authenticate")
async def authenticate_czds(request: AuthRequest) -> Dict:
    """
    Authenticate with CZDS API and obtain access token.
    Returns credentials that can be used for subsequent requests.
    """
    client = CZDSClient(username=request.username, password=request.password)
    
    try:
        result = client.authenticate()
        # Return credentials info (without password) for client-side storage
        return {
            "success": True,
            "message": "Authentication successful",
            "data": {
                "accessToken": result.get("accessToken"),
                "expiresAt": result.get("expiresAt"),
                "expiresIn": result.get("expiresIn"),
                "username": request.username  # Store username for future requests
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.get("/czds/token-info")
async def get_token_info() -> Dict:
    """
    Get current access token information.
    """
    client = CZDSClient()
    info = client.get_token_info()
    
    if info is None:
        return {
            "success": False,
            "message": "No token available. Please authenticate first.",
            "data": None
        }
    
    return {
        "success": True,
        "data": info
    }


@router.post("/czds/zones")
async def list_zones(request: ZonesRequest) -> Dict:
    """
    List all authorized zone files.
    Requires authentication credentials.
    """
    client = CZDSClient(username=request.username, password=request.password)
    
    try:
        zones = client.list_zones()
        return {
            "success": True,
            "data": zones,
            "count": len(zones)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list zones: {str(e)}")


@router.get("/czds/zone-info")
async def get_zone_info(zone_url: str, username: Optional[str] = None, password: Optional[str] = None) -> Dict:
    """
    Get zone file information without downloading.
    Requires authentication credentials.
    """
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    client = CZDSClient(username=username, password=password)
    
    try:
        info = client.get_zone_info(zone_url)
        return {
            "success": True,
            "data": info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get zone info: {str(e)}")


@router.post("/czds/download")
async def download_zone(
    request: DownloadRequest,
    auto_process: bool = Query(False, description="Automatically parse and detect drops after download")
) -> Dict:
    """
    Download a zone file.
    Requires authentication credentials.
    
    Args:
        auto_process: If True, automatically parse and detect drops after download
    """
    if not request.username or not request.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    client = CZDSClient(username=request.username, password=request.password)
    
    try:
        from datetime import datetime as dt
        
        target_date = None
        if request.target_date:
            target_date = dt.strptime(request.target_date, "%Y-%m-%d").date()
        
        path = client.download_zone(
            request.zone_url,
            tld=request.tld,
            target_date=target_date
        )
        
        result = {
            "success": True,
            "message": "Zone file downloaded successfully",
            "data": {
                "path": str(path),
                "size": path.stat().st_size if path.exists() else 0,
                "tld": request.tld,
                "date": target_date.isoformat() if target_date else None
            }
        }
        
        # Auto-process if requested
        if auto_process and request.tld and path.exists():
            try:
                from app.core.database import SessionLocal
                from app.models.tld import Tld
                from app.services.zone_parser import extract_slds_from_zone
                from app.services.drop_detector import compute_dropped_slds, persist_drops
                from datetime import timedelta
                import re
                
                db = SessionLocal()
                try:
                    # If target_date not provided, extract from filename
                    actual_date = target_date
                    if not actual_date:
                        # Try to extract date from filename (e.g., 20251210.zone)
                        match = re.search(r'(\d{8})\.zone$', path.name)
                        if match:
                            date_str = match.group(1)
                            actual_date = dt.strptime(date_str, "%Y%m%d").date()
                        else:
                            # Use today's date as fallback
                            actual_date = dt.now().date()
                    
                    # ALWAYS get or create TLD first
                    tld_obj = db.query(Tld).filter(Tld.name == request.tld.lower()).first()
                    if not tld_obj:
                        tld_obj = Tld(
                            name=request.tld.lower(),
                            display_name=request.tld.lower(),
                            is_active=True
                        )
                        db.add(tld_obj)
                        db.commit()
                        db.refresh(tld_obj)
                    
                    # Parse zone file
                    slds = extract_slds_from_zone(path, request.tld)
                    
                    process_info = {
                        "sld_count": len(slds),
                        "parsed": True,
                        "tld_created": True
                    }
                    
                    # Try to detect drops
                    prev_date = actual_date - timedelta(days=1)
                    from app.core.config import get_settings
                    settings = get_settings()
                    prev_zone_path = Path(settings.DATA_DIR) / "zones" / request.tld.lower() / f"{prev_date.strftime('%Y%m%d')}.zone"
                    
                    if prev_zone_path.exists():
                        # Load previous day's SLDs
                        prev_set = extract_slds_from_zone(prev_zone_path, request.tld.lower())
                        
                        # Compute drops
                        dropped_slds = compute_dropped_slds(prev_set, slds)
                        
                        # Persist drops
                        persisted_count = 0
                        if dropped_slds:
                            persisted_count = persist_drops(db, tld_obj, prev_date, dropped_slds)
                        
                        process_info["drops_detected"] = True
                        process_info["dropped_count"] = len(dropped_slds)
                        process_info["persisted_count"] = persisted_count
                        
                        # Update TLD metadata
                        tld_obj.last_import_date = actual_date
                        tld_obj.last_drop_count = persisted_count
                        db.commit()
                    else:
                        process_info["drops_detected"] = False
                        process_info["message"] = f"Previous day zone file not found: {prev_zone_path.name}"
                        
                        # Still update TLD metadata
                        tld_obj.last_import_date = actual_date
                        db.commit()
                    
                    result["data"]["processed"] = True
                    result["data"]["process_result"] = process_info
                finally:
                    db.close()
            except Exception as e:
                result["data"]["processed"] = False
                result["data"]["process_error"] = str(e)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

