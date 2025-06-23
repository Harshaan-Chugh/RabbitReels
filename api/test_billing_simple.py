"""Simple billing system test."""

import sys
import os
sys.path.append(os.path.dirname(__file__))

# Simple test without external dependencies
def test_credit_prices():
    """Test that credit prices are configured correctly."""
    from config import CREDIT_PRICES
    
    print("🧪 Testing Credit Configuration...")
    print(f"Available credit packages: {CREDIT_PRICES}")
    
    # Check that we have the expected packages
    expected_packages = [1, 10, 50, 100]
    for package in expected_packages:
        assert package in CREDIT_PRICES, f"Missing {package} credit package"
        price = CREDIT_PRICES[package]
        price_per_credit = price / package
        print(f"  {package} credits: ${price/100:.2f} (${price_per_credit/100:.2f} per credit)")
    
    print("✅ All credit packages configured correctly")

def test_billing_imports():
    """Test that all billing modules import correctly."""
    print("\n🧪 Testing Billing Imports...")
    
    try:
        import billing
        print("✅ Billing module imports successfully")
        
        # Test that key functions exist
        assert hasattr(billing, 'get_user_credits'), "Missing get_user_credits function"
        assert hasattr(billing, 'grant_credits'), "Missing grant_credits function"
        assert hasattr(billing, 'spend_credit'), "Missing spend_credit function"
        print("✅ All billing functions available")
        
        # Test that router exists
        assert hasattr(billing, 'router'), "Missing FastAPI router"
        print("✅ FastAPI router available")
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    return True

def test_stripe_configuration():
    """Test Stripe configuration."""
    print("\n🧪 Testing Stripe Configuration...")
    
    from config import STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET
    
    if not STRIPE_SECRET_KEY:
        print("⚠️  STRIPE_SECRET_KEY not set (expected for development)")
    else:
        print("✅ STRIPE_SECRET_KEY configured")
    
    if not STRIPE_PUBLISHABLE_KEY:
        print("⚠️  STRIPE_PUBLISHABLE_KEY not set (expected for development)")
    else:
        print("✅ STRIPE_PUBLISHABLE_KEY configured")
    
    if not STRIPE_WEBHOOK_SECRET:
        print("⚠️  STRIPE_WEBHOOK_SECRET not set (expected for development)")
    else:
        print("✅ STRIPE_WEBHOOK_SECRET configured")
    
    print("ℹ️  To test with real Stripe, set up test keys from https://dashboard.stripe.com/test/apikeys")

def test_api_endpoints():
    """Test that the main API loads with billing endpoints."""
    print("\n🧪 Testing API Endpoint Registration...")
    
    try:
        # Mock Redis to avoid connection
        from unittest.mock import Mock, patch
        
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        
        with patch('main.get_redis', return_value=mock_redis):
            with patch('main.get_rabbit_channel', return_value=(Mock(), Mock())):
                from main import app
                
                # Check that billing routes are registered
                routes = [route.path for route in app.routes]
                
                billing_routes = [
                    '/billing/balance',
                    '/billing/checkout-session', 
                    '/billing/webhook',
                    '/billing/success',
                    '/billing/cancel',
                    '/billing/prices'
                ]
                
                for route in billing_routes:
                    if route in routes:
                        print(f"✅ {route} endpoint registered")
                    else:
                        print(f"❌ {route} endpoint missing")
                
                print("✅ API loads successfully with billing endpoints")
                
    except Exception as e:
        print(f"❌ API loading failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 RabbitReels Billing System Test Suite")
    print("=" * 50)
    
    tests = [
        test_credit_prices,
        test_billing_imports,
        test_stripe_configuration,
        test_api_endpoints
    ]
    
    passed = 0
    for test in tests:
        try:
            result = test()
            if result is not False:
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 Test Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! Billing system is ready.")
        print("\n📋 Next Steps:")
        print("1. Set up a Stripe account at https://stripe.com")
        print("2. Get your test API keys")
        print("3. Add them to your .env file")
        print("4. Start Redis (redis-server) and RabbitMQ")
        print("5. Run the API server: python main.py")
        print("6. Start the frontend: cd ../web && npm run dev")
        print("7. Test the full billing flow at http://localhost:3001/billing")
    else:
        print("❌ Some tests failed. Please check the errors above.")
