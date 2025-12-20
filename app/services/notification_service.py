"""
Notification Service for sending alerts via multiple channels.
"""
import json
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List, Dict, Any
import requests

from sqlalchemy.orm import Session

from app.models.notification import (
    Notification, NotificationSetting, 
    NotificationChannel, NotificationStatus
)
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications via multiple channels."""
    
    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_from: str = "noreply@expireddomain.dev",
        telegram_bot_token: Optional[str] = None
    ):
        """
        Initialize notification service.
        
        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            smtp_from: From email address
            telegram_bot_token: Default Telegram bot token
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.smtp_from = smtp_from
        self.telegram_bot_token = telegram_bot_token
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Send email notification.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            
        Returns:
            True if sent successfully
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_from
            msg["To"] = to_email
            
            # Add plain text
            msg.attach(MIMEText(body, "plain"))
            
            # Add HTML if provided
            if html_body:
                msg.attach(MIMEText(html_body, "html"))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_telegram(
        self,
        chat_id: str,
        message: str,
        bot_token: Optional[str] = None,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        Send Telegram notification.
        
        Args:
            chat_id: Telegram chat ID
            message: Message text
            bot_token: Bot token (uses default if not provided)
            parse_mode: Message parse mode (HTML or Markdown)
            
        Returns:
            True if sent successfully
        """
        token = bot_token or self.telegram_bot_token
        if not token:
            logger.error("No Telegram bot token configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Telegram message sent to {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Telegram to {chat_id}: {e}")
            return False
    
    def send_discord(
        self,
        webhook_url: str,
        message: str,
        username: str = "ExpiredDomain.dev",
        embeds: Optional[List[Dict]] = None
    ) -> bool:
        """
        Send Discord webhook notification.
        
        Args:
            webhook_url: Discord webhook URL
            message: Message content
            username: Bot username
            embeds: Optional embed objects
            
        Returns:
            True if sent successfully
        """
        try:
            payload = {
                "username": username,
                "content": message
            }
            
            if embeds:
                payload["embeds"] = embeds
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info("Discord webhook sent")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Discord webhook: {e}")
            return False
    
    def send_webhook(
        self,
        url: str,
        data: Dict[str, Any],
        secret: Optional[str] = None
    ) -> bool:
        """
        Send generic webhook notification.
        
        Args:
            url: Webhook URL
            data: JSON data to send
            secret: Optional secret for HMAC signature
            
        Returns:
            True if sent successfully
        """
        try:
            headers = {"Content-Type": "application/json"}
            
            if secret:
                import hmac
                import hashlib
                payload = json.dumps(data)
                signature = hmac.new(
                    secret.encode(),
                    payload.encode(),
                    hashlib.sha256
                ).hexdigest()
                headers["X-Signature"] = signature
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Webhook sent to {url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send webhook to {url}: {e}")
            return False
    
    def create_notification(
        self,
        db: Session,
        user_id: int,
        channel: NotificationChannel,
        message: str,
        subject: Optional[str] = None,
        recipient: Optional[str] = None,
        data: Optional[Dict] = None
    ) -> Notification:
        """
        Create a notification record in database.
        
        Args:
            db: Database session
            user_id: User ID
            channel: Notification channel
            message: Message content
            subject: Optional subject (for email)
            recipient: Recipient address
            data: Optional JSON data
            
        Returns:
            Created Notification object
        """
        notification = Notification(
            user_id=user_id,
            channel=channel,
            message=message,
            subject=subject,
            recipient=recipient,
            data=json.dumps(data) if data else None,
            status=NotificationStatus.PENDING
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        return notification
    
    def send_notification(
        self,
        db: Session,
        notification: Notification
    ) -> bool:
        """
        Send a notification and update its status.
        
        Args:
            db: Database session
            notification: Notification object to send
            
        Returns:
            True if sent successfully
        """
        success = False
        error_msg = None
        
        try:
            if notification.channel == NotificationChannel.EMAIL:
                success = self.send_email(
                    notification.recipient,
                    notification.subject or "ExpiredDomain.dev Notification",
                    notification.message
                )
            
            elif notification.channel == NotificationChannel.TELEGRAM:
                success = self.send_telegram(
                    notification.recipient,
                    notification.message
                )
            
            elif notification.channel == NotificationChannel.DISCORD:
                success = self.send_discord(
                    notification.recipient,
                    notification.message
                )
            
            elif notification.channel == NotificationChannel.WEBHOOK:
                data = json.loads(notification.data) if notification.data else {}
                data["message"] = notification.message
                success = self.send_webhook(notification.recipient, data)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Notification send error: {e}")
        
        # Update status
        if success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
        else:
            notification.retry_count += 1
            notification.error_message = error_msg
            if notification.retry_count >= 3:
                notification.status = NotificationStatus.FAILED
        
        db.commit()
        return success
    
    def notify_user(
        self,
        db: Session,
        user: User,
        message: str,
        subject: Optional[str] = None,
        data: Optional[Dict] = None,
        channels: Optional[List[NotificationChannel]] = None
    ) -> List[Notification]:
        """
        Send notification to user via all enabled channels.
        
        Args:
            db: Database session
            user: User to notify
            message: Message content
            subject: Optional subject
            data: Optional data
            channels: Specific channels to use (None = all enabled)
            
        Returns:
            List of created notifications
        """
        notifications = []
        
        # Get user's notification settings
        settings = db.query(NotificationSetting).filter(
            NotificationSetting.user_id == user.id
        ).first()
        
        # Create default settings if not exist
        if not settings:
            settings = NotificationSetting(
                user_id=user.id,
                email_enabled=True,
                email_address=user.email
            )
            db.add(settings)
            db.commit()
        
        # Email notification
        if (not channels or NotificationChannel.EMAIL in channels) and settings.email_enabled:
            email = settings.email_address or user.email
            notification = self.create_notification(
                db, user.id, NotificationChannel.EMAIL,
                message, subject, email, data
            )
            self.send_notification(db, notification)
            notifications.append(notification)
        
        # Telegram notification
        if (not channels or NotificationChannel.TELEGRAM in channels) and settings.telegram_enabled:
            if settings.telegram_chat_id:
                notification = self.create_notification(
                    db, user.id, NotificationChannel.TELEGRAM,
                    message, subject, settings.telegram_chat_id, data
                )
                self.send_notification(db, notification)
                notifications.append(notification)
        
        # Discord notification
        if (not channels or NotificationChannel.DISCORD in channels) and settings.discord_enabled:
            if settings.discord_webhook_url:
                notification = self.create_notification(
                    db, user.id, NotificationChannel.DISCORD,
                    message, subject, settings.discord_webhook_url, data
                )
                self.send_notification(db, notification)
                notifications.append(notification)
        
        # Webhook notification
        if (not channels or NotificationChannel.WEBHOOK in channels) and settings.webhook_enabled:
            if settings.webhook_url:
                notification = self.create_notification(
                    db, user.id, NotificationChannel.WEBHOOK,
                    message, subject, settings.webhook_url, data
                )
                self.send_notification(db, notification)
                notifications.append(notification)
        
        return notifications


def format_domain_alert(
    domains: List[Dict[str, Any]],
    watchlist_name: str
) -> tuple[str, str]:
    """
    Format domain alert message for notifications.
    
    Args:
        domains: List of domain dicts with name, tld, score
        watchlist_name: Name of the watchlist that matched
        
    Returns:
        Tuple of (plain_text, html_text)
    """
    plain_lines = [
        f"🔔 Watchlist Alert: {watchlist_name}",
        f"Found {len(domains)} matching domain(s):",
        ""
    ]
    
    html_lines = [
        f"<h2>🔔 Watchlist Alert: {watchlist_name}</h2>",
        f"<p>Found {len(domains)} matching domain(s):</p>",
        "<ul>"
    ]
    
    for d in domains[:20]:  # Limit to 20
        plain_lines.append(f"• {d['domain']}.{d['tld']} (Score: {d.get('score', 'N/A')})")
        html_lines.append(f"<li><strong>{d['domain']}.{d['tld']}</strong> - Score: {d.get('score', 'N/A')}</li>")
    
    if len(domains) > 20:
        plain_lines.append(f"... and {len(domains) - 20} more")
        html_lines.append(f"<li>... and {len(domains) - 20} more</li>")
    
    html_lines.append("</ul>")
    html_lines.append("<p>Visit <a href='https://expireddomain.dev'>ExpiredDomain.dev</a> for details.</p>")
    
    plain_lines.append("")
    plain_lines.append("Visit https://expireddomain.dev for details.")
    
    return "\n".join(plain_lines), "\n".join(html_lines)






