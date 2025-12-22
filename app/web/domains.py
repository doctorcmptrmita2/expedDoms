"""
Web route for comprehensive domain listing page with pagination.
"""
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, case

from app.core.database import get_db
from app.models.tld import Tld
from app.models.drop import DroppedDomain
from app.schemas.drop import DropRead

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/domains", response_class=HTMLResponse)
def domains_list(
    request: Request,
    date_filter: Optional[date] = Query(None, alias="date"),
    tld: Optional[str] = Query(None),
    future_days: int = Query(7, ge=1, le=30, description="Days to look ahead for future drops"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, description="Items per page (30, 50, 100, 200, or 500)"),
    db: Session = Depends(get_db)
):
    """
    Comprehensive domain listing page with pagination.
    """
    # Validate page_size
    valid_page_sizes = [30, 50, 100, 200, 500]
    if page_size not in valid_page_sizes:
        page_size = 100
    
    # Initialize default values
    active_tlds = []
    selected_date = None
    selected_tld = tld
    dropped_domains = []
    future_domains = []
    total_dropped = 0
    total_future = 0
    total_pages = 1
    page_range = []
    
    try:
        # Get all active TLDs for filter
        active_tlds = db.query(Tld).filter(Tld.is_active == True).order_by(Tld.name).all()
        
        # Determine date to show - default: show all domains
        if date_filter:
            selected_date = date_filter
        
        # Get dropped domains - show all if no date filter
        query_dropped = db.query(DroppedDomain).join(Tld)
        
        # Apply date filter only if date is specified
        if selected_date:
            query_dropped = query_dropped.filter(DroppedDomain.drop_date == selected_date)
        
        # Apply TLD filter
        if tld:
            query_dropped = query_dropped.filter(Tld.name == tld.lower())
        
        # Get total count before pagination
        total_dropped = query_dropped.count()
        total_pages = max(1, (total_dropped + page_size - 1) // page_size)
        
        # Ensure page is within bounds
        if page > total_pages:
            page = total_pages
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Order and paginate
        # Order by drop_date (newest first), then by quality_score (highest first), then by domain name
        # MySQL doesn't support NULLS LAST, so we use CASE to put NULLs at the end
        dropped_domains_list = query_dropped.order_by(
            desc(DroppedDomain.drop_date),
            case((DroppedDomain.quality_score.is_(None), 1), else_=0),  # NULL values last
            desc(DroppedDomain.quality_score),
            DroppedDomain.domain
        ).offset(offset).limit(page_size).all()
        
        dropped_domains = [
            DropRead(
                id=drop.id,
                domain=drop.domain,
                tld=drop.tld.name,
                drop_date=drop.drop_date,
                length=drop.length,
                charset_type=drop.charset_type
            )
            for drop in dropped_domains_list
        ]
        
        # Get future dropping domains (only when date is selected)
        if selected_date:
            future_date = selected_date + timedelta(days=future_days)
            query_future = db.query(DroppedDomain).join(Tld)
            query_future = query_future.filter(
                and_(
                    DroppedDomain.drop_date > selected_date,
                    DroppedDomain.drop_date <= future_date
                )
            )
            
            if tld:
                query_future = query_future.filter(Tld.name == tld.lower())
            
            future_domains_list = query_future.order_by(
                DroppedDomain.drop_date,
                case((DroppedDomain.quality_score.is_(None), 1), else_=0),  # NULL values last
                desc(DroppedDomain.quality_score),
                DroppedDomain.domain
            ).limit(100).all()
            
            future_domains = [
                DropRead(
                    id=drop.id,
                    domain=drop.domain,
                    tld=drop.tld.name,
                    drop_date=drop.drop_date,
                    length=drop.length,
                    charset_type=drop.charset_type
                )
                for drop in future_domains_list
            ]
            
            total_future = query_future.count()
        else:
            future_domains = []
            total_future = 0
        
        # Calculate page range for pagination
        if total_pages <= 7:
            page_range = list(range(1, total_pages + 1))
        else:
            if page <= 4:
                page_range = list(range(1, 6)) + ['...', total_pages]
            elif page >= total_pages - 3:
                page_range = [1, '...'] + list(range(total_pages - 4, total_pages + 1))
            else:
                page_range = [1, '...'] + list(range(page - 1, page + 2)) + ['...', total_pages]
        
    except Exception as e:
        import logging
        logging.error(f"Database error in domains_list route: {e}")
        # On error, ensure page_range is set
        if not page_range:
            page_range = [1]
    
    return templates.TemplateResponse("domains_list.html", {
        "request": request,
        "active_tlds": active_tlds,
        "selected_date": selected_date,
        "selected_tld": selected_tld,
        "future_days": future_days,
        "dropped_domains": dropped_domains,
        "future_domains": future_domains,
        "total_dropped": total_dropped,
        "total_future": total_future,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "page_range": page_range,
        "valid_page_sizes": valid_page_sizes
    })


@router.get("/domain/{domain:path}", response_class=HTMLResponse)
def domain_detail(
    request: Request,
    domain: str,
    db: Session = Depends(get_db)
):
    """
    Domain detail page showing quality score, Wayback Machine data, and Whois info.
    """
    # Clean domain
    domain = domain.lower().strip()
    
    return templates.TemplateResponse("domain_detail.html", {
        "request": request,
        "domain": domain
    })
