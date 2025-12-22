"""
Web route for deleted domains page - shows last 7 days grouped by date.
"""
from datetime import date, timedelta
from typing import Dict, List
from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case

from app.core.database import get_db
from app.models.tld import Tld
from app.models.drop import DroppedDomain
from app.schemas.drop import DropRead

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/deleted-domains", response_class=HTMLResponse)
def deleted_domains_list(
    request: Request,
    days: int = Query(7, ge=1, le=30, description="Number of days to show"),
    tld: str = Query(None, description="Filter by TLD"),
    db: Session = Depends(get_db)
):
    """
    Deleted domains page showing last N days grouped by date.
    """
    # Initialize default values
    active_tlds = []
    domains_by_date: Dict[date, List[Dict]] = {}
    total_domains = 0
    date_stats: Dict[date, int] = {}
    today = date.today()
    start_date = today
    end_date = today
    
    try:
        # Get all active TLDs for filter
        active_tlds = db.query(Tld).filter(Tld.is_active == True).order_by(Tld.name).all()
        
        # Calculate date range (last N days)
        today = date.today()
        start_date = today - timedelta(days=days)
        end_date = today
        
        # Check if there are domains in the requested range
        count_in_range = db.query(DroppedDomain).filter(
            DroppedDomain.drop_date >= start_date,
            DroppedDomain.drop_date <= today
        ).count()
        
        # If no domains in range, use all available domains (or last 30 days from latest date)
        if count_in_range == 0:
            # Get the latest available date
            latest_date = db.query(func.max(DroppedDomain.drop_date)).scalar()
            if latest_date:
                # Show last 30 days from latest date, or all if less than 30 days
                actual_start = latest_date - timedelta(days=min(30, days))
                start_date = actual_start
                end_date = latest_date
        
        # Build query for dropped domains in the date range
        query = db.query(DroppedDomain).join(Tld).filter(
            DroppedDomain.drop_date >= start_date,
            DroppedDomain.drop_date <= end_date
        )
        
        # Apply TLD filter if specified
        if tld:
            query = query.filter(Tld.name == tld.lower())
        
        # Get all domains ordered by date (newest first), then quality score, then domain name
        # Limit to prevent timeout on large datasets (max 5000 domains per request)
        all_domains = query.order_by(
            desc(DroppedDomain.drop_date),
            case((DroppedDomain.quality_score.is_(None), 1), else_=0),
            desc(DroppedDomain.quality_score),
            DroppedDomain.domain
        ).limit(5000).all()
        
        # Group domains by date
        for domain in all_domains:
            drop_date = domain.drop_date
            if drop_date not in domains_by_date:
                domains_by_date[drop_date] = []
                date_stats[drop_date] = 0
            
            domains_by_date[drop_date].append({
                "id": domain.id,
                "domain": domain.domain,
                "tld": domain.tld.name if domain.tld else "unknown",
                "drop_date": domain.drop_date,
                "length": domain.length,
                "charset_type": domain.charset_type,
                "quality_score": domain.quality_score,
                "label_count": domain.label_count if hasattr(domain, 'label_count') else None
            })
            date_stats[drop_date] += 1
        
        # Calculate total
        total_domains = len(all_domains)
        
        # Sort dates in descending order (newest first)
        sorted_dates = sorted(domains_by_date.keys(), reverse=True)
        
    except Exception as e:
        import logging
        logging.error(f"Database error in deleted_domains_list route: {e}", exc_info=True)
        sorted_dates = []
        domains_by_date = {}
        date_stats = {}
        total_domains = 0
        # Ensure dates are set
        if 'start_date' not in locals():
            start_date = today
        if 'end_date' not in locals():
            end_date = today
    
    return templates.TemplateResponse("deleted_domains.html", {
        "request": request,
        "active_tlds": active_tlds,
        "selected_tld": tld,
        "days": days,
        "domains_by_date": domains_by_date,
        "sorted_dates": sorted_dates,
        "date_stats": date_stats,
        "total_domains": total_domains,
        "start_date": start_date,
        "end_date": end_date,
        "has_data": total_domains > 0,
        "requested_days": days
    })


