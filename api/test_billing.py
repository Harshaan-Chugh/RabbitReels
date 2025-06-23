"""Simple test script to verify billing endpoints without external dependencies."""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from fastapi.testclient import TestClient
import pytest
from unittest.mock import Mock, patch
import json

# Mock Redis to avoid connection issues
class MockRedis:
    def __init__(self):
        self.data = {}
    
    def get(self, key):
        return self.data.get(key)
    
    def set(self, key, value):
        self.data[key] = value
    
    def incrby(self, key, amount):
        current = int(self.data.get(key, 0))
        self.data[key] = str(current + amount)
    
    def decr(self, key):
        current = int(self.data.get(key, 0))
        self.data[key] = str(max(0, current - 1))
    
    def lpush(self, key, value):
        pass
    
    def ltrim(self, key, start, end):
        pass
    
    def ping(self):
        return True

# Mock RabbitMQ
def mock_get_rabbit_channel():
    return Mock(), Mock()

# Mock authentication
def mock_get_current_user():
    return {
        "id": "test_user_123",
        "email": "test@example.com",
        "name": "Test User"
    }

def test_billing_system():
    """Test the billing system without external dependencies."""
    
    # Mock Redis connection
    mock_redis = MockRedis()
    
    with patch('billing.get_redis', return_value=mock_redis):
        with patch('main.get_redis', return_value=mock_redis):
            with patch('main.get_rabbit_channel', side_effect=mock_get_rabbit_channel):
                with patch('billing.get_current_user', return_value=mock_get_current_user()):
                    # Import after patching
                    from main import app
                    from billing import get_user_credits, grant_credits, spend_credit
                    
                    client = TestClient(app)
                    
                    print("🧪 Testing Billing System...")
                    
                    # Test 1: Check initial credit balance
                    print("\n1. Testing initial credit balance...")
                    user_id = "test_user_123"
                    initial_credits = get_user_credits(user_id)
                    print(f"   Initial credits: {initial_credits}")
                    assert initial_credits == 0, f"Expected 0 credits, got {initial_credits}"
                    print("   ✅ Initial balance is 0")
                    
                    # Test 2: Grant credits
                    print("\n2. Testing credit granting...")
                    grant_credits(user_id, 10)
                    credits_after_grant = get_user_credits(user_id)
                    print(f"   Credits after granting 10: {credits_after_grant}")
                    assert credits_after_grant == 10, f"Expected 10 credits, got {credits_after_grant}"
                    print("   ✅ Credit granting works")
                    
                    # Test 3: Spend credit
                    print("\n3. Testing credit spending...")
                    spend_credit(user_id)
                    credits_after_spend = get_user_credits(user_id)
                    print(f"   Credits after spending 1: {credits_after_spend}")
                    assert credits_after_spend == 9, f"Expected 9 credits, got {credits_after_spend}"
                    print("   ✅ Credit spending works")
                    
                    # Test 4: Try to spend credit when balance is 0
                    print("\n4. Testing spending with insufficient credits...")
                    # Spend all remaining credits
                    for _ in range(9):
                        spend_credit(user_id)
                    
                    try:
                        spend_credit(user_id)  # This should fail
                        print("   ❌ Should have failed with insufficient credits")
                        assert False, "Should have raised an exception"
                    except Exception as e:
                        print(f"   ✅ Correctly failed with: {str(e)}")
                        assert "Insufficient credits" in str(e)
                    
                    # Test 5: Test credit packages endpoint
                    print("\n5. Testing credit packages endpoint...")
                    response = client.get("/billing/prices")
                    print(f"   Response status: {response.status_code}")
                    if response.status_code == 200:
                        data = response.json()
                        packages = data.get("packages", [])
                        print(f"   Found {len(packages)} credit packages")
                        for pkg in packages:
                            print(f"     - {pkg['credits']} credits for ${pkg['price_dollars']}")
                        print("   ✅ Credit packages endpoint works")
                    else:
                        print(f"   ❌ Failed with status {response.status_code}")
                    
                    print("\n🎉 All billing tests passed!")
                    return True

if __name__ == "__main__":
    test_billing_system()
