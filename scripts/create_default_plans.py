#!/usr/bin/env python3
"""
Script to create default subscription plans.
Run this after migration: alembic upgrade head
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.subscription import SubscriptionPlan


def create_default_plans():
    """Create default subscription plans."""
    db = SessionLocal()
    
    try:
        # Check if plans already exist
        existing = db.query(SubscriptionPlan).count()
        if existing > 0:
            print("⚠️  Plans already exist. Skipping creation.")
            return
        
        plans = [
            {
                "name": "free",
                "display_name": "Free",
                "description": "Perfect for getting started with domain monitoring",
                "price_monthly": 0,
                "price_yearly": 0,
                "features": [
                    "3 Watchlists",
                    "100 Favorites",
                    "Daily digest email",
                    "Basic filtering",
                    "Community support"
                ],
                "limits": {
                    "watchlist_max": 3,
                    "favorites_max": 100,
                    "api_daily_limit": 0,
                    "api_monthly_limit": 0,
                    "export_enabled": False,
                    "bulk_operations": False,
                    "webhook_enabled": False,
                    "priority_support": False
                },
                "is_active": True,
                "is_featured": False
            },
            {
                "name": "starter",
                "display_name": "Starter",
                "description": "For serious domain investors",
                "price_monthly": 9.00,
                "price_yearly": 90.00,  # 2 months free
                "features": [
                    "20 Watchlists",
                    "1,000 Favorites",
                    "Real-time email/Telegram alerts",
                    "Advanced filtering (regex)",
                    "API access (1,000 req/day)",
                    "Priority support"
                ],
                "limits": {
                    "watchlist_max": 20,
                    "favorites_max": 1000,
                    "api_daily_limit": 1000,
                    "api_monthly_limit": 30000,
                    "export_enabled": False,
                    "bulk_operations": False,
                    "webhook_enabled": False,
                    "priority_support": True
                },
                "is_active": True,
                "is_featured": True
            },
            {
                "name": "pro",
                "display_name": "Pro",
                "description": "For professional domain investors and agencies",
                "price_monthly": 29.00,
                "price_yearly": 290.00,  # 2 months free
                "features": [
                    "Unlimited Watchlists",
                    "Unlimited Favorites",
                    "Multi-channel alerts (Email/Telegram/Discord/Webhook)",
                    "Advanced filtering + regex",
                    "API access (10,000 req/day)",
                    "Bulk export (CSV/Excel)",
                    "Domain history tracking",
                    "Priority support"
                ],
                "limits": {
                    "watchlist_max": -1,  # -1 means unlimited
                    "favorites_max": -1,
                    "api_daily_limit": 10000,
                    "api_monthly_limit": 300000,
                    "export_enabled": True,
                    "bulk_operations": True,
                    "webhook_enabled": True,
                    "priority_support": True
                },
                "is_active": True,
                "is_featured": True
            },
            {
                "name": "business",
                "display_name": "Business",
                "description": "Enterprise features for teams and agencies",
                "price_monthly": 99.00,
                "price_yearly": 990.00,  # 2 months free
                "features": [
                    "All Pro features",
                    "Unlimited API access",
                    "Custom webhook integration",
                    "White-label API (optional)",
                    "Dedicated support",
                    "SLA guarantee",
                    "Custom integrations"
                ],
                "limits": {
                    "watchlist_max": -1,
                    "favorites_max": -1,
                    "api_daily_limit": -1,  # Unlimited
                    "api_monthly_limit": -1,
                    "export_enabled": True,
                    "bulk_operations": True,
                    "webhook_enabled": True,
                    "priority_support": True
                },
                "is_active": True,
                "is_featured": False
            }
        ]
        
        for plan_data in plans:
            plan = SubscriptionPlan(**plan_data)
            db.add(plan)
            print(f"✅ Created plan: {plan.display_name} (${plan.price_monthly}/mo)")
        
        db.commit()
        print("\n🎉 All default plans created successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating plans: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_default_plans()


