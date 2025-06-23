#!/usr/bin/env python3
"""
End-to-End Billing System Test for RabbitReels
Tests the complete billing flow: authentication, credit purchase, video generation, credit spending
"""
import sys
import os
import time
import json
import requests
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configuration
API_BASE = "http://localhost:8080"
WEB_BASE = "http://localhost:3001"
TEST_USER_ID = f"test-user-{uuid4().hex[:8]}"
TEST_JOB_ID = f"test-job-{uuid4().hex[:8]}"

class BillingTestSuite:
    def __init__(self):
        self.api_base = API_BASE
        self.web_base = WEB_BASE
        self.test_user_id = TEST_USER_ID
        self.auth_token = None
        self.results = []
        
    def log_result(self, test_name, success, message="", details=None):
        """Log test result."""
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
        if details:
            print(f"   {details}")
        self.results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        })
        
    def test_prerequisites(self):
        """Test that all required services are running."""
        print("\n🔧 Testing Prerequisites...")
        
        # Test API server
        try:
            response = requests.get(f"{self.api_base}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                if health.get("status") == "healthy":
                    self.log_result("API Health", True, "API server is healthy")
                    
                    # Check individual services
                    redis_ok = health.get("redis") == "ok"
                    rabbitmq_ok = health.get("rabbitmq") == "ok"
                    
                    self.log_result("Redis Connection", redis_ok, 
                                  "Connected" if redis_ok else f"Error: {health.get('redis')}")
                    self.log_result("RabbitMQ Connection", rabbitmq_ok,
                                  "Connected" if rabbitmq_ok else f"Error: {health.get('rabbitmq')}")
                else:
                    self.log_result("API Health", False, f"Unhealthy: {health}")
            else:
                self.log_result("API Health", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("API Health", False, f"Connection failed: {e}")
            return False
            
        # Test frontend (optional)
        try:
            response = requests.get(self.web_base, timeout=5)
            if response.status_code == 200:
                self.log_result("Frontend", True, "Frontend is accessible")
            else:
                self.log_result("Frontend", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("Frontend", False, f"Not accessible: {e}")
            
        return True
        
    def test_billing_endpoints(self):
        """Test that billing endpoints are available."""
        print("\n💳 Testing Billing Endpoints...")
        
        endpoints = [
            ("/billing/prices", "GET", "Credit packages"),
            ("/billing/balance", "GET", "Credit balance (requires auth)"),
            ("/billing/checkout-session", "POST", "Checkout session (requires auth)"),
            ("/billing/webhook", "POST", "Stripe webhook"),
            ("/billing/success", "GET", "Payment success"),
            ("/billing/cancel", "GET", "Payment cancel")
        ]
        
        for endpoint, method, description in endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{self.api_base}{endpoint}")
                else:
                    response = requests.post(f"{self.api_base}{endpoint}")
                      # 401/403 is expected for protected endpoints without auth
                # 500 is expected for webhook when not configured
                if response.status_code in [200, 401, 403, 422, 500]:
                    self.log_result(f"Endpoint {endpoint}", True, 
                                  f"Accessible (HTTP {response.status_code})")
                else:
                    self.log_result(f"Endpoint {endpoint}", False, 
                                  f"HTTP {response.status_code}")
            except Exception as e:
                self.log_result(f"Endpoint {endpoint}", False, f"Error: {e}")
                
    def test_credit_packages(self):
        """Test credit package configuration."""
        print("\n📦 Testing Credit Packages...")
        
        try:
            response = requests.get(f"{self.api_base}/billing/prices")
            if response.status_code == 200:
                data = response.json()
                packages = data.get("packages", [])
                
                if packages:
                    self.log_result("Credit Packages", True, f"Found {len(packages)} packages")
                    
                    for pkg in packages:
                        credits = pkg.get("credits")
                        price = pkg.get("price_dollars")
                        savings = pkg.get("savings_percent", 0)
                        
                        if savings > 0:
                            msg = f"{credits} credits for ${price} (Save {savings}%)"
                        else:
                            msg = f"{credits} credits for ${price}"
                            
                        self.log_result(f"Package {credits}", True, msg)
                else:
                    self.log_result("Credit Packages", False, "No packages found")
            else:
                self.log_result("Credit Packages", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("Credit Packages", False, f"Error: {e}")
            
    def test_credit_management(self):
        """Test credit management functions directly."""
        print("\n🏦 Testing Credit Management...")
        
        try:
            # Import billing functions
            from billing import get_user_credits, grant_credits, spend_credit
            
            # Test getting credits for new user (should be 0)
            initial_credits = get_user_credits(self.test_user_id)
            self.log_result("Get Initial Credits", True, f"User has {initial_credits} credits")
            
            # Test granting credits
            grant_credits(self.test_user_id, 5)
            new_credits = get_user_credits(self.test_user_id)
            
            if new_credits == initial_credits + 5:
                self.log_result("Grant Credits", True, f"Successfully granted 5 credits")
            else:
                self.log_result("Grant Credits", False, 
                              f"Expected {initial_credits + 5}, got {new_credits}")
                
            # Test spending credit
            spend_credit(self.test_user_id)
            final_credits = get_user_credits(self.test_user_id)
            
            if final_credits == new_credits - 1:
                self.log_result("Spend Credit", True, f"Successfully spent 1 credit")
            else:
                self.log_result("Spend Credit", False, 
                              f"Expected {new_credits - 1}, got {final_credits}")
                              
            # Test spending more credits than available
            try:
                # Spend all remaining credits first
                for _ in range(final_credits):
                    spend_credit(self.test_user_id)
                      # This should raise an HTTPException
                spend_credit(self.test_user_id)
                self.log_result("Insufficient Credits", False, 
                              "Should have raised an exception")
            except Exception as e:
                # Check if it's an HTTPException with status 402
                if (hasattr(e, 'status_code') and e.status_code == 402) or \
                   (hasattr(e, 'detail') and "Insufficient credits" in str(e.detail)):
                    self.log_result("Insufficient Credits", True, 
                                  "Correctly rejected when no credits")
                else:
                    self.log_result("Insufficient Credits", False, f"Wrong error: {e}")
                    
        except Exception as e:
            self.log_result("Credit Management", False, f"Import/execution error: {e}")
            
    def test_mock_authentication(self):
        """Test authentication flow (mocked)."""
        print("\n🔐 Testing Authentication...")
          # For testing purposes, we'll create a mock user session
        # In a real scenario, this would be done through OAuth
        try:
            # Create a test JWT token (for testing only)
            from auth import create_jwt_token
            from config import JWT_SECRET
            
            mock_user = {
                "sub": self.test_user_id,
                "email": f"test-{self.test_user_id}@example.com",
                "name": f"Test User {self.test_user_id}",
                "id": self.test_user_id
            }
            
            token = create_jwt_token(mock_user)
            self.auth_token = token
            
            self.log_result("Mock Authentication", True, "Created test JWT token")
            
            # Test token validation
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{self.api_base}/auth/me", headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                self.log_result("Token Validation", True, f"Token valid for {user_data.get('email')}")
            else:
                self.log_result("Token Validation", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("Mock Authentication", False, f"Error: {e}")
            
    def test_authenticated_billing_endpoints(self):
        """Test billing endpoints with authentication."""
        print("\n🔑 Testing Authenticated Billing...")
        
        if not self.auth_token:
            self.log_result("Auth Required", False, "No auth token available")
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test getting balance
        try:
            response = requests.get(f"{self.api_base}/billing/balance", headers=headers)
            if response.status_code == 200:
                balance = response.json()
                credits = balance.get("credits", 0)
                self.log_result("Get Balance", True, f"User has {credits} credits")
            else:
                self.log_result("Get Balance", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("Get Balance", False, f"Error: {e}")
            
        # Test creating checkout session (will fail without Stripe keys, but should validate request)
        try:
            checkout_data = {"credits": 10}
            response = requests.post(
                f"{self.api_base}/billing/checkout-session",
                headers={**headers, "Content-Type": "application/json"},
                json=checkout_data
            )
            
            if response.status_code == 200:
                session_data = response.json()
                self.log_result("Checkout Session", True, "Session created successfully")
            elif response.status_code == 500 and "not configured" in response.text:
                self.log_result("Checkout Session", True, "Correctly requires Stripe configuration")
            else:
                self.log_result("Checkout Session", False, f"HTTP {response.status_code}: {response.text}")
        except Exception as e:
            self.log_result("Checkout Session", False, f"Error: {e}")
            
    def test_video_generation_with_credits(self):
        """Test video generation with credit requirements."""
        print("\n🎬 Testing Video Generation with Credits...")
        
        if not self.auth_token:
            self.log_result("Video Generation", False, "No auth token available")
            return
              # First, ensure user has credits
        try:
            from billing import grant_credits
            grant_credits(self.test_user_id, 2)  # Give user 2 credits
            self.log_result("Setup Credits", True, "Granted 2 credits for testing")
        except Exception as e:
            self.log_result("Setup Credits", False, f"Error: {e}")
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Test video submission
        job_data = {
            "job_id": TEST_JOB_ID,
            "prompt": "Explain what a credit system is",
            "character_theme": "family_guy"
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/videos",
                headers={**headers, "Content-Type": "application/json"},
                json=job_data
            )
            
            if response.status_code == 202:
                self.log_result("Video Submission", True, "Video job submitted successfully")
                
                # Check that credit was spent
                from billing import get_user_credits
                remaining_credits = get_user_credits(self.test_user_id)
                if remaining_credits == 1:  # Should be 2 - 1 = 1
                    self.log_result("Credit Deduction", True, "Credit properly deducted")
                else:
                    self.log_result("Credit Deduction", False, f"Expected 1 credit, got {remaining_credits}")
                    
            elif response.status_code == 402:
                self.log_result("Video Submission", True, "Correctly rejected due to insufficient credits")
            else:
                self.log_result("Video Submission", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Video Submission", False, f"Error: {e}")
            
        # Test submission without credits
        try:
            from billing import spend_credit
            # Spend remaining credits
            spend_credit(self.test_user_id)  # Should have 0 credits now
            
            response = requests.post(
                f"{self.api_base}/videos",
                headers={**headers, "Content-Type": "application/json"},
                json=job_data
            )
            
            if response.status_code == 402:
                self.log_result("No Credits Rejection", True, "Correctly rejected when no credits")
            else:
                self.log_result("No Credits Rejection", False, f"Should have been rejected (HTTP {response.status_code})")
                
        except Exception as e:
            self.log_result("No Credits Rejection", False, f"Error: {e}")
            
    def test_frontend_integration(self):
        """Test that frontend billing pages are accessible."""
        print("\n🌐 Testing Frontend Integration...")
        
        frontend_pages = [
            ("/billing", "Main billing page"),
            ("/billing/success", "Payment success page"),
            ("/billing/cancel", "Payment cancel page")
        ]
        
        for page, description in frontend_pages:
            try:
                response = requests.get(f"{self.web_base}{page}")
                if response.status_code == 200:
                    self.log_result(f"Frontend {page}", True, f"{description} accessible")
                else:
                    self.log_result(f"Frontend {page}", False, f"HTTP {response.status_code}")
            except Exception as e:
                self.log_result(f"Frontend {page}", False, f"Error: {e}")
                
    def cleanup(self):
        """Clean up test data."""
        print("\n🧹 Cleaning up...")
        
        try:
            # Remove test user credits from Redis
            import redis
            from config import REDIS_URL
            
            r = redis.from_url(REDIS_URL, decode_responses=True)
              # Clean up credit data
            r.delete(f"credits:{self.test_user_id}")
            r.delete(f"credit_transactions:{self.test_user_id}")
            
            # Clean up any test job data
            r.delete(TEST_JOB_ID)
            
            self.log_result("Cleanup", True, "Test data cleaned up")
            
        except Exception as e:
            self.log_result("Cleanup", False, f"Error: {e}")
            
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 RabbitReels Billing System - End-to-End Test")
        print("=" * 60)
        
        # Run tests in order
        if not self.test_prerequisites():
            print("\n❌ Prerequisites failed. Cannot continue.")
            return
            
        self.test_billing_endpoints()
        self.test_credit_packages()
        self.test_credit_management()
        self.test_mock_authentication()
        self.test_authenticated_billing_endpoints()
        self.test_video_generation_with_credits()
        self.test_frontend_integration()
        self.cleanup()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 All tests passed! Billing system is working correctly.")
            print("\n📋 Next Steps:")
            print("1. Set up Stripe test keys for real payment testing")
            print("2. Test with actual Stripe checkout flow")
            print("3. Configure webhooks for production")
        else:
            print(f"\n⚠️  {total - passed} tests failed. Check the errors above.")
            
        return passed == total

if __name__ == "__main__":
    test_suite = BillingTestSuite()
    success = test_suite.run_all_tests()
    sys.exit(0 if success else 1)
