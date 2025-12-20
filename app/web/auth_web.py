"""
Web routes for authentication pages.
Handles login, register, and dashboard pages.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User, UserWatchlist, UserFavorite
from app.services.auth_service import (
    create_user, authenticate_user, get_user_by_id,
    create_access_token, decode_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from sqlalchemy import func

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_current_user_from_cookie(request: Request, db: Session) -> Optional[User]:
    """
    Get current user from cookie token.
    """
    token = request.cookies.get("access_token")
    
    if not token:
        return None
    
    # Remove 'Bearer ' prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    payload = decode_access_token(token)
    
    if not payload:
        return None
    
    user_id = payload.get("user_id")
    if not user_id:
        return None
    
    user = get_user_by_id(db, user_id)
    
    if not user or not user.is_active:
        return None
    
    return user


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    """
    Login page.
    """
    # Check if already logged in
    user = get_current_user_from_cookie(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse("auth/login.html", {
        "request": request,
        "error": None
    })


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    email_or_username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Process login form submission.
    """
    user = authenticate_user(db, email_or_username, password)
    
    if not user:
        return templates.TemplateResponse("auth/login.html", {
            "request": request,
            "error": "Geçersiz email/kullanıcı adı veya şifre"
        })
    
    # Create access token
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "email": user.email,
            "username": user.username
        }
    )
    
    # Redirect to dashboard with cookie
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    """
    Registration page.
    """
    # Check if already logged in
    user = get_current_user_from_cookie(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse("auth/register.html", {
        "request": request,
        "error": None
    })


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    full_name: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Process registration form submission.
    """
    # Validate passwords match
    if password != password_confirm:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "Şifreler eşleşmiyor"
        })
    
    # Validate password length
    if len(password) < 6:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "Şifre en az 6 karakter olmalıdır"
        })
    
    # Validate username
    if len(username) < 3:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": "Kullanıcı adı en az 3 karakter olmalıdır"
        })
    
    try:
        user = create_user(
            db=db,
            email=email,
            username=username,
            password=password,
            full_name=full_name if full_name else None
        )
    except ValueError as e:
        return templates.TemplateResponse("auth/register.html", {
            "request": request,
            "error": str(e)
        })
    
    # Create access token
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "email": user.email,
            "username": user.username
        }
    )
    
    # Redirect to dashboard with cookie
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    
    return response


@router.get("/logout")
def logout(request: Request):
    """
    Logout and clear cookie.
    """
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    return response


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, db: Session = Depends(get_db)):
    """
    User dashboard page.
    """
    user = get_current_user_from_cookie(request, db)
    
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Get user stats
    watchlist_count = db.query(func.count(UserWatchlist.id)).filter(
        UserWatchlist.user_id == user.id
    ).scalar()
    
    favorite_count = db.query(func.count(UserFavorite.id)).filter(
        UserFavorite.user_id == user.id
    ).scalar()
    
    # Get recent watchlists
    recent_watchlists = db.query(UserWatchlist).filter(
        UserWatchlist.user_id == user.id
    ).order_by(UserWatchlist.created_at.desc()).limit(5).all()
    
    # Get recent favorites with domain info
    from app.models.drop import DroppedDomain
    recent_favorites = db.query(UserFavorite).filter(
        UserFavorite.user_id == user.id
    ).order_by(UserFavorite.created_at.desc()).limit(10).all()
    
    # Enrich favorites with domain data
    favorites_data = []
    for fav in recent_favorites:
        domain = db.query(DroppedDomain).filter(DroppedDomain.id == fav.domain_id).first()
        if domain:
            favorites_data.append({
                "id": fav.id,
                "domain": domain.domain,
                "tld": domain.tld.name if domain.tld else "",
                "drop_date": domain.drop_date,
                "notes": fav.notes,
                "created_at": fav.created_at
            })
    
    return templates.TemplateResponse("auth/dashboard.html", {
        "request": request,
        "user": user,
        "watchlist_count": watchlist_count,
        "favorite_count": favorite_count,
        "recent_watchlists": recent_watchlists,
        "recent_favorites": favorites_data
    })


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, db: Session = Depends(get_db)):
    """
    User profile page.
    """
    user = get_current_user_from_cookie(request, db)
    
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("auth/profile.html", {
        "request": request,
        "user": user,
        "success": None,
        "error": None
    })


@router.get("/watchlists", response_class=HTMLResponse)
def watchlists_page(request: Request, db: Session = Depends(get_db)):
    """
    User watchlists page.
    """
    user = get_current_user_from_cookie(request, db)
    
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    watchlists = db.query(UserWatchlist).filter(
        UserWatchlist.user_id == user.id
    ).order_by(UserWatchlist.created_at.desc()).all()
    
    max_watchlists = 20 if user.is_premium else 3
    
    return templates.TemplateResponse("auth/watchlists.html", {
        "request": request,
        "user": user,
        "watchlists": watchlists,
        "max_watchlists": max_watchlists
    })


@router.get("/favorites", response_class=HTMLResponse)
def favorites_page(request: Request, db: Session = Depends(get_db)):
    """
    User favorites page.
    """
    user = get_current_user_from_cookie(request, db)
    
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    from app.models.drop import DroppedDomain
    
    favorites = db.query(UserFavorite).filter(
        UserFavorite.user_id == user.id
    ).order_by(UserFavorite.created_at.desc()).all()
    
    # Enrich with domain data
    favorites_data = []
    for fav in favorites:
        domain = db.query(DroppedDomain).filter(DroppedDomain.id == fav.domain_id).first()
        if domain:
            favorites_data.append({
                "id": fav.id,
                "domain_id": fav.domain_id,
                "domain": domain.domain,
                "tld": domain.tld.name if domain.tld else "",
                "drop_date": domain.drop_date,
                "length": domain.length,
                "charset_type": domain.charset_type,
                "notes": fav.notes,
                "created_at": fav.created_at
            })
    
    return templates.TemplateResponse("auth/favorites.html", {
        "request": request,
        "user": user,
        "favorites": favorites_data
    })






