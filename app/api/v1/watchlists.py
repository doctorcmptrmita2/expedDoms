"""
API endpoints for watchlist management.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy import and_

from app.core.database import get_db
from app.models.user import User, UserWatchlist
from app.services.subscription_service import SubscriptionService, get_subscription_service
from app.web.auth_web import get_current_user_from_cookie
from fastapi import Request

router = APIRouter()


# ============== Schemas ==============

class WatchlistCreate(BaseModel):
    name: str
    domain_pattern: Optional[str] = None
    tld_filter: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    charset_filter: Optional[str] = None
    min_quality_score: Optional[int] = None
    notify_email: bool = True
    notify_telegram: bool = False
    notify_discord: bool = False


class WatchlistUpdate(BaseModel):
    name: Optional[str] = None
    domain_pattern: Optional[str] = None
    tld_filter: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    charset_filter: Optional[str] = None
    min_quality_score: Optional[int] = None
    notify_email: Optional[bool] = None
    notify_telegram: Optional[bool] = None
    notify_discord: Optional[bool] = None
    is_active: Optional[bool] = None


class WatchlistResponse(BaseModel):
    id: int
    name: str
    domain_pattern: Optional[str]
    tld_filter: Optional[str]
    min_length: Optional[int]
    max_length: Optional[int]
    charset_filter: Optional[str]
    min_quality_score: Optional[int]
    notify_email: bool
    notify_telegram: bool
    notify_discord: bool
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True


# ============== Endpoints ==============

@router.post("/watchlists", response_model=WatchlistResponse)
def create_watchlist(
    request: Request,
    watchlist: WatchlistCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new watchlist.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check plan limit
    service = get_subscription_service(db)
    is_within_limit, current_usage, max_allowed = service.check_plan_limit(user, "watchlist_max")
    
    if not is_within_limit:
        raise HTTPException(
            status_code=403,
            detail=f"Watchlist limit reached ({current_usage}/{max_allowed}). Upgrade your plan to create more watchlists."
        )
    
    # Create watchlist
    watchlist_obj = UserWatchlist(
        user_id=user.id,
        name=watchlist.name,
        domain_pattern=watchlist.domain_pattern,
        tld_filter=watchlist.tld_filter,
        min_length=watchlist.min_length,
        max_length=watchlist.max_length,
        charset_filter=watchlist.charset_filter,
        min_quality_score=watchlist.min_quality_score,
        notify_email=watchlist.notify_email,
        notify_telegram=watchlist.notify_telegram,
        notify_discord=watchlist.notify_discord
    )
    
    db.add(watchlist_obj)
    db.commit()
    db.refresh(watchlist_obj)
    
    return watchlist_obj


@router.get("/watchlists", response_model=List[WatchlistResponse])
def list_watchlists(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    List user's watchlists.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    watchlists = db.query(UserWatchlist).filter(
        UserWatchlist.user_id == user.id
    ).order_by(UserWatchlist.created_at.desc()).all()
    
    return watchlists


@router.get("/watchlists/{watchlist_id}", response_model=WatchlistResponse)
def get_watchlist(
    request: Request,
    watchlist_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific watchlist.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    watchlist = db.query(UserWatchlist).filter(
        and_(
            UserWatchlist.id == watchlist_id,
            UserWatchlist.user_id == user.id
        )
    ).first()
    
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    
    return watchlist


@router.put("/watchlists/{watchlist_id}", response_model=WatchlistResponse)
def update_watchlist(
    request: Request,
    watchlist_id: int,
    watchlist: WatchlistUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a watchlist.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    watchlist_obj = db.query(UserWatchlist).filter(
        and_(
            UserWatchlist.id == watchlist_id,
            UserWatchlist.user_id == user.id
        )
    ).first()
    
    if not watchlist_obj:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    
    # Update fields
    update_data = watchlist.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(watchlist_obj, field, value)
    
    db.commit()
    db.refresh(watchlist_obj)
    
    return watchlist_obj


@router.delete("/watchlists/{watchlist_id}")
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
        raise HTTPException(status_code=401, detail="Authentication required")
    
    watchlist = db.query(UserWatchlist).filter(
        and_(
            UserWatchlist.id == watchlist_id,
            UserWatchlist.user_id == user.id
        )
    ).first()
    
    if not watchlist:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    
    db.delete(watchlist)
    db.commit()
    
    return {"message": "Watchlist deleted successfully"}


