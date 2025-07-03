"""Billing and payment processing with Stripe."""

import logging
import stripe #type: ignore
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request #type: ignore
from pydantic import BaseModel #type: ignore
from sqlalchemy.orm import Session #type: ignore

from auth import get_current_user
from database import get_db, CreditBalance, CreditTransaction
from config import (
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
    FRONTEND_URL,
    CREDIT_PRICES,
    ENVIRONMENT
)

# Configure Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    logging.warning("STRIPE_SECRET_KEY not configured")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])

# Pydantic models
class CheckoutRequest(BaseModel):
    credits: int

class CheckoutResponse(BaseModel):
    url: str

class BalanceResponse(BaseModel):
    credits: int

class CreditTransactionResponse(BaseModel):
    amount: int
    timestamp: str
    description: str

class ProcessPaymentRequest(BaseModel):
    session_id: str

def get_redis():
    """
    Get Redis client - import here to avoid circular imports.
    """
    import redis #type: ignore
    from config import REDIS_URL
    try:
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return None

def get_user_credits(user_id: str, db: Session) -> int:
    """
    Get user's current credit balance from database.
    """
    try:
        balance = db.query(CreditBalance).filter(CreditBalance.user_id == user_id).first()
        return balance.credits if balance else 0
    except Exception as e:
        logger.error(f"Error getting user credits for {user_id}: {e}")
        return 0

def grant_credits(user_id: str, credits: int, db: Session) -> None:
    """
    Grant credits to a user in database.
    """
    try:
        # Get or create credit balance
        balance = db.query(CreditBalance).filter(CreditBalance.user_id == user_id).first()
        if balance:
            balance.credits += credits
        else:
            balance = CreditBalance(user_id=user_id, credits=credits)
            db.add(balance)
        
        # Log the transaction using database model
        transaction = CreditTransaction(
            user_id=user_id,
            amount=credits,
            description=f"Purchased {credits} credits"
        )
        db.add(transaction)
        db.commit()
        
        logger.info(f"Granted {credits} credits to user {user_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error granting credits to {user_id}: {e}")
        raise

def spend_credit(user_id: str, db: Session) -> None:
    """
    Spend one credit from user's balance in database.
    """
    try:
        balance = db.query(CreditBalance).filter(CreditBalance.user_id == user_id).first()
        
        if not balance or balance.credits <= 0:
            raise HTTPException(
                status_code=402,
                detail="Insufficient credits. Please purchase more credits to continue."
            )
        
        balance.credits -= 1
        
        transaction = CreditTransaction(
            user_id=user_id,
            amount=-1,
            description="Video generation"
        )
        db.add(transaction)
        db.commit()
        
        logger.info(f"Spent 1 credit for user {user_id}, remaining: {balance.credits}")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error spending credit for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error processing credit")

