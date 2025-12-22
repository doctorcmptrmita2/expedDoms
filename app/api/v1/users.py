"""
User management API endpoints.
Handles watchlists and favorites.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.user import User, UserWatchlist, UserFavorite
from app.models.drop import DroppedDomain
from app.models.tld import Tld
from app.schemas.user import (
    WatchlistCreate, WatchlistUpdate, WatchlistRead,
    FavoriteCreate, FavoriteUpdate, FavoriteRead, FavoriteListResponse
)
from app.api.v1.auth import get_current_user_required

router = APIRouter()


# ============== Watchlist Endpoints ==============

@router.get("/watchlists", response_model=List[WatchlistRead])
def list_watchlists(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    List all watchlists for the current user.
    """
    watchlists = db.query(UserWatchlist).filter(
        UserWatchlist.user_id == current_user.id
    ).order_by(UserWatchlist.created_at.desc()).all()
    
    return [WatchlistRead.model_validate(w) for w in watchlists]


@router.post("/watchlists", response_model=WatchlistRead, status_code=status.HTTP_201_CREATED)
def create_watchlist(
    watchlist_data: WatchlistCreate,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Create a new watchlist for the current user.
    """
    # Check watchlist limit (free users: 3, premium: 20)
    existing_count = db.query(func.count(UserWatchlist.id)).filter(
        UserWatchlist.user_id == current_user.id
    ).scalar()
    
    max_watchlists = 20 if current_user.is_premium else 3
    
    if existing_count >= max_watchlists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Maksimum {max_watchlists} watchlist oluşturabilirsiniz. Premium üyelik ile limiti artırabilirsiniz."
        )
    
    watchlist = UserWatchlist(
        user_id=current_user.id,
        name=watchlist_data.name,
        domain_pattern=watchlist_data.domain_pattern,
        tld_filter=watchlist_data.tld_filter,
        min_length=watchlist_data.min_length,
        max_length=watchlist_data.max_length,
        charset_filter=watchlist_data.charset_filter,
        min_quality_score=watchlist_data.min_quality_score,
        notify_email=watchlist_data.notify_email,
        notify_telegram=watchlist_data.notify_telegram,
        notify_discord=watchlist_data.notify_discord,
        is_active=watchlist_data.is_active
    )
    
    db.add(watchlist)
    db.commit()
    db.refresh(watchlist)
    
    return WatchlistRead.model_validate(watchlist)


@router.get("/watchlists/{watchlist_id}", response_model=WatchlistRead)
def get_watchlist(
    watchlist_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Get a specific watchlist by ID.
    """
    watchlist = db.query(UserWatchlist).filter(
        UserWatchlist.id == watchlist_id,
        UserWatchlist.user_id == current_user.id
    ).first()
    
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist bulunamadı"
        )
    
    return WatchlistRead.model_validate(watchlist)


@router.put("/watchlists/{watchlist_id}", response_model=WatchlistRead)
def update_watchlist(
    watchlist_id: int,
    watchlist_data: WatchlistUpdate,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Update a watchlist.
    """
    watchlist = db.query(UserWatchlist).filter(
        UserWatchlist.id == watchlist_id,
        UserWatchlist.user_id == current_user.id
    ).first()
    
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist bulunamadı"
        )
    
    # Update fields
    update_data = watchlist_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(watchlist, field, value)
    
    db.commit()
    db.refresh(watchlist)
    
    return WatchlistRead.model_validate(watchlist)


@router.delete("/watchlists/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watchlist(
    watchlist_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Delete a watchlist.
    """
    watchlist = db.query(UserWatchlist).filter(
        UserWatchlist.id == watchlist_id,
        UserWatchlist.user_id == current_user.id
    ).first()
    
    if not watchlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist bulunamadı"
        )
    
    db.delete(watchlist)
    db.commit()


# ============== Favorites Endpoints ==============

