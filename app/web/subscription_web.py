"""
Web routes for subscription management.
"""
from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.subscription import SubscriptionPlan
from app.services.subscription_service import SubscriptionService, get_subscription_service
from app.services.stripe_service import StripeService, get_stripe_service
from app.web.auth_web import get_current_user_from_cookie

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request, db: Session = Depends(get_db)):
    """
    Pricing page with subscription plans.
    """
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True
    ).order_by(SubscriptionPlan.price_monthly).all()
    
    # Get current user's subscription if logged in
    user = get_current_user_from_cookie(request, db)
    current_subscription = None
    if user:
        service = get_subscription_service(db)
        current_subscription = service.get_user_subscription(user)
    
    return templates.TemplateResponse("pricing.html", {
        "request": request,
        "plans": plans,
        "current_subscription": current_subscription,
        "user": user
    })


@router.get("/subscription/success", response_class=HTMLResponse)
def subscription_success(
    request: Request,
    session_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Subscription success page after Stripe checkout.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    service = get_subscription_service(db)
    subscription = service.get_user_subscription(user)
    
    return templates.TemplateResponse("subscription_success.html", {
        "request": request,
        "subscription": subscription,
        "session_id": session_id
    })


@router.get("/subscription/cancel", response_class=HTMLResponse)
def subscription_cancel(request: Request):
    """
    Subscription cancellation page.
    """
    return templates.TemplateResponse("subscription_cancel.html", {
        "request": request
    })


@router.post("/subscription/checkout", response_class=RedirectResponse)
def create_checkout(
    request: Request,
    plan_name: str = Form(...),
    billing_cycle: str = Form("monthly"),
    db: Session = Depends(get_db)
):
    """
    Create Stripe checkout session and redirect.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/auth/login?next=/pricing", status_code=302)
    
    # Get plan
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.name == plan_name,
        SubscriptionPlan.is_active == True
    ).first()
    
    if not plan:
        return RedirectResponse(url="/pricing?error=plan_not_found", status_code=302)
    
    # Create checkout session
    stripe_service = get_stripe_service(db)
    session = stripe_service.create_checkout_session(
        user=user,
        plan=plan,
        billing_cycle=billing_cycle,
        success_url=f"{request.base_url}subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{request.base_url}subscription/cancel"
    )
    
    if not session:
        return RedirectResponse(url="/pricing?error=checkout_failed", status_code=302)
    
    # Redirect to Stripe Checkout
    return RedirectResponse(url=session['url'], status_code=303)


@router.get("/subscription/manage", response_class=HTMLResponse)
def subscription_manage(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Subscription management page.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/auth/login?next=/subscription/manage", status_code=302)
    
    service = get_subscription_service(db)
    subscription = service.get_user_subscription(user)
    plan = service.get_user_plan(user)
    plan_info = service.get_plan_features(plan)
    
    return templates.TemplateResponse("subscription_manage.html", {
        "request": request,
        "user": user,
        "subscription": subscription,
        "plan": plan,
        "plan_info": plan_info
    })


