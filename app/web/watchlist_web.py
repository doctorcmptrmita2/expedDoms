"""
Web routes for watchlist management.
"""
from fastapi import APIRouter, Depends, Request, Form, Query, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db
from app.models.user import User, UserWatchlist
from app.services.subscription_service import SubscriptionService, get_subscription_service
from app.web.auth_web import get_current_user_from_cookie

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/watchlists", response_class=HTMLResponse)
def watchlists_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    User watchlists page.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/auth/login?next=/watchlists", status_code=302)
    
    # Get subscription info
    service = get_subscription_service(db)
    plan = service.get_user_plan(user)
    is_within_limit, current_usage, max_allowed = service.check_plan_limit(user, "watchlist_max")
    
    # Get watchlists
    watchlists = db.query(UserWatchlist).filter(
        UserWatchlist.user_id == user.id
    ).order_by(UserWatchlist.created_at.desc()).all()
    
    # Get TLD list for filter dropdown
    from app.models.tld import Tld
    tlds = db.query(Tld).filter(Tld.is_active == True).order_by(Tld.name).all()
    
    return templates.TemplateResponse("auth/watchlists.html", {
        "request": request,
        "user": user,
        "watchlists": watchlists,
        "plan": plan,
        "current_usage": current_usage,
        "max_allowed": max_allowed,
        "is_within_limit": is_within_limit,
        "tlds": tlds
    })


@router.post("/watchlists/create", response_class=RedirectResponse)
def create_watchlist(
    request: Request,
    name: str = Form(...),
    domain_pattern: str = Form(None),
    tld_filter: str = Form(None),
    min_length: int = Form(None),
    max_length: int = Form(None),
    charset_filter: str = Form(None),
    min_quality_score: int = Form(None),
    notify_email: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    Create a new watchlist.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Check plan limit
    service = get_subscription_service(db)
    is_within_limit, current_usage, max_allowed = service.check_plan_limit(user, "watchlist_max")
    
    if not is_within_limit:
        return RedirectResponse(url=f"/watchlists?error=limit_reached&current={current_usage}&max={max_allowed}", status_code=302)
    
    # Create watchlist
    watchlist = UserWatchlist(
        user_id=user.id,
        name=name,
        domain_pattern=domain_pattern if domain_pattern else None,
        tld_filter=tld_filter if tld_filter else None,
        min_length=min_length if min_length else None,
        max_length=max_length if max_length else None,
        charset_filter=charset_filter if charset_filter else None,
        min_quality_score=min_quality_score if min_quality_score else None,
        notify_email=notify_email
    )
    
    db.add(watchlist)
    db.commit()
    
    return RedirectResponse(url="/watchlists?success=created", status_code=302)


@router.post("/watchlists/{watchlist_id}/delete", response_class=RedirectResponse)
def delete_watchlist(
    request: Request,
    watchlist_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a watchlist.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    watchlist = db.query(UserWatchlist).filter(
        and_(
            UserWatchlist.id == watchlist_id,
            UserWatchlist.user_id == user.id
        )
    ).first()
    
    if watchlist:
        db.delete(watchlist)
        db.commit()
    
    return RedirectResponse(url="/watchlists?success=deleted", status_code=302)


@router.get("/watchlists/{watchlist_id}/matches", response_class=HTMLResponse)
def watchlist_matches(
    request: Request,
    watchlist_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    db: Session = Depends(get_db)
):
    """
    Show matched domains for a watchlist.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    watchlist = db.query(UserWatchlist).filter(
        and_(
            UserWatchlist.id == watchlist_id,
            UserWatchlist.user_id == user.id
        )
    ).first()
    
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    
    # Get matched domains using watchlist criteria
    from app.models.drop import DroppedDomain
    from app.models.tld import Tld
    import re
    
    # Start with all dropped domains
    query = db.query(DroppedDomain).join(Tld)
    
    # Apply TLD filter
    if watchlist.tld_filter:
        tlds = [t.strip().lower() for t in watchlist.tld_filter.split(',')]
        query = query.filter(Tld.name.in_(tlds))
    
    # Apply length filter
    if watchlist.min_length:
        query = query.filter(DroppedDomain.length >= watchlist.min_length)
    if watchlist.max_length:
        query = query.filter(DroppedDomain.length <= watchlist.max_length)
    
    # Apply quality score filter
    if watchlist.min_quality_score:
        query = query.filter(DroppedDomain.quality_score >= watchlist.min_quality_score)
    
    # Get all matching domains
    all_domains = query.order_by(DroppedDomain.drop_date.desc(), DroppedDomain.quality_score.desc()).all()
    
    # Filter by domain pattern and charset (requires domain name extraction)
    matched_domains = []
    for domain in all_domains:
        domain_name = domain.domain.split('.')[0] if '.' in domain.domain else domain.domain
        
        # Check domain pattern
        if watchlist.domain_pattern:
            try:
                pattern = watchlist.domain_pattern.replace('*', '.*')
                if not re.search(pattern, domain_name, re.IGNORECASE):
                    continue
            except re.error:
                pass  # Invalid regex, skip pattern check
        
        # Check charset filter
        if watchlist.charset_filter:
            if watchlist.charset_filter == "letters" and not domain_name.isalpha():
                continue
            elif watchlist.charset_filter == "numbers" and not domain_name.isdigit():
                continue
            elif watchlist.charset_filter == "mixed":
                if not (domain_name.isalnum() and not domain_name.isalpha() and not domain_name.isdigit()):
                    continue
        
        matched_domains.append(domain)
    
    # Pagination
    total = len(matched_domains)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_domains = matched_domains[start:end]
    
    # Format matches for template
    matches = []
    for domain in paginated_domains:
        matches.append({
            "id": domain.id,
            "domain": domain.domain,
            "tld": domain.tld.name if domain.tld else "",
            "drop_date": domain.drop_date,
            "quality_score": domain.quality_score,
            "length": domain.length,
            "charset_type": domain.charset_type
        })
    
    return templates.TemplateResponse("auth/watchlist_matches.html", {
        "request": request,
        "watchlist": watchlist,
        "matches": matches,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size
    })



