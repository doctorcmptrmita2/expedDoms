"""
Web routes for authentication pages.
Handles login, register, and dashboard pages.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User, UserWatchlist, UserFavorite
from app.models.auth_token import EmailVerificationToken, PasswordResetToken
from app.services.auth_service import (
    create_user, authenticate_user, get_user_by_id, get_user_by_email,
    create_access_token, decode_access_token, update_user_password,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.services.email_service import EmailService
from app.services.subscription_service import SubscriptionService, get_subscription_service
from app.models.subscription import ApiKey
from datetime import datetime
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

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
    try:
        user = get_current_user_from_cookie(request, db)
        
        if not user:
            return RedirectResponse(url="/auth/login?next=/dashboard", status_code=302)
        
        # Get user stats
        watchlist_count = db.query(func.count(UserWatchlist.id)).filter(
            UserWatchlist.user_id == user.id
        ).scalar() or 0
        
        favorite_count = db.query(func.count(UserFavorite.id)).filter(
            UserFavorite.user_id == user.id
        ).scalar() or 0
        
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
        
        # Get subscription info
        subscription_service = get_subscription_service(db)
        plan = subscription_service.get_user_plan(user)
        subscription = subscription_service.get_user_subscription(user)
        
        # Get usage stats
        _, watchlist_usage, watchlist_max = subscription_service.check_plan_limit(user, "watchlist_max")
        _, favorites_usage, favorites_max = subscription_service.check_plan_limit(user, "favorites_max")
        
        # Get API keys count (if user has API access)
        api_keys_count = 0
        try:
            if subscription_service.can_access_feature(user, "api_access"):
                api_keys_count = db.query(func.count(ApiKey.id)).filter(
                    ApiKey.user_id == user.id,
                    ApiKey.is_active == True
                ).scalar() or 0
        except Exception:
            api_keys_count = 0
        
        # Prepare template context with safe defaults
        context = {
            "request": request,
            "user": user,
            "watchlist_count": watchlist_count,
            "favorite_count": favorite_count,
            "recent_watchlists": recent_watchlists or [],
            "recent_favorites": favorites_data or [],
            "plan": plan,
            "subscription": subscription,
            "watchlist_usage": watchlist_usage or 0,
            "watchlist_max": watchlist_max if watchlist_max is not None else 0,
            "favorites_usage": favorites_usage or 0,
            "favorites_max": favorites_max if favorites_max is not None else 0,
            "api_keys_count": api_keys_count,
            "can_export": subscription_service.can_access_feature(user, "export_enabled") if subscription_service else False,
            "has_api_access": subscription_service.can_access_feature(user, "api_access") if subscription_service else False
        }
        
        return templates.TemplateResponse("auth/dashboard.html", context)
    except Exception as e:
        logger.error(f"Dashboard error: {e}", exc_info=True)
        # Return simple error message
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            f"Dashboard Error: {str(e)}\n\nPlease check server logs for details.",
            status_code=500
        )


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


@router.get("/auth/verify-email", response_class=HTMLResponse)
def verify_email_page(
    request: Request,
    token: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Email verification page.
    """
    if not token:
        return templates.TemplateResponse("auth/verify_email.html", {
            "request": request,
            "success": False,
            "message": "Token bulunamadı"
        })
    
    # Find token
    verification_token = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == token
    ).first()
    
    if not verification_token or not verification_token.is_valid():
        return templates.TemplateResponse("auth/verify_email.html", {
            "request": request,
            "success": False,
            "message": "Geçersiz veya süresi dolmuş token"
        })
    
    user = verification_token.user
    if not user:
        return templates.TemplateResponse("auth/verify_email.html", {
            "request": request,
            "success": False,
            "message": "Kullanıcı bulunamadı"
        })
    
    # Mark email as verified
    user.is_verified = True
    verification_token.is_used = True
    verification_token.used_at = datetime.utcnow()
    db.commit()
    
    return templates.TemplateResponse("auth/verify_email.html", {
        "request": request,
        "success": True,
        "message": "Email adresiniz başarıyla doğrulandı!"
    })


