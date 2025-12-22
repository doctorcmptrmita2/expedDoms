"""
Middleware and decorators for enforcing subscription plan limits.
"""
from functools import wraps
from typing import Callable
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.subscription_service import SubscriptionService, get_subscription_service
from app.web.auth_web import get_current_user_from_cookie
from fastapi import Request


def require_plan_feature(feature_name: str):
    """
    Decorator to require a specific plan feature.
    
    Usage:
        @require_plan_feature("export_enabled")
        def export_domains(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and db from kwargs
            request = None
            db = None
            
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                elif isinstance(arg, Session):
                    db = arg
            
            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if not db:
                for key, value in kwargs.items():
                    if isinstance(value, Session):
                        db = value
                        break
            
            if not request or not db:
                raise HTTPException(status_code=500, detail="Request or DB not found")
            
            # Get current user
            user = get_current_user_from_cookie(request, db)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Check feature access
            service = get_subscription_service(db)
            if not service.can_access_feature(user, feature_name):
                plan = service.get_user_plan(user)
                raise HTTPException(
                    status_code=403,
                    detail=f"Feature '{feature_name}' requires a higher plan. Current plan: {plan.display_name}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_plan_limit(limit_name: str):
    """
    Decorator to check plan limit before executing function.
    
    Usage:
        @check_plan_limit("watchlist_max")
        def create_watchlist(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and db from kwargs
            request = None
            db = None
            
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                elif isinstance(arg, Session):
                    db = arg
            
            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if not db:
                for key, value in kwargs.items():
                    if isinstance(value, Session):
                        db = value
                        break
            
            if not request or not db:
                raise HTTPException(status_code=500, detail="Request or DB not found")
            
            # Get current user
            user = get_current_user_from_cookie(request, db)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Check limit
            service = get_subscription_service(db)
            is_within_limit, current_usage, max_allowed = service.check_plan_limit(user, limit_name)
            
            if not is_within_limit:
                plan = service.get_user_plan(user)
                raise HTTPException(
                    status_code=403,
                    detail=f"Plan limit reached for '{limit_name}'. Current: {current_usage}/{max_allowed}. Upgrade to increase limits."
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_user_plan_info(user: User, db: Session) -> dict:
    """
    Get user's plan information for use in templates/endpoints.
    
    Args:
        user: User object
        db: Database session
        
    Returns:
        Dictionary with plan information
    """
    service = get_subscription_service(db)
    plan = service.get_user_plan(user)
    subscription = service.get_user_subscription(user)
    
    return {
        "plan": plan,
        "subscription": subscription,
        "is_premium": user.is_premium,
        "limits": {
            "watchlist": service.check_plan_limit(user, "watchlist_max"),
            "favorites": service.check_plan_limit(user, "favorites_max"),
            "api_daily": service.check_plan_limit(user, "api_daily_limit"),
        },
        "features": {
            "export": service.can_access_feature(user, "export_enabled"),
            "webhook": service.can_access_feature(user, "webhook_enabled"),
            "bulk_ops": service.can_access_feature(user, "bulk_operations"),
            "priority_support": service.can_access_feature(user, "priority_support"),
        }
    }


