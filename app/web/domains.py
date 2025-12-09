"""
Web route for comprehensive domain listing page.
"""
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

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
    db: Session = Depends(get_db)
):
    """
    Comprehensive domain listing page showing dropped and future-dropping domains.
    """
    # Initialize default values
    active_tlds = []
    selected_date = date.today()
    selected_tld = tld
    dropped_domains = []
    future_domains = []
    total_dropped = 0
    total_future = 0
    
    try:
        # Get all active TLDs for filter
        active_tlds = db.query(Tld).filter(Tld.is_active == True).order_by(Tld.name).all()
        
        # Determine date to show
        if date_filter:
            selected_date = date_filter
        else:
            # Get latest drop date from database
            latest_date = db.query(func.max(DroppedDomain.drop_date)).scalar()
            if latest_date:
                selected_date = latest_date
        
        # Get dropped domains for selected date
        query_dropped = db.query(DroppedDomain).join(Tld)
        query_dropped = query_dropped.filter(DroppedDomain.drop_date == selected_date)
        
        if tld:
            query_dropped = query_dropped.filter(Tld.name == tld.lower())
        
        dropped_domains_list = query_dropped.order_by(
            desc(DroppedDomain.quality_score),
            DroppedDomain.domain
        ).limit(1000).all()
        
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
        
        total_dropped = query_dropped.count()
        
        # Get future dropping domains (domains that will drop in the next N days)
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
            desc(DroppedDomain.quality_score),
            DroppedDomain.domain
        ).limit(1000).all()
        
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
        
    except Exception as e:
        import logging
        logging.error(f"Database error in domains_list route: {e}")
        # Values already set to defaults above
    
    # Get date range for calendar
    date_range = []
    try:
        min_date = db.query(func.min(DroppedDomain.drop_date)).scalar()
        max_date = db.query(func.max(DroppedDomain.drop_date)).scalar()
        
        if min_date and max_date:
            current = min_date
            while current <= max_date:
                count = db.query(func.count(DroppedDomain.id)).filter(
                    DroppedDomain.drop_date == current
                ).scalar()
                date_range.append({
                    "date": current,
                    "count": count
                })
                current += timedelta(days=1)
    except Exception as e:
        import logging
        logging.error(f"Error getting date range: {e}")
    
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
        "date_range": date_range[:30]  # Last 30 days
    })