@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's current credit balance.
    """
    user_id = str(current_user["sub"])
    credits = get_user_credits(user_id, db)
    return BalanceResponse(credits=credits)

@router.post("/checkout-session", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a Stripe checkout session for purchasing credits.
    """
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
        user_email = current_user.get("email")
        if not user_email:
            logger.warning(f"No email found for user {current_user.get('sub')}")
            user_email = "customer@example.com"

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
            }],
            customer_email=user_email,
            client_reference_id=str(current_user["sub"]),
            metadata={
                "user_id": str(current_user["sub"]),
                "credits": str(request.credits),
                "email": user_email
            },
            success_url=f"{FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/billing/cancel",
        )
        
        logger.info(f"Created checkout session for user {current_user['sub']}: {session.id}")
        
        if not session.url:
            raise HTTPException(status_code=500, detail="Failed to create checkout session URL")
            
        return CheckoutResponse(url=session.url)
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/process-payment", include_in_schema=ENVIRONMENT == "development")
async def process_payment_manually(
    request: ProcessPaymentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Development-only endpoint to manually process payments when webhooks aren't available.
    This endpoint is only available in development mode.
    """
    if ENVIRONMENT != "development":
        raise HTTPException(status_code=404, detail="Not found")
    
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe is not configured")
    
    try:
        session = stripe.checkout.Session.retrieve(request.session_id)
        
        if session.payment_status != "paid":
            raise HTTPException(
                status_code=400, 
                detail=f"Payment not completed. Status: {session.payment_status}"
            )
        
        if session.client_reference_id != str(current_user["sub"]):
            raise HTTPException(
                status_code=403,
                detail="Session does not belong to current user"
            )
        
        metadata = session.metadata or {}
        credits = int(metadata.get("credits", 0))
        
        if credits <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid credits amount in session"
            )
        
        user_id = str(current_user["sub"])
        r = get_redis()
        processed_key = f"processed_session:{request.session_id}"
        
        if r and r.get(processed_key):
            raise HTTPException(
                status_code=409,
                detail="Payment already processed"
            )
        
        grant_credits(user_id, credits, db)
        
        if r:
            r.setex(processed_key, 86400, "1")
        
        logger.info(f"Manually processed payment for user {user_id}: {credits} credits")
        
        return {
            "status": "success",
            "message": f"Successfully granted {credits} credits",
            "credits": credits,
            "new_balance": get_user_credits(user_id, db)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing payment manually: {e}")
        raise HTTPException(status_code=500, detail="Error processing payment")

@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events."""
    logger.info("Webhook hit. Raw body len=%s", len(await request.body()))
    if not STRIPE_WEBHOOK_SECRET:
        logger.error("Stripe webhook secret not configured")
        raise HTTPException(status_code=500, detail="Webhook not configured")
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        logger.error("Missing Stripe signature header")
        raise HTTPException(status_code=400, detail="Missing signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as e:
        logger.error(f"Invalid signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    try:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            
            user_id = session.get("client_reference_id")
            credits = int(session.get("metadata", {}).get("credits", 0))
            session_id = session.get("id")
            
            if user_id and credits > 0: 
                r = get_redis()
                if r is None:
                    logger.error("Redis connection failed, cannot check for duplicate processing")
                    grant_credits(user_id, credits, db)
                else:
                    processed_key = f"processed_session:{session_id}"
                    processed_value = r.get(processed_key)
                    if processed_value is not None and str(processed_value) == "1":
                        logger.info(f"Webhook: Session {session_id} already processed, skipping")
                    else:
                        grant_credits(user_id, credits, db)
                        r.setex(processed_key, 86400, "1")
                        logger.info(f"Webhook: Granted {credits} credits to user {user_id}")
            else:
                logger.error(f"Webhook: Missing user_id or credits in session {session.get('id')}")
        
        elif event["type"] == "checkout.session.async_payment_succeeded":
            session = event["data"]["object"]
            user_id = session.get("client_reference_id")
            credits = int(session.get("metadata", {}).get("credits", 0))
            session_id = session.get("id")
            
            if user_id and credits > 0:
                r = get_redis()
                if r is None:
                    logger.error("Redis connection failed, cannot check for duplicate processing")
                    grant_credits(user_id, credits, db)
                else:
                    processed_key = f"processed_session:{session_id}"
                    processed_value = r.get(processed_key)
                    if processed_value is not None and str(processed_value) == "1":
                        logger.info(f"Webhook: Async session {session_id} already processed, skipping")
                    else:
                        grant_credits(user_id, credits, db)
                        r.setex(processed_key, 86400, "1")
                        logger.info(f"Webhook: Async payment succeeded, granted {credits} credits to user {user_id}")
        
        elif event["type"] == "checkout.session.async_payment_failed":
            session = event["data"]["object"]
            logger.warning(f"Webhook: Async payment failed for session {session.get('id')}")
        
        else:
            logger.info(f"Webhook: Unhandled event type: {event['type']}")
    
    except Exception as e:
        logger.error(f"Error processing webhook event: {e}")
        raise HTTPException(status_code=500, detail="Error processing webhook")
    
    return {"status": "success"}

@router.get("/success")
async def payment_success(session_id: str, db: Session = Depends(get_db)):
    """Handle successful payment redirect."""
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session ID")
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        logger.info(f"Retrieved session: {session_id}, payment_status: {session.payment_status}")
        
        if session.payment_status == "paid":
            metadata = session.metadata or {}
            credits = int(metadata.get("credits", 0))
            user_id = session.get("client_reference_id")
            
            if not user_id:
                raise HTTPException(status_code=400, detail="Invalid session: missing user ID")
                
            logger.info(f"Payment is paid. Credits: {credits}, User ID: {user_id}")
            
            current_credits = get_user_credits(user_id, db)
            logger.info(f"Current credits for user {user_id}: {current_credits}")
            
            needs_manual_processing = False
            if ENVIRONMENT == "development":
                logger.info(f"Development mode: checking for manual processing needed")
                recent_transaction = db.query(CreditTransaction).filter(
                    CreditTransaction.user_id == user_id,
                    CreditTransaction.amount == credits,
                    CreditTransaction.description.like(f"%{credits} credits%")
                ).order_by(CreditTransaction.created_at.desc()).first()
                
                logger.info(f"Looking for transaction: user_id={user_id}, amount={credits}, description like '%{credits} credits%'")
                logger.info(f"Found recent transaction: {recent_transaction}")
                
                if not recent_transaction:
                    needs_manual_processing = True
                    logger.info(f"Development: Manual processing needed for session {session_id}")
                else:
                    logger.info(f"Development: Transaction found, no manual processing needed")
            
            logger.info(f"needs_manual_processing: {needs_manual_processing}")
            
            if needs_manual_processing:
                return {
                    "status": "needs_manual_processing",
                    "message": f"Payment successful! {credits} credits are ready to be activated.",
                    "credits": credits,
                    "current_balance": current_credits,
                    "session_id": session_id,
                    "development_note": "Manual processing required in development mode."
                }
            else:
                return {
                    "status": "success",
                    "message": f"Payment successful! {credits} credits have been added to your account.",
                    "credits": credits,
                    "current_balance": current_credits,
                    "session_id": session_id,
                    "development_note": None
                }
        else:
            logger.info(f"Payment status is not paid: {session.payment_status}")
            return {
                "status": "pending",
                "message": "Payment is being processed. Credits will be added shortly."
            }
    
    except Exception as e:
        logger.error(f"Error retrieving session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Error verifying payment")

@router.get("/cancel")
async def payment_cancel():
    """Handle cancelled payment."""
    return {
        "status": "cancelled",
        "message": "Payment was cancelled. You can try again anytime."
    }

@router.get("/prices")
async def get_credit_prices():
    """
    Get available credit packages and prices.
    """
    prices = []
    for credits, price_cents in CREDIT_PRICES.items():
        price_dollars = price_cents / 100
        savings = 0
        if credits > 2:
            single_price = credits * (CREDIT_PRICES[2] / 2 / 100)
            savings = round(((single_price - price_dollars) / single_price) * 100)
        
        prices.append({
            "credits": credits,
            "price_cents": price_cents,
            "price_dollars": price_dollars,
            "savings_percent": savings,
            "popular": credits == 10
        })
    
    return {"packages": prices}
