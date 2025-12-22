"""
Authentication token models for email verification and password reset.
"""
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
import secrets

from app.core.database import Base


class EmailVerificationToken(Base):
    """Model for email verification tokens."""
    
    __tablename__ = "email_verification_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="email_verification_tokens")
    
    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(48)
    
    @staticmethod
    def create_token(user_id: int, expires_in_hours: int = 24) -> "EmailVerificationToken":
        """Create a new verification token."""
        return EmailVerificationToken(
            user_id=user_id,
            token=EmailVerificationToken.generate_token(),
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
        )
    
    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        return not self.is_used and datetime.utcnow() < self.expires_at
    
    def __repr__(self) -> str:
        return f"<EmailVerificationToken(user_id={self.user_id}, is_used={self.is_used})>"


class PasswordResetToken(Base):
    """Model for password reset tokens."""
    
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="password_reset_tokens")
    
    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(48)
    
    @staticmethod
    def create_token(user_id: int, expires_in_hours: int = 1) -> "PasswordResetToken":
        """Create a new password reset token (expires in 1 hour by default)."""
        return PasswordResetToken(
            user_id=user_id,
            token=PasswordResetToken.generate_token(),
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
        )
    
    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        return not self.is_used and datetime.utcnow() < self.expires_at
    
    def __repr__(self) -> str:
        return f"<PasswordResetToken(user_id={self.user_id}, is_used={self.is_used})>"


