"""
Stripe service for payment and subscription management.
"""
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None

from app.core.config import get_settings
from app.models.user import User
from app.models.subscription import SubscriptionPlan, UserSubscription, Payment, SubscriptionStatus, PaymentStatus


class StripeService:
    """Service for Stripe payment and subscription operations."""
    
    def __init__(self, db: Session):
        """
        Initialize Stripe service.
        
        Args:
            db: Database session
        """
        self.db = db
        settings = get_settings()
        
        # Initialize Stripe
        if STRIPE_AVAILABLE:
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
            self.stripe_available = bool(stripe.api_key)
        else:
            self.stripe_available = False
    
    def create_checkout_session(
        self,
        user: User,
        plan: SubscriptionPlan,
        billing_cycle: str = "monthly",
        success_url: str = None,
        cancel_url: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create Stripe Checkout session for subscription.
        
        Args:
            user: User object
            plan: SubscriptionPlan object
            billing_cycle: "monthly" or "yearly"
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL
            
        Returns:
            Checkout session dict or None if Stripe not available
        """
        if not self.stripe_available:
            return None
        
        # Determine price
        if billing_cycle == "yearly" and plan.price_yearly:
            price_amount = int(float(plan.price_yearly) * 100)  # Convert to cents
        else:
            price_amount = int(float(plan.price_monthly) * 100)
        
        try:
            # Create or retrieve Stripe customer
            customer_id = self.get_or_create_customer(user)
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f"{plan.display_name} Plan",
                            'description': plan.description or f"Subscription to {plan.display_name} plan"
                        },
                        'unit_amount': price_amount,
                        'recurring': {
                            'interval': 'month' if billing_cycle == "monthly" else 'year'
                        }
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url or f"{os.getenv('APP_URL', 'http://localhost:8000')}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url or f"{os.getenv('APP_URL', 'http://localhost:8000')}/subscription/cancel",
                metadata={
                    'user_id': str(user.id),
                    'plan_id': str(plan.id),
                    'billing_cycle': billing_cycle
                }
            )
            
            return {
                'session_id': session.id,
                'url': session.url
            }
        except Exception as e:
            print(f"Stripe checkout error: {e}")
            return None
    
    def get_or_create_customer(self, user: User) -> Optional[str]:
        """
        Get or create Stripe customer for user.
        
        Args:
            user: User object
            
        Returns:
            Stripe customer ID or None
        """
        if not self.stripe_available:
            return None
        
        # Check if user already has a Stripe customer ID
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.user_id == user.id,
            UserSubscription.stripe_customer_id.isnot(None)
        ).first()
        
        if subscription and subscription.stripe_customer_id:
            return subscription.stripe_customer_id
        
        # Create new Stripe customer
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.full_name or user.username,
                metadata={
                    'user_id': str(user.id),
                    'username': user.username
                }
            )
            return customer.id
        except Exception as e:
            print(f"Stripe customer creation error: {e}")
            return None
    
    def handle_webhook(self, payload: bytes, signature: str) -> bool:
        """
        Handle Stripe webhook event.
        
        Args:
            payload: Webhook payload bytes
            signature: Webhook signature
            
        Returns:
            True if handled successfully
        """
        if not self.stripe_available:
            return False
        
        settings = get_settings()
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        
        if not webhook_secret:
            return False
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
        except ValueError:
            return False
        except stripe.error.SignatureVerificationError:
            return False
        
        # Handle different event types
        if event['type'] == 'checkout.session.completed':
            self._handle_checkout_completed(event['data']['object'])
        elif event['type'] == 'customer.subscription.created':
            self._handle_subscription_created(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            self._handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            self._handle_subscription_deleted(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            self._handle_payment_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            self._handle_payment_failed(event['data']['object'])
        
        return True
    
    def _handle_checkout_completed(self, session: Dict[str, Any]):
        """Handle checkout.session.completed event."""
        user_id = int(session['metadata'].get('user_id', 0))
        plan_id = int(session['metadata'].get('plan_id', 0))
        billing_cycle = session['metadata'].get('billing_cycle', 'monthly')
        
        user = self.db.query(User).filter(User.id == user_id).first()
        plan = self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        
        if not user or not plan:
            return
        
        # Create subscription
        from app.services.subscription_service import SubscriptionService
        service = SubscriptionService(self.db)
        service.create_subscription(
            user=user,
            plan=plan,
            stripe_subscription_id=session.get('subscription'),
            stripe_customer_id=session.get('customer'),
            billing_cycle=billing_cycle
        )
    
    def _handle_subscription_created(self, subscription: Dict[str, Any]):
        """Handle customer.subscription.created event."""
        # Subscription already created in checkout handler
        pass
    
    def _handle_subscription_updated(self, subscription: Dict[str, Any]):
        """Handle customer.subscription.updated event."""
        stripe_sub_id = subscription['id']
        db_subscription = self.db.query(UserSubscription).filter(
            UserSubscription.stripe_subscription_id == stripe_sub_id
        ).first()
        
        if not db_subscription:
            return
        
        # Update subscription status
        status_map = {
            'active': SubscriptionStatus.ACTIVE.value,
            'canceled': SubscriptionStatus.CANCELED.value,
            'past_due': SubscriptionStatus.PAST_DUE.value,
            'unpaid': SubscriptionStatus.UNPAID.value,
            'trialing': SubscriptionStatus.TRIALING.value,
            'incomplete': SubscriptionStatus.INCOMPLETE.value,
            'incomplete_expired': SubscriptionStatus.INCOMPLETE_EXPIRED.value
        }
        
        db_subscription.status = status_map.get(subscription['status'], SubscriptionStatus.ACTIVE.value)
        db_subscription.current_period_start = datetime.fromtimestamp(subscription['current_period_start'])
        db_subscription.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
        db_subscription.cancel_at_period_end = subscription.get('cancel_at_period_end', False)
        
        if subscription['status'] == 'canceled' and not db_subscription.canceled_at:
            db_subscription.canceled_at = datetime.utcnow()
        
        self.db.commit()
    
    def _handle_subscription_deleted(self, subscription: Dict[str, Any]):
        """Handle customer.subscription.deleted event."""
        stripe_sub_id = subscription['id']
        db_subscription = self.db.query(UserSubscription).filter(
            UserSubscription.stripe_subscription_id == stripe_sub_id
        ).first()
        
        if db_subscription:
            db_subscription.status = SubscriptionStatus.CANCELED.value
            db_subscription.canceled_at = datetime.utcnow()
            db_subscription.user.is_premium = False
            self.db.commit()
    
    def _handle_payment_succeeded(self, invoice: Dict[str, Any]):
        """Handle invoice.payment_succeeded event."""
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return
        
        db_subscription = self.db.query(UserSubscription).filter(
            UserSubscription.stripe_subscription_id == subscription_id
        ).first()
        
        if not db_subscription:
            return
        
        # Create payment record
        payment = Payment(
            user_id=db_subscription.user_id,
            subscription_id=db_subscription.id,
            stripe_payment_intent_id=invoice.get('payment_intent'),
            stripe_invoice_id=invoice['id'],
            amount=float(invoice['amount_paid']) / 100,  # Convert from cents
            currency=invoice['currency'],
            status=PaymentStatus.SUCCEEDED.value,
            description=invoice.get('description', ''),
            paid_at=datetime.fromtimestamp(invoice['created'])
        )
        
        self.db.add(payment)
        self.db.commit()
    
    def _handle_payment_failed(self, invoice: Dict[str, Any]):
        """Handle invoice.payment_failed event."""
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return
        
        db_subscription = self.db.query(UserSubscription).filter(
            UserSubscription.stripe_subscription_id == subscription_id
        ).first()
        
        if db_subscription:
            db_subscription.status = SubscriptionStatus.PAST_DUE.value
            self.db.commit()
    
    def cancel_subscription(self, subscription: UserSubscription) -> bool:
        """
        Cancel Stripe subscription.
        
        Args:
            subscription: UserSubscription object
            
        Returns:
            True if canceled successfully
        """
        if not self.stripe_available or not subscription.stripe_subscription_id:
            return False
        
        try:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            subscription.cancel_at_period_end = True
            self.db.commit()
            return True
        except Exception as e:
            print(f"Stripe cancel error: {e}")
            return False


def get_stripe_service(db: Session) -> StripeService:
    """
    Get Stripe service instance.
    
    Args:
        db: Database session
        
    Returns:
        StripeService instance
    """
    return StripeService(db)


