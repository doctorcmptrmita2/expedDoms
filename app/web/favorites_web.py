"""
Web routes for favorites management.
"""
from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db
from app.models.user import User, UserFavorite
from app.models.drop import DroppedDomain
from app.services.subscription_service import SubscriptionService, get_subscription_service
from app.web.auth_web import get_current_user_from_cookie

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/favorites", response_class=HTMLResponse)
def favorites_page(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    db: Session = Depends(get_db)
):
    """
    User favorites page.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/auth/login?next=/favorites", status_code=302)
    
    # Get subscription info
    service = get_subscription_service(db)
    plan = service.get_user_plan(user)
    is_within_limit, current_usage, max_allowed = service.check_plan_limit(user, "favorites_max")
    
    # Get favorites
    query = db.query(UserFavorite).filter(UserFavorite.user_id == user.id)
    total = query.count()
    
    favorites = query.order_by(UserFavorite.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    # Enrich with domain info
    favorite_list = []
    for fav in favorites:
        domain = db.query(DroppedDomain).filter(DroppedDomain.id == fav.domain_id).first()
        favorite_list.append({
            "id": fav.id,
            "domain_id": fav.domain_id,
            "domain": domain.domain if domain else "Unknown",
            "tld": domain.tld.name if domain and domain.tld else "",
            "notes": fav.notes,
            "created_at": fav.created_at,
            "quality_score": domain.quality_score if domain else None,
            "drop_date": domain.drop_date if domain else None
        })
    
    return templates.TemplateResponse("auth/favorites.html", {
        "request": request,
        "user": user,
        "favorites": favorite_list,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "plan": plan,
        "current_usage": current_usage,
        "max_allowed": max_allowed,
        "is_within_limit": is_within_limit
    })


@router.post("/favorites/add", response_class=RedirectResponse)
def add_favorite(
    request: Request,
    domain_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """
    Add domain to favorites.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Check plan limit
    service = get_subscription_service(db)
    is_within_limit, current_usage, max_allowed = service.check_plan_limit(user, "favorites_max")
    
    if not is_within_limit:
        # Redirect with error message
        return RedirectResponse(url=f"/favorites?error=limit_reached&current={current_usage}&max={max_allowed}", status_code=302)
    
    # Check if already favorited
    existing = db.query(UserFavorite).filter(
        and_(
            UserFavorite.user_id == user.id,
            UserFavorite.domain_id == domain_id
        )
    ).first()
    
    if existing:
        return RedirectResponse(url="/favorites?error=already_favorited", status_code=302)
    
    # Create favorite
    favorite = UserFavorite(
        user_id=user.id,
        domain_id=domain_id
    )
    
    db.add(favorite)
    db.commit()
    
    return RedirectResponse(url="/favorites?success=added", status_code=302)


@router.post("/favorites/remove", response_class=RedirectResponse)
def remove_favorite(
    request: Request,
    favorite_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """
    Remove domain from favorites.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    favorite = db.query(UserFavorite).filter(
        and_(
            UserFavorite.id == favorite_id,
            UserFavorite.user_id == user.id
        )
    ).first()
    
    if favorite:
        db.delete(favorite)
        db.commit()
    
    return RedirectResponse(url="/favorites?success=removed", status_code=302)


