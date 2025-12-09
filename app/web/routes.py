"""
Web routes for HTML pages.
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.core.database import get_db
from app.models.tld import Tld
from app.models.drop import DroppedDomain
from app.schemas.drop import DropRead

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    """
    Home page with stats and preview.
    """
    # Get stats
    tld_count = db.query(Tld).filter(Tld.is_active == True).count()
    
    latest_date = db.query(func.max(DroppedDomain.drop_date)).scalar()
    
    latest_drop_count = 0
    if latest_date:
        latest_drop_count = db.query(func.count(DroppedDomain.id)).filter(
            DroppedDomain.drop_date == latest_date
        ).scalar()
    
    # Get top 20 latest drops for preview
    preview_drops = db.query(DroppedDomain).join(Tld).order_by(
        desc(DroppedDomain.drop_date),
        DroppedDomain.domain
    ).limit(20).all()
    
    preview_results = [
        DropRead(
            id=drop.id,
            domain=drop.domain,
            tld=drop.tld.name,
            drop_date=drop.drop_date,
            length=drop.length,
            charset_type=drop.charset_type
        )
        for drop in preview_drops
    ]
    
    return templates.TemplateResponse("home.html", {
        "request": request,
        "tld_count": tld_count,
        "latest_date": latest_date,
        "latest_drop_count": latest_drop_count,
        "preview_drops": preview_results
    })


@router.get("/drops", response_class=HTMLResponse)
def drops_list(
    request: Request,
    date_filter: Optional[date] = Query(None, alias="date"),
    tld: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Drops list page with filters.
    """
    # Get all active TLDs for filter
    active_tlds = db.query(Tld).filter(Tld.is_active == True).order_by(Tld.name).all()
    
    # Determine date to show
    if date_filter is None:
        date_filter = db.query(func.max(DroppedDomain.drop_date)).scalar()
    
    # Get initial page of results
    query = db.query(DroppedDomain).join(Tld)
    
    if date_filter:
        query = query.filter(DroppedDomain.drop_date == date_filter)
    
    if tld:
        query = query.filter(Tld.name == tld.lower())
    
    initial_drops = query.order_by(DroppedDomain.domain).limit(50).all()
    
    initial_results = [
        DropRead(
            id=drop.id,
            domain=drop.domain,
            tld=drop.tld.name,
            drop_date=drop.drop_date,
            length=drop.length,
            charset_type=drop.charset_type
        )
        for drop in initial_drops
    ]
    
    total_count = query.count() if date_filter else 0
    
    return templates.TemplateResponse("drops_list.html", {
        "request": request,
        "active_tlds": active_tlds,
        "selected_date": date_filter,
        "selected_tld": tld,
        "initial_drops": initial_results,
        "total_count": total_count
    })


@router.get("/tlds", response_class=HTMLResponse)
def tld_list(request: Request, db: Session = Depends(get_db)):
    """
    TLD list page.
    """
    tlds = db.query(Tld).filter(Tld.is_active == True).order_by(Tld.name).all()
    
    return templates.TemplateResponse("tld_list.html", {
        "request": request,
        "tlds": tlds
    })


@router.get("/about", response_class=HTMLResponse)
def about(request: Request):
    """
    About page.
    """
    return templates.TemplateResponse("about.html", {
        "request": request
    })