@router.get("/favorites", response_model=FavoriteListResponse)
def list_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    List all favorites for the current user with pagination.
    """
    query = db.query(UserFavorite).filter(
        UserFavorite.user_id == current_user.id
    )
    
    total = query.count()
    offset = (page - 1) * page_size
    
    favorites = query.order_by(UserFavorite.created_at.desc()).offset(offset).limit(page_size).all()
    
    # Build response with domain info
    results = []
    for fav in favorites:
        domain = db.query(DroppedDomain).filter(DroppedDomain.id == fav.domain_id).first()
        
        results.append(FavoriteRead(
            id=fav.id,
            user_id=fav.user_id,
            domain_id=fav.domain_id,
            domain_name=domain.domain if domain else None,
            tld=domain.tld.name if domain and domain.tld else None,
            notes=fav.notes,
            created_at=fav.created_at
        ))
    
    return FavoriteListResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=results
    )


@router.post("/favorites", response_model=FavoriteRead, status_code=status.HTTP_201_CREATED)
def create_favorite(
    favorite_data: FavoriteCreate,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Add a domain to favorites.
    """
    # Check if domain exists
    domain = db.query(DroppedDomain).filter(
        DroppedDomain.id == favorite_data.domain_id
    ).first()
    
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain bulunamadı"
        )
    
    # Check if already favorited
    existing = db.query(UserFavorite).filter(
        UserFavorite.user_id == current_user.id,
        UserFavorite.domain_id == favorite_data.domain_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu domain zaten favorilerinizde"
        )
    
    # Check favorites limit (free: 100, premium: unlimited)
    if not current_user.is_premium:
        fav_count = db.query(func.count(UserFavorite.id)).filter(
            UserFavorite.user_id == current_user.id
        ).scalar()
        
        if fav_count >= 100:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Maksimum 100 favori ekleyebilirsiniz. Premium üyelik ile sınırsız favori ekleyebilirsiniz."
            )
    
    favorite = UserFavorite(
        user_id=current_user.id,
        domain_id=favorite_data.domain_id,
        notes=favorite_data.notes
    )
    
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    
    return FavoriteRead(
        id=favorite.id,
        user_id=favorite.user_id,
        domain_id=favorite.domain_id,
        domain_name=domain.domain,
        tld=domain.tld.name if domain.tld else None,
        notes=favorite.notes,
        created_at=favorite.created_at
    )


@router.put("/favorites/{favorite_id}", response_model=FavoriteRead)
def update_favorite(
    favorite_id: int,
    favorite_data: FavoriteUpdate,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Update favorite notes.
    """
    favorite = db.query(UserFavorite).filter(
        UserFavorite.id == favorite_id,
        UserFavorite.user_id == current_user.id
    ).first()
    
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favori bulunamadı"
        )
    
    if favorite_data.notes is not None:
        favorite.notes = favorite_data.notes
    
    db.commit()
    db.refresh(favorite)
    
    domain = db.query(DroppedDomain).filter(DroppedDomain.id == favorite.domain_id).first()
    
    return FavoriteRead(
        id=favorite.id,
        user_id=favorite.user_id,
        domain_id=favorite.domain_id,
        domain_name=domain.domain if domain else None,
        tld=domain.tld.name if domain and domain.tld else None,
        notes=favorite.notes,
        created_at=favorite.created_at
    )


@router.delete("/favorites/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(
    favorite_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Remove a domain from favorites.
    """
    favorite = db.query(UserFavorite).filter(
        UserFavorite.id == favorite_id,
        UserFavorite.user_id == current_user.id
    ).first()
    
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favori bulunamadı"
        )
    
    db.delete(favorite)
    db.commit()


@router.delete("/favorites/domain/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite_by_domain(
    domain_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Remove a domain from favorites by domain ID.
    """
    favorite = db.query(UserFavorite).filter(
        UserFavorite.domain_id == domain_id,
        UserFavorite.user_id == current_user.id
    ).first()
    
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favori bulunamadı"
        )
    
    db.delete(favorite)
    db.commit()


@router.get("/favorites/check/{domain_id}")
def check_favorite(
    domain_id: int,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Check if a domain is in favorites.
    """
    favorite = db.query(UserFavorite).filter(
        UserFavorite.domain_id == domain_id,
        UserFavorite.user_id == current_user.id
    ).first()
    
    return {"is_favorite": favorite is not None, "favorite_id": favorite.id if favorite else None}








