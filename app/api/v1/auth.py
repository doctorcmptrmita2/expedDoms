"""
Authentication API endpoints.
Handles user registration, login, and token management.
"""
from datetime import timedelta, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserLogin, UserRead, UserUpdate,
    Token, PasswordChange, PasswordReset, PasswordResetConfirm
)
from app.services.auth_service import (
    create_user, authenticate_user, get_user_by_id, get_user_by_email,
    create_access_token, decode_access_token, verify_password,
    update_user_password, ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.services.email_service import EmailService
from app.models.auth_token import EmailVerificationToken, PasswordResetToken

router = APIRouter()
security = HTTPBearer(auto_error=False)


# ============== Dependency Functions ==============

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current authenticated user from JWT token.
    Returns None if not authenticated.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
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


async def get_current_user_required(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """
    Get current authenticated user (required).
    Raises 401 if not authenticated.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Giriş yapmanız gerekiyor",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user_required)
) -> User:
    """
    Get current admin user (required).
    Raises 403 if not admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için yetkiniz yok"
        )
    return current_user


# ============== Auth Endpoints ==============

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.
    
    Returns JWT token on successful registration.
    Sends verification email if email service is configured.
    """
    try:
        user = create_user(
            db=db,
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Create and send verification email
    try:
        email_service = EmailService(db)
        token = EmailVerificationToken.create_token(user.id)
        db.add(token)
        db.commit()
        email_service.send_verification_email(user, token)
    except Exception as e:
        # Log error but don't fail registration
        import logging
        logging.error(f"Failed to send verification email: {e}")
    
    # Create access token
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "email": user.email,
            "username": user.username
        }
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserRead.model_validate(user)
    )


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    
    Accepts either email or username for login.
    """
    user = authenticate_user(
        db=db,
        email_or_username=user_data.email_or_username,
        password=user_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz email/kullanıcı adı veya şifre",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Create access token
    access_token = create_access_token(
        data={
            "user_id": user.id,
            "email": user.email,
            "username": user.username
        }
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserRead.model_validate(user)
    )


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user_required)):
    """
    Get current user's profile information.
    """
    return UserRead.model_validate(current_user)


@router.put("/me", response_model=UserRead)
def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile information.
    """
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    
    if user_data.avatar_url is not None:
        current_user.avatar_url = user_data.avatar_url
    
    db.commit()
    db.refresh(current_user)
    
    return UserRead.model_validate(current_user)


@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Change current user's password.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mevcut şifre yanlış"
        )
    
    # Update password
    update_user_password(db, current_user, password_data.new_password)
    
    return {"message": "Şifreniz başarıyla değiştirildi"}


@router.post("/password-reset")
def request_password_reset(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Request a password reset email.
    
    Always returns success to prevent email enumeration.
    """
    user = get_user_by_email(db, reset_data.email)
    
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
            # Log error but don't reveal if user exists
            import logging
            logging.error(f"Failed to send password reset email: {e}")
    
    # Always return success to prevent email enumeration
    return {"message": "Şifre sıfırlama bağlantısı email adresinize gönderildi"}


@router.post("/password-reset/confirm")
def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset with token.
    """
    # Find token
    token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == reset_data.token
    ).first()
    
    if not token or not token.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz veya süresi dolmuş token"
        )
    
    user = token.user
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kullanıcı bulunamadı"
        )
    
    # Update password
    update_user_password(db, user, reset_data.new_password)
    
    # Mark token as used
    token.is_used = True
    token.used_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Şifreniz başarıyla sıfırlandı"}


@router.post("/refresh", response_model=Token)
def refresh_token(current_user: User = Depends(get_current_user_required)):
    """
    Refresh the access token.
    """
    access_token = create_access_token(
        data={
            "user_id": current_user.id,
            "email": current_user.email,
            "username": current_user.username
        }
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserRead.model_validate(current_user)
    )


@router.get("/verify-email")
def verify_email(
    token: str = Query(..., description="Verification token"),
    db: Session = Depends(get_db)
):
    """
    Verify user email with token.
    """
    # Find token
    verification_token = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == token
    ).first()
    
    if not verification_token or not verification_token.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz veya süresi dolmuş token"
        )
    
    user = verification_token.user
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kullanıcı bulunamadı"
        )
    
    # Mark email as verified
    user.is_verified = True
    verification_token.is_used = True
    verification_token.used_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Email adresiniz başarıyla doğrulandı"}


@router.post("/resend-verification")
def resend_verification_email(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Resend email verification email.
    """
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email adresiniz zaten doğrulanmış"
        )
    
    try:
        email_service = EmailService(db)
        token = EmailVerificationToken.create_token(current_user.id)
        db.add(token)
        db.commit()
        email_service.send_verification_email(current_user, token)
        
        return {"message": "Doğrulama emaili gönderildi"}
    except Exception as e:
        import logging
        logging.error(f"Failed to send verification email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email gönderilemedi"
        )








