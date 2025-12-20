"""
Notification model for user alerts.
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.database import Base


class NotificationChannel(str, Enum):
    """Supported notification channels."""
    EMAIL = "email"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WEBHOOK = "webhook"


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationSetting(Base):
    """User notification settings for different channels."""
    
    __tablename__ = "notification_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Email settings
    email_enabled = Column(Boolean, default=True, nullable=False)
    email_address = Column(String(255), nullable=True)  # Override user email
    
    # Telegram settings
    telegram_enabled = Column(Boolean, default=False, nullable=False)
    telegram_chat_id = Column(String(100), nullable=True)
    telegram_bot_token = Column(String(255), nullable=True)  # For custom bots
    
    # Discord settings
    discord_enabled = Column(Boolean, default=False, nullable=False)
    discord_webhook_url = Column(String(500), nullable=True)
    
    # Webhook settings
    webhook_enabled = Column(Boolean, default=False, nullable=False)
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(255), nullable=True)  # For HMAC verification
    
    # Preferences
    notify_on_watchlist_match = Column(Boolean, default=True, nullable=False)
    notify_daily_digest = Column(Boolean, default=False, nullable=False)
    notify_premium_drops = Column(Boolean, default=True, nullable=False)
    min_quality_score = Column(Integer, default=0, nullable=False)  # Only notify if score >= this
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="notification_settings")
    
    def __repr__(self) -> str:
        return f"<NotificationSetting(user_id={self.user_id})>"


class Notification(Base):
    """Individual notification record."""
    
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Notification details
    channel = Column(SQLEnum(NotificationChannel), nullable=False)
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False)
    
    # Content
    subject = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    data = Column(Text, nullable=True)  # JSON data for templates
    
    # Delivery info
    recipient = Column(String(500), nullable=True)  # Email, chat_id, webhook_url
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="notifications")
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, channel={self.channel}, status={self.status})>"






