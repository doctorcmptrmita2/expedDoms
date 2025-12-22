"""
Subscription service for managing user subscriptions and plan limits.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.user import User
from app.models.subscription import (
    SubscriptionPlan, UserSubscription, Payment, PlanType, SubscriptionStatus
)


class SubscriptionService:
    """Service for managing subscriptions and plan limits."""
    
    def __init__(self, db: Session):
        """
        Initialize subscription service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_user_plan(self, user: User) -> SubscriptionPlan:
        """
        Get user's current subscription plan.
        
        Args:
            user: User object
            
        Returns:
            SubscriptionPlan object (defaults to FREE plan)
        """
        # Check for active subscription
        subscription = self.db.query(UserSubscription).filter(
            and_(
                UserSubscription.user_id == user.id,
                UserSubscription.status == SubscriptionStatus.ACTIVE.value,
                UserSubscription.current_period_end > datetime.utcnow()
            )
        ).first()
        
        if subscription and subscription.plan:
            return subscription.plan
        
        # Default to FREE plan
        free_plan = self.db.query(SubscriptionPlan).filter(
            SubscriptionPlan.name == PlanType.FREE.value
        ).first()
        
        if not free_plan:
            # Create default FREE plan if it doesn't exist
            free_plan = SubscriptionPlan(
                name=PlanType.FREE.value,
                display_name="Free",
                description="Free tier with basic features",
                price_monthly=0,
                limits={
                    "watchlist_max": 3,
                    "favorites_max": 100,
                    "api_daily_limit": 0,
                    "api_monthly_limit": 0,
                    "export_enabled": False,
                    "bulk_operations": False,
                    "webhook_enabled": False,
                    "priority_support": False
                },
                features=[
                    "3 Watchlists",
                    "100 Favorites",
                    "Daily digest email",
                    "Basic filtering"
                ],
                is_active=True
            )
            self.db.add(free_plan)
            self.db.commit()
            self.db.refresh(free_plan)
        
        return free_plan
    
    def get_user_subscription(self, user: User) -> Optional[UserSubscription]:
        """
        Get user's active subscription.
        
        Args:
            user: User object
            
        Returns:
            UserSubscription or None
        """
        return self.db.query(UserSubscription).filter(
            and_(
                UserSubscription.user_id == user.id,
                UserSubscription.status == SubscriptionStatus.ACTIVE.value,
                UserSubscription.current_period_end > datetime.utcnow()
            )
        ).first()
    
    def check_plan_limit(self, user: User, limit_name: str) -> tuple[bool, int, int | None]:
        """
        Check if user has reached a plan limit.
        
        Args:
            user: User object
            limit_name: Name of the limit to check (e.g., "watchlist_max", "favorites_max")
            
        Returns:
            Tuple of (is_within_limit, current_usage, max_allowed)
        """
        try:
            plan = self.get_user_plan(user)
            # Handle JSON field - it might be None or already a dict
            if plan.limits is None:
                limits = {}
            elif isinstance(plan.limits, dict):
                limits = plan.limits
            else:
                # If it's a string, try to parse it (shouldn't happen with JSON field)
                import json
                limits = json.loads(plan.limits) if isinstance(plan.limits, str) else {}
            
            max_allowed = limits.get(limit_name, 0)
        except Exception as e:
            # Fallback to safe defaults
            import logging
            logging.getLogger(__name__).error(f"Error checking plan limit: {e}")
            return (True, 0, None)
        
        # Get current usage based on limit type
        try:
            if limit_name == "watchlist_max":
                from app.models.user import UserWatchlist
                current_usage = self.db.query(UserWatchlist).filter(
                    UserWatchlist.user_id == user.id,
                    UserWatchlist.is_active == True
                ).count()
            elif limit_name == "favorites_max":
                from app.models.user import UserFavorite
                current_usage = self.db.query(UserFavorite).filter(
                    UserFavorite.user_id == user.id
                ).count()
            elif limit_name == "api_daily_limit":
                from app.models.subscription import ApiKey
                # Get API requests for today
                today = datetime.utcnow().date()
                current_usage = self.db.query(ApiKey).filter(
                    and_(
                        ApiKey.user_id == user.id,
                        ApiKey.is_active == True,
                        func.date(ApiKey.last_used_at) == today
                    )
                ).count()  # This is simplified - should track actual API requests
            else:
                current_usage = 0
            
            is_within_limit = current_usage < max_allowed if max_allowed > 0 else True
            
            return (is_within_limit, current_usage, max_allowed)
        except Exception as e:
            # Fallback to safe defaults
            import logging
            logging.getLogger(__name__).error(f"Error in check_plan_limit: {e}")
            return (True, 0, None)
    
    def can_access_feature(self, user: User, feature_name: str) -> bool:
        """
        Check if user can access a feature based on their plan.
        
        Args:
            user: User object
            feature_name: Name of the feature (e.g., "export_enabled", "webhook_enabled")
            
        Returns:
            True if user can access the feature
        """
        try:
            plan = self.get_user_plan(user)
            # Handle JSON field - it might be None or already a dict
            if plan.limits is None:
                limits = {}
            elif isinstance(plan.limits, dict):
                limits = plan.limits
            else:
                # If it's a string, try to parse it (shouldn't happen with JSON field)
                import json
                limits = json.loads(plan.limits) if isinstance(plan.limits, str) else {}
            
            # Admin users have access to all features
            if user.is_admin:
                return True
            
            return limits.get(feature_name, False)
        except Exception as e:
            # Fallback to safe defaults
            import logging
            logging.getLogger(__name__).error(f"Error checking feature access: {e}")
            return False
    
    def create_subscription(
        self,
        user: User,
        plan: SubscriptionPlan,
        stripe_subscription_id: Optional[str] = None,
        stripe_customer_id: Optional[str] = None,
        billing_cycle: str = "monthly"
    ) -> UserSubscription:
        """
        Create a new subscription for a user.
        
        Args:
            user: User object
            plan: SubscriptionPlan object
            stripe_subscription_id: Stripe subscription ID
            stripe_customer_id: Stripe customer ID
            billing_cycle: "monthly" or "yearly"
            
        Returns:
            Created UserSubscription object
        """
        # Cancel existing subscription if any
        existing = self.get_user_subscription(user)
        if existing:
            existing.status = SubscriptionStatus.CANCELED.value
            existing.canceled_at = datetime.utcnow()
        
        # Calculate period dates
        now = datetime.utcnow()
        if billing_cycle == "yearly":
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)
        
        # Create new subscription
        subscription = UserSubscription(
            user_id=user.id,
            plan_id=plan.id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            status=SubscriptionStatus.ACTIVE.value,
            billing_cycle=billing_cycle,
            current_period_start=now,
            current_period_end=period_end
        )
        
        self.db.add(subscription)
        
        # Update user premium status
        if plan.name != PlanType.FREE.value:
            user.is_premium = True
        
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    def cancel_subscription(self, user: User, cancel_at_period_end: bool = True) -> bool:
        """
        Cancel user's subscription.
        
        Args:
            user: User object
            cancel_at_period_end: If True, cancel at end of period; otherwise cancel immediately
            
        Returns:
            True if canceled successfully
        """
        subscription = self.get_user_subscription(user)
        
        if not subscription:
            return False
        
        if cancel_at_period_end:
            subscription.cancel_at_period_end = True
        else:
            subscription.status = SubscriptionStatus.CANCELED.value
            subscription.canceled_at = datetime.utcnow()
            
            # Downgrade to free plan
            user.is_premium = False
        
        self.db.commit()
        return True
    
    def get_plan_features(self, plan: SubscriptionPlan) -> Dict[str, Any]:
        """
        Get formatted plan features for display.
        
        Args:
            plan: SubscriptionPlan object
            
        Returns:
            Dictionary with plan information
        """
        limits = plan.limits or {}
        
        return {
            "name": plan.display_name,
            "price_monthly": float(plan.price_monthly),
            "price_yearly": float(plan.price_yearly) if plan.price_yearly else None,
            "features": plan.features or [],
            "limits": {
                "watchlist": limits.get("watchlist_max", 0),
                "favorites": limits.get("favorites_max", 0),
                "api_daily": limits.get("api_daily_limit", 0),
                "export": limits.get("export_enabled", False),
                "webhook": limits.get("webhook_enabled", False),
                "bulk_ops": limits.get("bulk_operations", False),
                "priority_support": limits.get("priority_support", False)
            }
        }


def get_subscription_service(db: Session) -> SubscriptionService:
    """
    Get subscription service instance.
    
    Args:
        db: Database session
        
    Returns:
        SubscriptionService instance
    """
    return SubscriptionService(db)

