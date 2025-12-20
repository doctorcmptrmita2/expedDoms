"""
Pydantic schemas for user-related data validation.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# ============== User Schemas ==============

class UserBase(BaseModel):
    """Base schema for user data."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=6, max_length=100)
    password_confirm: str = Field(..., min_length=6, max_length=100)
    
    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        """Validate username contains only alphanumeric characters and underscores."""
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Kullanıcı adı sadece harf, rakam ve alt çizgi içerebilir")
        return v.lower()
    
    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate password confirmation matches password."""
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Şifreler eşleşmiyor")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email_or_username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class UserRead(BaseModel):
    """Schema for reading user data (public)."""
    id: int
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_premium: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)


class PasswordChange(BaseModel):
    """Schema for changing password."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=100)
    new_password_confirm: str = Field(..., min_length=6, max_length=100)
    
    @field_validator("new_password_confirm")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate new password confirmation matches new password."""
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Yeni şifreler eşleşmiyor")
        return v


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=6, max_length=100)
    new_password_confirm: str = Field(..., min_length=6, max_length=100)


# ============== Token Schemas ==============

class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserRead


class TokenData(BaseModel):
    """Schema for token payload data."""
    user_id: int
    email: str
    username: str


# ============== Watchlist Schemas ==============

class WatchlistBase(BaseModel):
    """Base schema for watchlist data."""
    name: str = Field(..., min_length=1, max_length=100)
    domain_pattern: Optional[str] = Field(None, max_length=255)
    tld_filter: Optional[str] = Field(None, max_length=255)
    min_length: Optional[int] = Field(None, ge=1, le=63)
    max_length: Optional[int] = Field(None, ge=1, le=63)
    charset_filter: Optional[str] = Field(None, pattern="^(letters|numbers|mixed)$")
    min_quality_score: Optional[int] = Field(None, ge=0, le=100)
    notify_email: bool = True
    notify_telegram: bool = False
    notify_discord: bool = False
    is_active: bool = True


class WatchlistCreate(WatchlistBase):
    """Schema for creating a watchlist."""
    pass


class WatchlistUpdate(BaseModel):
    """Schema for updating a watchlist."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    domain_pattern: Optional[str] = Field(None, max_length=255)
    tld_filter: Optional[str] = Field(None, max_length=255)
    min_length: Optional[int] = Field(None, ge=1, le=63)
    max_length: Optional[int] = Field(None, ge=1, le=63)
    charset_filter: Optional[str] = Field(None, pattern="^(letters|numbers|mixed)$")
    min_quality_score: Optional[int] = Field(None, ge=0, le=100)
    notify_email: Optional[bool] = None
    notify_telegram: Optional[bool] = None
    notify_discord: Optional[bool] = None
    is_active: Optional[bool] = None


class WatchlistRead(WatchlistBase):
    """Schema for reading watchlist data."""
    id: int
    user_id: int
    last_notified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============== Favorite Schemas ==============

class FavoriteCreate(BaseModel):
    """Schema for creating a favorite."""
    domain_id: int
    notes: Optional[str] = Field(None, max_length=1000)


class FavoriteUpdate(BaseModel):
    """Schema for updating a favorite."""
    notes: Optional[str] = Field(None, max_length=1000)


class FavoriteRead(BaseModel):
    """Schema for reading favorite data."""
    id: int
    user_id: int
    domain_id: int
    domain_name: Optional[str] = None
    tld: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class FavoriteListResponse(BaseModel):
    """Schema for paginated favorite list response."""
    total: int
    page: int
    page_size: int
    results: List[FavoriteRead]






