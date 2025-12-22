"""
SaaS Admin Dashboard - Comprehensive management panel.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.core.database import get_db
from app.models.user import User
from app.models.subscription import SubscriptionPlan, UserSubscription, Payment, ApiKey
from app.models.drop import DroppedDomain
from app.models.tld import Tld
from app.models.notification import Notification
from app.web.auth_web import get_current_user_from_cookie

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def require_admin(request: Request, db: Session = Depends(get_db)):
    """Dependency to require admin access."""
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/auth/login?next=/admin/dashboard", status_code=302)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """Main admin dashboard with overview statistics."""
    admin_user = require_admin(request, db)
    """
    Main admin dashboard with overview statistics.
    """
    # Calculate statistics
    stats = {
        # User statistics
        "total_users": db.query(func.count(User.id)).scalar() or 0,
        "active_users": db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0,
        "premium_users": db.query(func.count(User.id)).filter(User.is_premium == True).scalar() or 0,
        "new_users_today": db.query(func.count(User.id)).filter(
            func.date(User.created_at) == datetime.utcnow().date()
        ).scalar() or 0,
        "new_users_week": db.query(func.count(User.id)).filter(
            User.created_at >= datetime.utcnow() - timedelta(days=7)
        ).scalar() or 0,
        
        # Subscription statistics
        "total_subscriptions": db.query(func.count(UserSubscription.id)).scalar() or 0,
        "active_subscriptions": db.query(func.count(UserSubscription.id)).filter(
            UserSubscription.status == "active"
        ).scalar() or 0,
        "mrr": db.query(func.sum(SubscriptionPlan.price_monthly)).join(
            UserSubscription, SubscriptionPlan.id == UserSubscription.plan_id
        ).filter(UserSubscription.status == "active").scalar() or 0,
        
        # Domain statistics
        "total_domains": db.query(func.count(DroppedDomain.id)).scalar() or 0,
        "domains_today": db.query(func.count(DroppedDomain.id)).filter(
            DroppedDomain.drop_date == datetime.utcnow().date()
        ).scalar() or 0,
        "total_tlds": db.query(func.count(Tld.id)).filter(Tld.is_active == True).scalar() or 0,
        
        # Payment statistics
        "total_revenue": db.query(func.sum(Payment.amount)).filter(
            Payment.status == "succeeded"
        ).scalar() or 0,
        "revenue_month": db.query(func.sum(Payment.amount)).filter(
            and_(
                Payment.status == "succeeded",
                Payment.created_at >= datetime.utcnow() - timedelta(days=30)
            )
        ).scalar() or 0,
        
        # API statistics
        "total_api_keys": db.query(func.count(ApiKey.id)).scalar() or 0,
        "active_api_keys": db.query(func.count(ApiKey.id)).filter(ApiKey.is_active == True).scalar() or 0,
    }
    
    # Recent activity
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(10).all()
    recent_payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(10).all()
    
    # Subscription breakdown by plan
    plan_stats = db.query(
        SubscriptionPlan.name,
        SubscriptionPlan.display_name,
        func.count(UserSubscription.id).label("count")
    ).join(
        UserSubscription, SubscriptionPlan.id == UserSubscription.plan_id
    ).filter(
        UserSubscription.status == "active"
    ).group_by(
        SubscriptionPlan.id, SubscriptionPlan.name, SubscriptionPlan.display_name
    ).all()
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "stats": stats,
        "recent_users": recent_users,
        "recent_payments": recent_payments,
        "plan_stats": plan_stats,
    })


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None)
):
    """User management page."""
    admin_user = require_admin(request, db)
    """
    User management page.
    """
    query = db.query(User)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
        )
    
    if status_filter == "active":
        query = query.filter(User.is_active == True)
    elif status_filter == "inactive":
        query = query.filter(User.is_active == False)
    elif status_filter == "premium":
        query = query.filter(User.is_premium == True)
    elif status_filter == "admin":
        query = query.filter(User.is_admin == True)
    
    # Pagination
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "users": users,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "search": search,
        "status_filter": status_filter,
    })


@router.get("/admin/subscriptions", response_class=HTMLResponse)
def admin_subscriptions(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    status_filter: Optional[str] = Query(None),
    plan_filter: Optional[str] = Query(None)
):
    """Subscription management page."""
    admin_user = require_admin(request, db)
    """
    Subscription management page.
    """
    query = db.query(UserSubscription).join(User).join(SubscriptionPlan)
    
    # Apply filters
    if status_filter:
        query = query.filter(UserSubscription.status == status_filter)
    
    if plan_filter:
        query = query.filter(SubscriptionPlan.name == plan_filter)
    
    # Pagination
    total = query.count()
    subscriptions = query.order_by(UserSubscription.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    # Get all plans for filter dropdown
    plans = db.query(SubscriptionPlan).filter(SubscriptionPlan.is_active == True).all()
    
    return templates.TemplateResponse("admin/subscriptions.html", {
        "request": request,
        "subscriptions": subscriptions,
        "plans": plans,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "status_filter": status_filter,
        "plan_filter": plan_filter,
    })


@router.get("/admin/plans", response_class=HTMLResponse)
def admin_plans(
    request: Request,
    db: Session = Depends(get_db)
):
    """Subscription plans management page."""
    admin_user = require_admin(request, db)
    """
    Subscription plans management page.
    """
    plans = db.query(SubscriptionPlan).order_by(SubscriptionPlan.price_monthly).all()
    
    # Get subscription counts for each plan
    for plan in plans:
        plan.active_count = db.query(func.count(UserSubscription.id)).filter(
            and_(
                UserSubscription.plan_id == plan.id,
                UserSubscription.status == "active"
            )
        ).scalar() or 0
    
    return templates.TemplateResponse("admin/plans.html", {
        "request": request,
        "plans": plans,
    })


@router.get("/admin/payments", response_class=HTMLResponse)
def admin_payments(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    status_filter: Optional[str] = Query(None)
):
    """Payment history page."""
    admin_user = require_admin(request, db)
    """
    Payment history page.
    """
    query = db.query(Payment).join(User)
    
    # Apply filters
    if status_filter:
        query = query.filter(Payment.status == status_filter)
    
    # Pagination
    total = query.count()
    payments = query.order_by(Payment.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return templates.TemplateResponse("admin/payments.html", {
        "request": request,
        "payments": payments,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "status_filter": status_filter,
    })


@router.get("/admin/analytics", response_class=HTMLResponse)
def admin_analytics(
    request: Request,
    db: Session = Depends(get_db)
):
    """Analytics and reporting page."""
    admin_user = require_admin(request, db)
    """
    Analytics and reporting page.
    """
    # Revenue over time (last 30 days)
    revenue_data = []
    for i in range(30):
        date = datetime.utcnow().date() - timedelta(days=29-i)
        revenue = db.query(func.sum(Payment.amount)).filter(
            and_(
                Payment.status == "succeeded",
                func.date(Payment.created_at) == date
            )
        ).scalar() or 0
        revenue_data.append({
            "date": date.isoformat(),
            "revenue": float(revenue)
        })
    
    # User growth (last 30 days)
    user_growth = []
    for i in range(30):
        date = datetime.utcnow().date() - timedelta(days=29-i)
        count = db.query(func.count(User.id)).filter(
            func.date(User.created_at) == date
        ).scalar() or 0
        user_growth.append({
            "date": date.isoformat(),
            "count": count
        })
    
    # Subscription churn
    canceled_this_month = db.query(func.count(UserSubscription.id)).filter(
        and_(
            UserSubscription.status == "canceled",
            UserSubscription.canceled_at >= datetime.utcnow() - timedelta(days=30)
        )
    ).scalar() or 0
    
    return templates.TemplateResponse("admin/analytics.html", {
        "request": request,
        "revenue_data": revenue_data,
        "user_growth": user_growth,
        "canceled_this_month": canceled_this_month,
    })


