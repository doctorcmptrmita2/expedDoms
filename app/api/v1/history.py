"""
API endpoints for domain history and Wayback Machine data.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date

from app.core.database import get_db
from app.models.domain_history import DomainHistory
from app.services.wayback_service import WaybackService, get_domain_wayback_info
from app.services.whois_service import WhoisService, get_domain_whois

router = APIRouter()


# ============== Schemas ==============

class WaybackInfoResponse(BaseModel):
    """Response schema for Wayback Machine info."""
    domain: str
    wayback_snapshots: int
    first_snapshot: Optional[date]
    last_snapshot: Optional[date]
    archive_url: Optional[str]
    has_archive: bool
    latest_archive_url: Optional[str]
    web_age_days: Optional[int] = None
    web_age_years: Optional[float] = None


class WhoisInfoResponse(BaseModel):
    """Response schema for Whois info."""
    domain: str
    available: bool
    registrar: Optional[str]
    creation_date: Optional[date]
    updated_date: Optional[date]
    expiry_date: Optional[date]
    name_servers: list[str]
    status: list[str]
    registrant: Optional[str]
    domain_age_days: Optional[int] = None
    domain_age_years: Optional[float] = None


class DomainHistoryResponse(BaseModel):
    """Response schema for complete domain history."""
    domain: str
    
    # Wayback data
    wayback_snapshots: int
    wayback_first_snapshot: Optional[date]
    wayback_last_snapshot: Optional[date]
    archive_url: Optional[str]
    
    # Whois data
    first_registered: Optional[date]
    last_updated: Optional[date]
    expiry_date: Optional[date]
    registrar: Optional[str]
    domain_age_days: Optional[int]
    domain_age_years: Optional[float]
    
    # Combined age (from whois or wayback)
    estimated_age_years: Optional[float]
    
    class Config:
        from_attributes = True


class SnapshotItem(BaseModel):
    """Single Wayback snapshot."""
    timestamp: str
    date: Optional[date]
    archive_url: str
    status: Optional[str] = None


class SnapshotsListResponse(BaseModel):
    """Response for snapshots list."""
    domain: str
    total: int
    snapshots: list[SnapshotItem]


# ============== Endpoints ==============

@router.get("/wayback/{domain:path}", response_model=WaybackInfoResponse)
def get_wayback_info(domain: str):
    """
    Get Wayback Machine (Internet Archive) info for a domain.
    
    Returns snapshot count, date range, and archive URLs.
    """
    # Clean domain
    domain = domain.lower().strip()
    if domain.startswith("http://") or domain.startswith("https://"):
        domain = domain.split("://")[1]
    domain = domain.rstrip("/")
    
    result = get_domain_wayback_info(domain)
    
    return WaybackInfoResponse(
        domain=result["domain"],
        wayback_snapshots=result["wayback_snapshots"],
        first_snapshot=result.get("first_snapshot"),
        last_snapshot=result.get("last_snapshot"),
        archive_url=result.get("archive_url"),
        has_archive=result.get("has_archive", False),
        latest_archive_url=result.get("latest_archive_url"),
        web_age_days=result.get("web_age_days"),
        web_age_years=result.get("web_age_years")
    )


@router.get("/wayback/{domain:path}/snapshots", response_model=SnapshotsListResponse)
def get_wayback_snapshots(
    domain: str,
    limit: int = Query(50, ge=1, le=500),
    from_date: Optional[str] = Query(None, description="Start date (YYYYMMDD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYYMMDD)")
):
    """
    Get list of Wayback Machine snapshots for a domain.
    """
    # Clean domain
    domain = domain.lower().strip()
    if domain.startswith("http://") or domain.startswith("https://"):
        domain = domain.split("://")[1]
    domain = domain.rstrip("/")
    
    service = WaybackService()
    snapshots = service.get_snapshots_list(domain, limit, from_date, to_date)
    
    items = [
        SnapshotItem(
            timestamp=s.get("timestamp", ""),
            date=s.get("date"),
            archive_url=s.get("archive_url", ""),
            status=s.get("statuscode")
        )
        for s in snapshots
    ]
    
    return SnapshotsListResponse(
        domain=domain,
        total=len(items),
        snapshots=items
    )


@router.get("/whois/{domain:path}", response_model=WhoisInfoResponse)
def get_whois_info(domain: str):
    """
    Get Whois information for a domain.
    
    Returns registration dates, registrar, and status.
    """
    # Clean domain
    domain = domain.lower().strip()
    if domain.startswith("http://") or domain.startswith("https://"):
        domain = domain.split("://")[1]
    domain = domain.rstrip("/")
    
    result = get_domain_whois(domain)
    
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    
    return WhoisInfoResponse(
        domain=result["domain"],
        available=result.get("available", False),
        registrar=result.get("registrar"),
        creation_date=result.get("creation_date"),
        updated_date=result.get("updated_date"),
        expiry_date=result.get("expiry_date"),
        name_servers=result.get("name_servers", []),
        status=result.get("status", []),
        registrant=result.get("registrant"),
        domain_age_days=result.get("domain_age_days"),
        domain_age_years=result.get("domain_age_years")
    )


@router.get("/domain/{domain:path}", response_model=DomainHistoryResponse)
def get_domain_history(
    domain: str,
    refresh: bool = Query(False, description="Force refresh from APIs"),
    db: Session = Depends(get_db)
):
    """
    Get complete domain history (Wayback + Whois combined).
    
    Results are cached in database for faster subsequent lookups.
    """
    # Clean domain
    domain = domain.lower().strip()
    if domain.startswith("http://") or domain.startswith("https://"):
        domain = domain.split("://")[1]
    domain = domain.rstrip("/")
    
    # Check cache first (unless refresh requested)
    if not refresh:
        cached = db.query(DomainHistory).filter(DomainHistory.domain == domain).first()
        if cached:
            # Calculate estimated age
            estimated_age = None
            if cached.domain_age_days:
                estimated_age = round(cached.domain_age_days / 365.25, 1)
            elif cached.wayback_first_snapshot:
                days = (date.today() - cached.wayback_first_snapshot).days
                estimated_age = round(days / 365.25, 1)
            
            return DomainHistoryResponse(
                domain=cached.domain,
                wayback_snapshots=cached.wayback_snapshots,
                wayback_first_snapshot=cached.wayback_first_snapshot,
                wayback_last_snapshot=cached.wayback_last_snapshot,
                archive_url=cached.archive_url,
                first_registered=cached.first_registered,
                last_updated=cached.last_updated,
                expiry_date=cached.expiry_date,
                registrar=cached.registrar,
                domain_age_days=cached.domain_age_days,
                domain_age_years=cached.domain_age_days / 365.25 if cached.domain_age_days else None,
                estimated_age_years=estimated_age
            )
    
    # Fetch fresh data
    wayback_data = get_domain_wayback_info(domain)
    whois_data = get_domain_whois(domain)
    
    # Calculate domain age
    domain_age_days = None
    if whois_data.get("creation_date"):
        domain_age_days = (date.today() - whois_data["creation_date"]).days
    
    # Create or update cache
    history = db.query(DomainHistory).filter(DomainHistory.domain == domain).first()
    
    if not history:
        history = DomainHistory(domain=domain)
        db.add(history)
    
    # Update fields
    history.wayback_snapshots = wayback_data.get("wayback_snapshots", 0)
    history.wayback_first_snapshot = wayback_data.get("first_snapshot")
    history.wayback_last_snapshot = wayback_data.get("last_snapshot")
    history.archive_url = wayback_data.get("archive_url")
    history.first_registered = whois_data.get("creation_date")
    history.last_updated = whois_data.get("updated_date")
    history.expiry_date = whois_data.get("expiry_date")
    history.registrar = whois_data.get("registrar")
    history.domain_age_days = domain_age_days
    history.whois_raw = whois_data.get("raw_whois")
    
    db.commit()
    
    # Calculate estimated age
    estimated_age = None
    if domain_age_days:
        estimated_age = round(domain_age_days / 365.25, 1)
    elif wayback_data.get("first_snapshot"):
        days = (date.today() - wayback_data["first_snapshot"]).days
        estimated_age = round(days / 365.25, 1)
    
    return DomainHistoryResponse(
        domain=domain,
        wayback_snapshots=wayback_data.get("wayback_snapshots", 0),
        wayback_first_snapshot=wayback_data.get("first_snapshot"),
        wayback_last_snapshot=wayback_data.get("last_snapshot"),
        archive_url=wayback_data.get("archive_url"),
        first_registered=whois_data.get("creation_date"),
        last_updated=whois_data.get("updated_date"),
        expiry_date=whois_data.get("expiry_date"),
        registrar=whois_data.get("registrar"),
        domain_age_days=domain_age_days,
        domain_age_years=round(domain_age_days / 365.25, 1) if domain_age_days else None,
        estimated_age_years=estimated_age
    )


@router.post("/batch-lookup")
def batch_domain_lookup(
    domains: list[str],
    include_whois: bool = Query(False, description="Include Whois data (slower)")
):
    """
    Lookup multiple domains at once.
    
    Note: Whois lookups are rate-limited, so batch with care.
    """
    if len(domains) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 domains per batch"
        )
    
    results = []
    
    for domain in domains:
        domain = domain.lower().strip()
        
        result = {"domain": domain}
        
        # Always get Wayback data (no rate limits)
        wayback = get_domain_wayback_info(domain)
        result["wayback_snapshots"] = wayback.get("wayback_snapshots", 0)
        result["web_age_years"] = wayback.get("web_age_years")
        result["has_archive"] = wayback.get("has_archive", False)
        
        # Optionally get Whois
        if include_whois:
            whois = get_domain_whois(domain)
            result["domain_age_years"] = whois.get("domain_age_years")
            result["registrar"] = whois.get("registrar")
            result["available"] = whois.get("available", False)
        
        results.append(result)
    
    return {
        "total": len(results),
        "results": results
    }






