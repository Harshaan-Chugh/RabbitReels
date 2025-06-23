"""Billing and payment processing with Stripe."""

import os
import logging
import stripe
import time
import json
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from auth import get_current_user
from config import (
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
    FRONTEND_URL,
    CREDIT_PRICES,
    REDIS_URL
)

# Configure Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    logging.warning("STRIPE_SECRET_KEY not configured")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])

# Pydantic models for request/response
class CheckoutRequest(BaseModel):
    credits: int

class CheckoutResponse(BaseModel):
    url: str

class BalanceResponse(BaseModel):
    credits: int

class CreditTransaction(BaseModel):
    amount: int
    timestamp: str
    description: str

def get_redis():
    """Get Redis client - import here to avoid circular imports."""
    import redis
    from config import REDIS_URL
    return redis.from_url(REDIS_URL, decode_responses=True)

def get_user_credits(user_id: str) -> int:
    """Get user's current credit balance."""
    try:
        r = get_redis()
        balance = r.get(f"credits:{user_id}")
        return int(balance) if balance else 0
    except Exception as e:
        logger.error(f"Error getting user credits for {user_id}: {e}")
        return 0

def grant_credits(user_id: str, credits: int) -> None:
    """Grant credits to a user."""
    try:
        r = get_redis()
        r.incrby(f"credits:{user_id}", credits)
        
        # Log the transaction
        import time
        import json
        transaction = {
            "amount": credits,
            "timestamp": str(int(time.time())),
            "description": f"Purchased {credits} credits"
        }
        
        # Store transaction history (keep last 100 transactions)
        transaction_key = f"credit_transactions:{user_id}"
        r.lpush(transaction_key, json.dumps(transaction))
        r.ltrim(transaction_key, 0, 99)  # Keep only last 100
        
        logger.info(f"Granted {credits} credits to user {user_id}")
    except Exception as e:
        logger.error(f"Error granting credits to {user_id}: {e}")
        raise

def spend_credit(user_id: str) -> None:
    """Spend one credit from user's balance."""
    try:
        r = get_redis()
        balance = get_user_credits(user_id)
        
        if balance <= 0:
            raise HTTPException(
                status_code=402,
                detail="Insufficient credits. Please purchase more credits to continue."
            )
        
        r.decr(f"credits:{user_id}")
        
        # Log the transaction
        import time
        import json
        transaction = {
            "amount": -1,
            "timestamp": str(int(time.time())),
            "description": "Video generation"
        }
        
        transaction_key = f"credit_transactions:{user_id}"
        r.lpush(transaction_key, json.dumps(transaction))
        r.ltrim(transaction_key, 0, 99)
        
        logger.info(f"Spent 1 credit for user {user_id}, remaining: {balance - 1}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error spending credit for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error processing credit")

@router.get("/balance", response_model=BalanceResponse)
async def get_balance(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get user's current credit balance."""
    user_id = str(current_user["sub"])  # JWT uses "sub" for user ID
    credits = get_user_credits(user_id)
    return BalanceResponse(credits=credits)

@router.post("/checkout-session", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a Stripe checkout session for purchasing credits."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Stripe is not configured on this server"
        )
    
    if request.credits not in CREDIT_PRICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported credit pack size. Available: {list(CREDIT_PRICES.keys())}"
        )
    
    try:
        # Create checkout session
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"RabbitReels Video Credits ({request.credits} credits)",
                        "description": f"Generate {request.credits} AI videos with RabbitReels"
                    },
                    "unit_amount": CREDIT_PRICES[request.credits],
                },
                "quantity": 1,
            }],            customer_email=current_user.get("email"),
            client_reference_id=str(current_user["sub"]),
            metadata={
                "user_id": str(current_user["sub"]),
                "credits": str(request.credits),
                "email": current_user.get("email", "")
            },
            success_url=f"{FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/billing/cancel",
        )
        
        logger.info(f"Created checkout session for user {current_user['sub']}: {session.id}")
        return CheckoutResponse(url=session.url)
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Payment processing error")
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    if not STRIPE_WEBHOOK_SECRET:
        logger.error("Stripe webhook secret not configured")
        raise HTTPException(status_code=500, detail="Webhook not configured")
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        logger.error("Missing Stripe signature header")
        raise HTTPException(status_code=400, detail="Missing signature")
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    try:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            
            # Extract user info and credits from session
            user_id = session.get("client_reference_id")
            credits = int(session.get("metadata", {}).get("credits", 0))
            
            if user_id and credits > 0:
                # Grant credits to user
                grant_credits(user_id, credits)
                logger.info(f"Webhook: Granted {credits} credits to user {user_id}")
            else:
                logger.error(f"Webhook: Missing user_id or credits in session {session.get('id')}")
        
        elif event["type"] == "checkout.session.async_payment_succeeded":
            # Handle async payments (like SEPA, etc.)
            session = event["data"]["object"]
            user_id = session.get("client_reference_id")
            credits = int(session.get("metadata", {}).get("credits", 0))
            
            if user_id and credits > 0:
                grant_credits(user_id, credits)
                logger.info(f"Webhook: Async payment succeeded, granted {credits} credits to user {user_id}")
        
        elif event["type"] == "checkout.session.async_payment_failed":
            # Handle failed async payments
            session = event["data"]["object"]
            logger.warning(f"Webhook: Async payment failed for session {session.get('id')}")
        
        else:
            logger.info(f"Webhook: Unhandled event type: {event['type']}")
    
    except Exception as e:
        logger.error(f"Error processing webhook event: {e}")
        raise HTTPException(status_code=500, detail="Error processing webhook")
    
    return {"status": "success"}

@router.get("/success")
async def payment_success(session_id: str):
    """Handle successful payment redirect."""
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session ID")
    
    try:
        # Retrieve the session to get details
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == "paid":
            credits = int(session.metadata.get("credits", 0))
            return {
                "status": "success",
                "message": f"Payment successful! {credits} credits have been added to your account.",
                "credits": credits
            }
        else:
            return {
                "status": "pending",
                "message": "Payment is being processed. Credits will be added shortly."
            }
    
    except stripe.error.StripeError as e:
        logger.error(f"Error retrieving session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Error verifying payment")

@router.get("/cancel")
async def payment_cancel():
    """Handle cancelled payment."""
    return {
        "status": "cancelled",
        "message": "Payment was cancelled. You can try again anytime."
    }

# Helper endpoint to get credit prices for frontend
@router.get("/prices")
async def get_credit_prices():
    """Get available credit packages and prices."""
    prices = []
    for credits, price_cents in CREDIT_PRICES.items():
        price_dollars = price_cents / 100
        savings = 0
        if credits > 1:
            single_price = credits * (CREDIT_PRICES[1] / 100)
            savings = round(((single_price - price_dollars) / single_price) * 100)
        
        prices.append({
            "credits": credits,
            "price_cents": price_cents,
            "price_dollars": price_dollars,
            "savings_percent": savings,
            "popular": credits == 10  # Mark 10-credit pack as popular
        })
    
    return {"packages": prices}
