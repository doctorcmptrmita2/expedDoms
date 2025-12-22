"""
Subscription and payment models for SaaS functionality.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Text, JSON, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class PlanType(str, Enum):
    """Subscription plan types."""
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    BUSINESS = "business"


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"


class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELED = "canceled"


class SubscriptionPlan(Base):
    """Model representing a subscription plan."""
    
    __tablename__ = "subscription_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)  # "free", "starter", "pro", "business"
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Pricing
    price_monthly = Column(Numeric(10, 2), nullable=False, default=0)
    price_yearly = Column(Numeric(10, 2), nullable=True)  # Optional yearly pricing
    
    # Features (JSON)
    features = Column(JSON, nullable=True)  # List of feature strings
    
    # Limits (JSON)
    limits = Column(JSON, nullable=False)  # {
    #   "watchlist_max": 3,
    #   "favorites_max": 100,
    #   "api_daily_limit": 0,
    #   "api_monthly_limit": 0,
    #   "export_enabled": false,
    #   "bulk_operations": false,
    #   "webhook_enabled": false,
    #   "priority_support": false
    # }
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)  # Featured on pricing page
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    subscriptions = relationship("UserSubscription", back_populates="plan")
    
    def __repr__(self) -> str:
        return f"<SubscriptionPlan(name={self.name}, price={self.price_monthly})>"


class UserSubscription(Base):
    """Model representing a user's subscription."""
    
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False, index=True)
    
    # Stripe integration
    stripe_subscription_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    
    # Subscription details
    status = Column(String(50), nullable=False, default=SubscriptionStatus.ACTIVE.value)
    billing_cycle = Column(String(20), nullable=False, default="monthly")  # "monthly" or "yearly"
    
    # Period
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    
    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    canceled_at = Column(DateTime, nullable=True)
    
    # Trial
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="subscription")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription")
    
    def __repr__(self) -> str:
        return f"<UserSubscription(user_id={self.user_id}, plan={self.plan.name if self.plan else None}, status={self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        return (
            self.status == SubscriptionStatus.ACTIVE.value and
            datetime.utcnow() < self.current_period_end
        )
    
    @property
    def is_trialing(self) -> bool:
        """Check if subscription is in trial period."""
        if not self.trial_end:
            return False
        return datetime.utcnow() < self.trial_end


class Payment(Base):
    """Model representing a payment transaction."""
    
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id", ondelete="SET_NULL"), nullable=True, index=True)
    
    # Stripe integration
    stripe_payment_intent_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_invoice_id = Column(String(255), nullable=True, index=True)
    
    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="usd")
    status = Column(String(50), nullable=False, default=PaymentStatus.PENDING.value)
    
    # Metadata
    description = Column(Text, nullable=True)
    payment_metadata = Column(JSON, nullable=True)  # Additional data (renamed from 'metadata' - reserved word)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="payments")
    subscription = relationship("UserSubscription", back_populates="payments")
    
    def __repr__(self) -> str:
        return f"<Payment(user_id={self.user_id}, amount={self.amount}, status={self.status})>"


class ApiKey(Base):
    """Model representing API keys for users."""
    
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Key details
    key_hash = Column(String(255), unique=True, nullable=False, index=True)  # Hashed API key
    name = Column(String(100), nullable=False)  # User-friendly name
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    requests_count = Column(Integer, default=0, nullable=False)
    requests_count_monthly = Column(Integer, default=0, nullable=False)
    last_reset_at = Column(DateTime, nullable=True)  # Monthly reset
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="api_keys")
    
    def __repr__(self) -> str:
        return f"<ApiKey(user_id={self.user_id}, name={self.name}, is_active={self.is_active})>"


