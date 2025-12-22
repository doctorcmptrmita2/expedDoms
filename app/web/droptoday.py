"""
Web route for today's dropping domains with filters.
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, case

from app.core.database import get_db
from app.models.tld import Tld
from app.models.drop import DroppedDomain
from app.schemas.drop import DropRead

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/droptoday", response_class=HTMLResponse)
def drop_today(
    request: Request,
    tld: Optional[str] = Query(None, description="Filter by TLD"),
    search: Optional[str] = Query(None, description="Search in domain names"),
    min_length: Optional[int] = Query(None, ge=1, description="Minimum SLD length"),
    max_length: Optional[int] = Query(None, ge=1, description="Maximum SLD length"),
    charset_type: Optional[str] = Query(None, description="Filter by charset type (letters/numbers/mixed)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, description="Items per page (30, 50, 100, 200, or 500)"),
    db: Session = Depends(get_db)
):
    """
    List domains dropping today with filters and pagination.
    """
    # Validate page_size
    valid_page_sizes = [30, 50, 100, 200, 500]
    if page_size not in valid_page_sizes:
        page_size = 100
    
    # Get today's date
    today = date.today()
    
    # Initialize default values
    active_tlds = []
    dropped_domains = []
    total_dropped = 0
    total_pages = 1
    page_range = []
    show_date = today  # Date to show (today or latest available)
    is_today = True  # Whether we're showing today's date or fallback
    
    try:
        # Get all active TLDs for filter
        active_tlds = db.query(Tld).filter(Tld.is_active == True).order_by(Tld.name).all()
        
        # Check if there are domains for today
        today_count = db.query(DroppedDomain).filter(DroppedDomain.drop_date == today).count()
        
        # If no domains for today, use the latest available date
        if today_count == 0:
            latest_date = db.query(func.max(DroppedDomain.drop_date)).scalar()
            if latest_date:
                show_date = latest_date
                is_today = False
        
        # Build query for the selected date
        query = db.query(DroppedDomain).join(Tld).filter(
            DroppedDomain.drop_date == show_date
        )
        
        # Apply TLD filter
        if tld:
            query = query.filter(Tld.name == tld.lower())
        
        # Apply search filter
        if search:
            search_term = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    DroppedDomain.domain.ilike(search_term)
                )
            )
        
        # Apply length filters
        if min_length is not None:
            query = query.filter(DroppedDomain.length >= min_length)
        if max_length is not None:
            query = query.filter(DroppedDomain.length <= max_length)
        
        # Apply charset filter
        if charset_type:
            query = query.filter(DroppedDomain.charset_type == charset_type.lower())
        
        # Get total count before pagination
        total_dropped = query.count()
        total_pages = max(1, (total_dropped + page_size - 1) // page_size)
        
        # Ensure page is within bounds
        if page > total_pages:
            page = total_pages
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Order and paginate
        # Order by quality_score (highest first), then by domain name
        dropped_domains_list = query.order_by(
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
        logging.error(f"Database error in drop_today route: {e}", exc_info=True)
        # On error, ensure page_range is set
        if not page_range:
            page_range = [1]
        # Ensure show_date and is_today are set even on error
        if 'show_date' not in locals():
            show_date = today
            is_today = True
    
    return templates.TemplateResponse("droptoday.html", {
        "request": request,
        "today": today,
        "show_date": show_date,
        "is_today": is_today,
        "active_tlds": active_tlds,
        "selected_tld": tld,
        "search": search,
        "min_length": min_length,
        "max_length": max_length,
        "charset_type": charset_type,
        "dropped_domains": dropped_domains,
        "total_dropped": total_dropped,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "page_range": page_range,
        "valid_page_sizes": valid_page_sizes
    })

