"""
API endpoints for subscription management.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.subscription import SubscriptionPlan, UserSubscription
from app.services.subscription_service import SubscriptionService, get_subscription_service
from app.services.stripe_service import StripeService, get_stripe_service
from app.web.auth_web import get_current_user_from_cookie
from fastapi import Request

router = APIRouter()


# ============== Schemas ==============

class PlanResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str]
    price_monthly: float
    price_yearly: Optional[float]
    features: Optional[list]
    limits: dict
    
    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    id: int
    plan: PlanResponse
    status: str
    billing_cycle: str
    current_period_start: str
    current_period_end: str
    cancel_at_period_end: bool
    
    class Config:
        from_attributes = True


class CheckoutSessionResponse(BaseModel):
    session_id: str
    url: str


# ============== Endpoints ==============

@router.get("/plans", response_model=list[PlanResponse])
def get_plans(db: Session = Depends(get_db)):
    """
    Get all available subscription plans.
    """
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True
    ).order_by(SubscriptionPlan.price_monthly).all()
    
    return plans


@router.get("/plans/{plan_name}", response_model=PlanResponse)
def get_plan(plan_name: str, db: Session = Depends(get_db)):
    """
    Get a specific subscription plan.
    """
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.name == plan_name,
        SubscriptionPlan.is_active == True
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return plan


@router.get("/subscription", response_model=Optional[SubscriptionResponse])
def get_my_subscription(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get current user's subscription.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    service = get_subscription_service(db)
    subscription = service.get_user_subscription(user)
    
    if not subscription:
        return None
    
    return subscription


@router.post("/checkout", response_model=CheckoutSessionResponse)
def create_checkout_session(
    request: Request,
    plan_name: str = Query(...),
    billing_cycle: str = Query("monthly", regex="^(monthly|yearly)$"),
    db: Session = Depends(get_db)
):
    """
    Create Stripe checkout session for subscription.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Get plan
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.name == plan_name,
        SubscriptionPlan.is_active == True
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Create checkout session
    stripe_service = get_stripe_service(db)
    session = stripe_service.create_checkout_session(
        user=user,
        plan=plan,
        billing_cycle=billing_cycle
    )
    
    if not session:
        raise HTTPException(status_code=500, detail="Failed to create checkout session. Stripe may not be configured.")
    
    return session


@router.post("/cancel")
def cancel_subscription(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Cancel current user's subscription.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    service = get_subscription_service(db)
    subscription = service.get_user_subscription(user)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    # Cancel via Stripe if available
    stripe_service = get_stripe_service(db)
    if subscription.stripe_subscription_id:
        stripe_service.cancel_subscription(subscription)
    
    # Cancel in database
    service.cancel_subscription(user, cancel_at_period_end=True)
    
    return {"message": "Subscription will be canceled at the end of the billing period"}


