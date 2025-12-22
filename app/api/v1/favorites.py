"""
API endpoints for favorites management.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy import and_

from app.core.database import get_db
from app.models.user import User, UserFavorite
from app.models.drop import DroppedDomain
from app.services.subscription_service import SubscriptionService, get_subscription_service
from app.web.auth_web import get_current_user_from_cookie
from fastapi import Request

router = APIRouter()


# ============== Schemas ==============

class FavoriteCreate(BaseModel):
    domain_id: int
    notes: Optional[str] = None


class FavoriteResponse(BaseModel):
    id: int
    domain_id: int
    domain: Optional[str] = None
    tld: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    
    class Config:
        from_attributes = True


class FavoriteListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[FavoriteResponse]


# ============== Endpoints ==============

@router.post("/favorites", response_model=FavoriteResponse)
def create_favorite(
    request: Request,
    favorite: FavoriteCreate,
    db: Session = Depends(get_db)
):
    """
    Add a domain to favorites.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check plan limit
    service = get_subscription_service(db)
    is_within_limit, current_usage, max_allowed = service.check_plan_limit(user, "favorites_max")
    
    if not is_within_limit:
        raise HTTPException(
            status_code=403,
            detail=f"Favorites limit reached ({current_usage}/{max_allowed}). Upgrade your plan to add more favorites."
        )
    
    # Check if domain exists
    domain = db.query(DroppedDomain).filter(DroppedDomain.id == favorite.domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    # Check if already favorited
    existing = db.query(UserFavorite).filter(
        and_(
            UserFavorite.user_id == user.id,
            UserFavorite.domain_id == favorite.domain_id
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Domain already in favorites")
    
    # Create favorite
    favorite_obj = UserFavorite(
        user_id=user.id,
        domain_id=favorite.domain_id,
        notes=favorite.notes
    )
    
    db.add(favorite_obj)
    db.commit()
    db.refresh(favorite_obj)
    
    # Get domain info for response
    favorite_obj.domain = domain.domain
    favorite_obj.tld = domain.tld.name if domain.tld else ""
    
    return favorite_obj


@router.get("/favorites", response_model=FavoriteListResponse)
def list_favorites(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    db: Session = Depends(get_db)
):
    """
    List user's favorites with pagination.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    query = db.query(UserFavorite).filter(UserFavorite.user_id == user.id)
    total = query.count()
    
    favorites = query.order_by(UserFavorite.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    # Enrich with domain info
    results = []
    for fav in favorites:
        domain = db.query(DroppedDomain).filter(DroppedDomain.id == fav.domain_id).first()
        results.append(FavoriteResponse(
            id=fav.id,
            domain_id=fav.domain_id,
            domain=domain.domain if domain else None,
            tld=domain.tld.name if domain and domain.tld else None,
            notes=fav.notes,
            created_at=fav.created_at.isoformat() if fav.created_at else ""
        ))
    
    return FavoriteListResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=results
    )


@router.delete("/favorites/{favorite_id}")
def delete_favorite(
    request: Request,
    favorite_id: int,
    db: Session = Depends(get_db)
):
    """
    Remove a domain from favorites.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    favorite = db.query(UserFavorite).filter(
        and_(
            UserFavorite.id == favorite_id,
            UserFavorite.user_id == user.id
        )
    ).first()
    
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    db.delete(favorite)
    db.commit()
    
    return {"message": "Favorite removed successfully"}


@router.get("/favorites/{domain_id}/check")
def check_favorite(
    request: Request,
    domain_id: int,
    db: Session = Depends(get_db)
):
    """
    Check if a domain is in user's favorites.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    favorite = db.query(UserFavorite).filter(
        and_(
            UserFavorite.user_id == user.id,
            UserFavorite.domain_id == domain_id
        )
    ).first()
    
    return {
        "is_favorite": favorite is not None,
        "favorite_id": favorite.id if favorite else None
    }


