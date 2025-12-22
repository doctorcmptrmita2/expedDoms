"""
Stripe webhook endpoint for handling subscription events.
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.stripe_service import StripeService, get_stripe_service

router = APIRouter()


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str = Header(None, alias="stripe-signature")
):
    """
    Handle Stripe webhook events.
    """
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    
    # Get raw body
    body = await request.body()
    
    # Process webhook
    stripe_service = get_stripe_service(db)
    success = stripe_service.handle_webhook(body, stripe_signature)
    
    if success:
        return Response(status_code=200)
    else:
        raise HTTPException(status_code=400, detail="Webhook processing failed")



