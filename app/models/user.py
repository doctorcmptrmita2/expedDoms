"""
User model for authentication and user management.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """Model representing a user account."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    watchlists = relationship("UserWatchlist", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(email={self.email}, username={self.username})>"


class UserWatchlist(Base):
    """Model representing a user's domain watchlist with pattern matching."""
    
    __tablename__ = "user_watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Watchlist settings
    name = Column(String(100), nullable=False)
    domain_pattern = Column(String(255), nullable=True)  # Pattern like "short*", "*tech*"
    
    # Filters
    tld_filter = Column(String(255), nullable=True)  # Comma-separated TLDs: "dev,app,io"
    min_length = Column(Integer, nullable=True)
    max_length = Column(Integer, nullable=True)
    charset_filter = Column(String(50), nullable=True)  # "letters", "numbers", "mixed"
    min_quality_score = Column(Integer, nullable=True)
    
    # Notification settings
    notify_email = Column(Boolean, default=True, nullable=False)
    notify_telegram = Column(Boolean, default=False, nullable=False)
    notify_discord = Column(Boolean, default=False, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_notified_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="watchlists")
    
    def __repr__(self) -> str:
        return f"<UserWatchlist(name={self.name}, user_id={self.user_id})>"


class UserFavorite(Base):
    """Model representing a user's favorite domains."""
    
    __tablename__ = "user_favorites"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    domain_id = Column(BigInteger, ForeignKey("dropped_domains.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # User notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="favorites")
    domain = relationship("DroppedDomain")
    
    # Unique constraint: user can favorite a domain only once
    __table_args__ = (
        Index("idx_user_domain_favorite", "user_id", "domain_id", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<UserFavorite(user_id={self.user_id}, domain_id={self.domain_id})>"








