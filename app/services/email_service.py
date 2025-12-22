"""
Email service for sending verification and password reset emails.
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.auth_token import EmailVerificationToken, PasswordResetToken
from app.services.notification_service import NotificationService
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending verification and password reset emails."""
    
    def __init__(self, db: Session):
        self.db = db
        settings = get_settings()
        
        # Initialize notification service for email sending
        self.notification_service = NotificationService(
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            smtp_user=settings.SMTP_USER,
            smtp_password=settings.SMTP_PASSWORD,
            smtp_from=settings.SMTP_FROM
        )
        
        self.app_url = settings.APP_URL
    
    def send_verification_email(self, user: User, token: EmailVerificationToken) -> bool:
        """
        Send email verification email.
        
        Args:
            user: User to send email to
            token: Verification token
            
        Returns:
            True if sent successfully
        """
        verification_url = f"{self.app_url}/auth/verify-email?token={token.token}"
        
        subject = "Email Verification - ExpiredDomain.dev"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #00f5ff; color: #000; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #888; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Email Verification</h2>
                <p>Hello {user.username},</p>
                <p>Thank you for registering with ExpiredDomain.dev!</p>
                <p>Please click the button below to verify your email address:</p>
                <p><a href="{verification_url}" class="button">Verify Email</a></p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{verification_url}</p>
                <p>This link will expire in 24 hours.</p>
                <div class="footer">
                    <p>If you didn't create an account, please ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Email Verification
        
        Hello {user.username},
        
        Thank you for registering with ExpiredDomain.dev!
        
        Please verify your email address by clicking this link:
        {verification_url}
        
        This link will expire in 24 hours.
        
        If you didn't create an account, please ignore this email.
        """
        
        return self.notification_service.send_email(
            to_email=user.email,
            subject=subject,
            body=text_body,
            html_body=html_body
        )
    
    def send_password_reset_email(self, user: User, token: PasswordResetToken) -> bool:
        """
        Send password reset email.
        
        Args:
            user: User to send email to
            token: Password reset token
            
        Returns:
            True if sent successfully
        """
        reset_url = f"{self.app_url}/auth/reset-password?token={token.token}"
        
        subject = "Password Reset - ExpiredDomain.dev"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #00f5ff; color: #000; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #888; }}
                .warning {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Password Reset Request</h2>
                <p>Hello {user.username},</p>
                <p>We received a request to reset your password for your ExpiredDomain.dev account.</p>
                <p>Click the button below to reset your password:</p>
                <p><a href="{reset_url}" class="button">Reset Password</a></p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{reset_url}</p>
                <div class="warning">
                    <strong>⚠️ Important:</strong> This link will expire in 1 hour. If you didn't request a password reset, please ignore this email.
                </div>
                <div class="footer">
                    <p>If you didn't request this, please ignore this email. Your password will remain unchanged.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Password Reset Request
        
        Hello {user.username},
        
        We received a request to reset your password for your ExpiredDomain.dev account.
        
        Click this link to reset your password:
        {reset_url}
        
        ⚠️ Important: This link will expire in 1 hour.
        
        If you didn't request a password reset, please ignore this email. Your password will remain unchanged.
        """
        
        return self.notification_service.send_email(
            to_email=user.email,
            subject=subject,
            body=text_body,
            html_body=html_body
        )