@router.get("/auth/reset-password", response_class=HTMLResponse)
def reset_password_page(
    request: Request,
    token: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Password reset page.
    """
    if not token:
        return templates.TemplateResponse("auth/reset_password.html", {
            "request": request,
            "token": None,
            "error": "Token bulunamadı"
        })
    
    # Verify token
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token
    ).first()
    
    if not reset_token or not reset_token.is_valid():
        return templates.TemplateResponse("auth/reset_password.html", {
            "request": request,
            "token": None,
            "error": "Geçersiz veya süresi dolmuş token"
        })
    
    return templates.TemplateResponse("auth/reset_password.html", {
        "request": request,
        "token": token,
        "error": None
    })


@router.post("/auth/reset-password", response_class=HTMLResponse)
def reset_password_submit(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Process password reset form submission.
    """
    # Validate passwords match
    if new_password != confirm_password:
        return templates.TemplateResponse("auth/reset_password.html", {
            "request": request,
            "token": token,
            "error": "Şifreler eşleşmiyor"
        })
    
    # Validate password length
    if len(new_password) < 6:
        return templates.TemplateResponse("auth/reset_password.html", {
            "request": request,
            "token": token,
            "error": "Şifre en az 6 karakter olmalıdır"
        })
    
    # Find token
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token
    ).first()
    
    if not reset_token or not reset_token.is_valid():
        return templates.TemplateResponse("auth/reset_password.html", {
            "request": request,
            "token": None,
            "error": "Geçersiz veya süresi dolmuş token"
        })
    
    user = reset_token.user
    if not user:
        return templates.TemplateResponse("auth/reset_password.html", {
            "request": request,
            "token": None,
            "error": "Kullanıcı bulunamadı"
        })
    
    # Update password
    update_user_password(db, user, new_password)
    
    # Mark token as used
    reset_token.is_used = True
    reset_token.used_at = datetime.utcnow()
    db.commit()
    
    return templates.TemplateResponse("auth/reset_password.html", {
        "request": request,
        "token": None,
        "success": True,
        "message": "Şifreniz başarıyla sıfırlandı. Giriş yapabilirsiniz."
    })


@router.get("/auth/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    """
    Forgot password page.
    """
    return templates.TemplateResponse("auth/forgot_password.html", {
        "request": request,
        "error": None,
        "success": False
    })


@router.post("/auth/forgot-password", response_class=HTMLResponse)
def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Process forgot password form submission.
    """
    user = get_user_by_email(db, email)
    
    if user:
        try:
            # Create password reset token
            token = PasswordResetToken.create_token(user.id)
            db.add(token)
            db.commit()
            
            # Send email
            email_service = EmailService(db)
            email_service.send_password_reset_email(user, token)
        except Exception as e:
            import logging
            logging.error(f"Failed to send password reset email: {e}")
    
    # Always return success to prevent email enumeration
    return templates.TemplateResponse("auth/forgot_password.html", {
        "request": request,
        "error": None,
        "success": True,
        "message": "Şifre sıfırlama bağlantısı email adresinize gönderildi"
    })


@router.get("/auth/resend-verification", response_class=HTMLResponse)
def resend_verification_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Resend verification email page.
    """
    user = get_current_user_from_cookie(request, db)
    
    if not user:
        return RedirectResponse(url="/login?next=/auth/resend-verification", status_code=302)
    
    if user.is_verified:
        return templates.TemplateResponse("auth/verify_email.html", {
            "request": request,
            "success": True,
            "message": "Email adresiniz zaten doğrulanmış"
        })
    
    return templates.TemplateResponse("auth/resend_verification.html", {
        "request": request,
        "user": user,
        "error": None,
        "success": False
    })


@router.post("/auth/resend-verification", response_class=HTMLResponse)
def resend_verification_submit(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Process resend verification email form submission.
    """
    user = get_current_user_from_cookie(request, db)
    
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    if user.is_verified:
        return templates.TemplateResponse("auth/verify_email.html", {
            "request": request,
            "success": True,
            "message": "Email adresiniz zaten doğrulanmış"
        })
    
    try:
        email_service = EmailService(db)
        token = EmailVerificationToken.create_token(user.id)
        db.add(token)
        db.commit()
        email_service.send_verification_email(user, token)
        
        return templates.TemplateResponse("auth/resend_verification.html", {
            "request": request,
            "user": user,
            "error": None,
            "success": True,
            "message": "Doğrulama emaili gönderildi. Lütfen email kutunuzu kontrol edin."
        })
    except Exception as e:
        import logging
        logging.error(f"Failed to send verification email: {e}")
        return templates.TemplateResponse("auth/resend_verification.html", {
            "request": request,
            "user": user,
            "error": "Email gönderilemedi. Lütfen daha sonra tekrar deneyin.",
            "success": False
        })






