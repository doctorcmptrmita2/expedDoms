"""
API endpoints for notification management.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models.user import User
from app.models.notification import (
    NotificationSetting, Notification,
    NotificationChannel, NotificationStatus
)
from app.api.v1.auth import get_current_user_required

router = APIRouter()


# ============== Schemas ==============

class NotificationSettingsUpdate(BaseModel):
    """Schema for updating notification settings."""
    email_enabled: Optional[bool] = None
    email_address: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    discord_enabled: Optional[bool] = None
    discord_webhook_url: Optional[str] = None
    webhook_enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    notify_on_watchlist_match: Optional[bool] = None
    notify_daily_digest: Optional[bool] = None
    notify_premium_drops: Optional[bool] = None
    min_quality_score: Optional[int] = None


class NotificationSettingsResponse(BaseModel):
    """Schema for notification settings response."""
    id: int
    email_enabled: bool
    email_address: Optional[str]
    telegram_enabled: bool
    telegram_chat_id: Optional[str]
    discord_enabled: bool
    discord_webhook_url: Optional[str]
    webhook_enabled: bool
    webhook_url: Optional[str]
    notify_on_watchlist_match: bool
    notify_daily_digest: bool
    notify_premium_drops: bool
    min_quality_score: int
    
    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    """Schema for notification response."""
    id: int
    channel: str
    status: str
    subject: Optional[str]
    message: str
    recipient: Optional[str]
    created_at: str
    sent_at: Optional[str]
    
    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Schema for notification list response."""
    total: int
    results: List[NotificationResponse]


# ============== Endpoints ==============

@router.get("/settings", response_model=NotificationSettingsResponse)
def get_notification_settings(
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Get current user's notification settings.
    """
    settings = db.query(NotificationSetting).filter(
        NotificationSetting.user_id == current_user.id
    ).first()
    
    # Create default settings if not exist
    if not settings:
        settings = NotificationSetting(
            user_id=current_user.id,
            email_enabled=True,
            email_address=current_user.email
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    return NotificationSettingsResponse.model_validate(settings)


@router.put("/settings", response_model=NotificationSettingsResponse)
def update_notification_settings(
    updates: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Update notification settings.
    """
    settings = db.query(NotificationSetting).filter(
        NotificationSetting.user_id == current_user.id
    ).first()
    
    if not settings:
        settings = NotificationSetting(user_id=current_user.id)
        db.add(settings)
    
    # Update fields
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    
    return NotificationSettingsResponse.model_validate(settings)


@router.get("/history", response_model=NotificationListResponse)
def get_notification_history(
    status_filter: Optional[str] = None,
    channel_filter: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Get notification history for current user.
    """
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id
    )
    
    if status_filter:
        try:
            status_enum = NotificationStatus(status_filter)
            query = query.filter(Notification.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status filter")
    
    if channel_filter:
        try:
            channel_enum = NotificationChannel(channel_filter)
            query = query.filter(Notification.channel == channel_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid channel filter")
    
    total = query.count()
    notifications = query.order_by(desc(Notification.created_at)).limit(limit).all()
    
    results = [
        NotificationResponse(
            id=n.id,
            channel=n.channel.value,
            status=n.status.value,
            subject=n.subject,
            message=n.message[:200] + "..." if len(n.message) > 200 else n.message,
            recipient=n.recipient,
            created_at=n.created_at.isoformat(),
            sent_at=n.sent_at.isoformat() if n.sent_at else None
        )
        for n in notifications
    ]
    
    return NotificationListResponse(total=total, results=results)


@router.post("/test/{channel}")
def send_test_notification(
    channel: str,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Send a test notification via specified channel.
    """
    from app.services.notification_service import NotificationService
    
    try:
        channel_enum = NotificationChannel(channel)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel")
    
    settings = db.query(NotificationSetting).filter(
        NotificationSetting.user_id == current_user.id
    ).first()
    
    if not settings:
        raise HTTPException(status_code=400, detail="No notification settings found")
    
    service = NotificationService()
    
    test_message = f"🔔 Test notification from ExpiredDomain.dev\n\nThis is a test message to verify your {channel} notifications are working correctly."
    
    success = False
    error = None
    
    try:
        if channel_enum == NotificationChannel.EMAIL:
            email = settings.email_address or current_user.email
            success = service.send_email(
                email,
                "Test Notification - ExpiredDomain.dev",
                test_message
            )
        
        elif channel_enum == NotificationChannel.TELEGRAM:
            if not settings.telegram_chat_id:
                raise HTTPException(status_code=400, detail="Telegram chat ID not configured")
            success = service.send_telegram(
                settings.telegram_chat_id,
                test_message
            )
        
        elif channel_enum == NotificationChannel.DISCORD:
            if not settings.discord_webhook_url:
                raise HTTPException(status_code=400, detail="Discord webhook URL not configured")
            success = service.send_discord(
                settings.discord_webhook_url,
                test_message
            )
        
        elif channel_enum == NotificationChannel.WEBHOOK:
            if not settings.webhook_url:
                raise HTTPException(status_code=400, detail="Webhook URL not configured")
            success = service.send_webhook(
                settings.webhook_url,
                {"type": "test", "message": test_message}
            )
    
    except Exception as e:
        error = str(e)
    
    if success:
        return {"success": True, "message": f"Test notification sent via {channel}"}
    else:
        return {"success": False, "message": f"Failed to send test notification", "error": error}


@router.get("/channels")
def get_available_channels():
    """
    Get list of available notification channels.
    """
    return {
        "channels": [
            {
                "id": "email",
                "name": "Email",
                "description": "Receive notifications via email",
                "icon": "mail",
                "requires_config": False
            },
            {
                "id": "telegram",
                "name": "Telegram",
                "description": "Receive notifications via Telegram bot",
                "icon": "send",
                "requires_config": True,
                "config_fields": ["telegram_chat_id"]
            },
            {
                "id": "discord",
                "name": "Discord",
                "description": "Receive notifications via Discord webhook",
                "icon": "message-circle",
                "requires_config": True,
                "config_fields": ["discord_webhook_url"]
            },
            {
                "id": "webhook",
                "name": "Custom Webhook",
                "description": "Send notifications to a custom URL",
                "icon": "link",
                "requires_config": True,
                "config_fields": ["webhook_url", "webhook_secret"]
            }
        ]
    }








