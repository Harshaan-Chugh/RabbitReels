#!/usr/bin/env python3
"""
Quick Stripe Setup Test Script
Tests your Stripe configuration and helps verify everything is working.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_stripe_config():
    """Check if Stripe is properly configured."""
    print("🔧 Checking Stripe Configuration...")
    
    # Check for required environment variables
    stripe_secret = os.getenv("STRIPE_SECRET_KEY")
    stripe_publishable = os.getenv("STRIPE_PUBLISHABLE_KEY")
    stripe_webhook = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    issues = []
    
    if not stripe_secret:
        issues.append("❌ STRIPE_SECRET_KEY not set")
    elif not stripe_secret.startswith(("sk_test_", "sk_live_")):
        issues.append("❌ STRIPE_SECRET_KEY has invalid format")
    else:
        key_type = "TEST" if stripe_secret.startswith("sk_test_") else "LIVE"
        print(f"✅ STRIPE_SECRET_KEY configured ({key_type} mode)")
    
    if not stripe_publishable:
        issues.append("❌ STRIPE_PUBLISHABLE_KEY not set")
    elif not stripe_publishable.startswith(("pk_test_", "pk_live_")):
        issues.append("❌ STRIPE_PUBLISHABLE_KEY has invalid format")
    else:
        key_type = "TEST" if stripe_publishable.startswith("pk_test_") else "LIVE"
        print(f"✅ STRIPE_PUBLISHABLE_KEY configured ({key_type} mode)")
    
    if not stripe_webhook:
        issues.append("⚠️  STRIPE_WEBHOOK_SECRET not set (webhooks won't work)")
    elif not stripe_webhook.startswith("whsec_"):
        issues.append("❌ STRIPE_WEBHOOK_SECRET has invalid format")
    else:
        print("✅ STRIPE_WEBHOOK_SECRET configured")
    
    # Check key consistency
    if stripe_secret and stripe_publishable:
        secret_is_test = stripe_secret.startswith("sk_test_")
        publishable_is_test = stripe_publishable.startswith("pk_test_")
        
        if secret_is_test != publishable_is_test:
            issues.append("❌ Secret and publishable keys are from different modes (test/live)")
    
    return issues

def test_stripe_connection():
    """Test connection to Stripe API."""
    print("\n🔌 Testing Stripe API Connection...")
    
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        
        # Try to retrieve account information
        account = stripe.Account.retrieve()
        print(f"✅ Connected to Stripe account: {account.display_name or account.id}")
        print(f"   Country: {account.country}")
        print(f"   Charges enabled: {account.charges_enabled}")
        print(f"   Payouts enabled: {account.payouts_enabled}")
        
        return True
        
    except stripe.error.AuthenticationError:
        print("❌ Authentication failed - check your STRIPE_SECRET_KEY")
        return False
    except stripe.error.StripeError as e:
        print(f"❌ Stripe API error: {e}")
        return False
    except ImportError:
        print("❌ Stripe library not installed. Run: pip install stripe")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_price_configuration():
    """Test credit price configuration."""
    print("\n💰 Testing Credit Price Configuration...")
    
    try:
        from config import CREDIT_PRICES
        
        print("✅ Credit prices loaded:")
        for credits, price_cents in CREDIT_PRICES.items():
            price_dollars = price_cents / 100
            if credits == 1:
                print(f"   {credits} credit: ${price_dollars:.2f}")
            else:
                base_price = CREDIT_PRICES[1] * credits / 100
                savings = ((base_price - price_dollars) / base_price) * 100
                print(f"   {credits} credits: ${price_dollars:.2f} (Save {savings:.0f}%)")
        
        return True
        
    except ImportError as e:
        print(f"❌ Could not import config: {e}")
        return False
    except Exception as e:
        print(f"❌ Error loading credit prices: {e}")
        return False

def create_test_checkout():
    """Create a test checkout session."""
    print("\n🛒 Creating Test Checkout Session...")
    
    try:
        import stripe
        from config import CREDIT_PRICES, FRONTEND_URL
        
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        
        # Create a checkout session for 10 credits
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': '10 RabbitReels Credits',
                        'description': 'Credits for video generation',
                    },
                    'unit_amount': CREDIT_PRICES[10],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/billing/cancel",
            metadata={
                'credits': '10',
                'user_id': 'test-user',
                'test': 'true'
            }
        )
        
        print("✅ Test checkout session created successfully!")
        print(f"   Session ID: {session.id}")
        print(f"   Amount: ${CREDIT_PRICES[10]/100:.2f}")
        print(f"   URL: {session.url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create checkout session: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 RabbitReels Stripe Setup Test")
    print("=" * 50)
    
    # Check configuration
    issues = check_stripe_config()
    
    if issues:
        print("\n⚠️  Configuration Issues Found:")
        for issue in issues:
            print(f"   {issue}")
        
        print("\n📖 Please check the STRIPE_SETUP.md guide for help.")
        
        if any("not set" in issue or "invalid format" in issue for issue in issues):
            print("\n❌ Cannot continue without proper Stripe keys.")
            return False
    
    # Test API connection
    if not test_stripe_connection():
        return False
    
    # Test price configuration
    if not test_price_configuration():
        return False
    
    # Create test checkout
    if not create_test_checkout():
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All Stripe tests passed!")
    print("\n📋 Next Steps:")
    print("1. Start your application: python main.py")
    print("2. Test the billing flow in your browser")
    print("3. Use test card: 4242424242424242")
    print("4. Check payments in your Stripe Dashboard")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
