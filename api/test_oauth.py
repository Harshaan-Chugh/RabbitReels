#!/usr/bin/env python3
"""
OAuth Test Script for RabbitReels API
This script will help test the OAuth flow and protected endpoints.
"""

import requests
import json
import sys
import webbrowser
from urllib.parse import urlparse, parse_qs

BASE_URL = "http://localhost:8080"

def test_unprotected_endpoint():
    """Test that unprotected endpoints work."""
    print("🔓 Testing unprotected endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/themes")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_protected_endpoint_without_auth():
    """Test that protected endpoints reject unauthenticated requests."""
    print("\n🔒 Testing protected endpoint without authentication...")
    try:
        response = requests.get(f"{BASE_URL}/auth/me")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        if response.status_code in [401, 403]:
            print("✅ Correctly rejected unauthenticated request")
            return True
        else:
            print("❌ Should have rejected unauthenticated request")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_protected_endpoint_with_auth(token):
    """Test that protected endpoints accept authenticated requests."""
    print(f"\n🔑 Testing protected endpoint with JWT token...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    endpoints = [
        ("/auth/me", "User Info"),
        ("/auth/profile", "User Profile"),
        ("/videos", "Videos List")
    ]
    
    for endpoint, name in endpoints:
        try:
            print(f"\n📡 Testing {name} ({endpoint})...")
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ {name} - Success!")
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            else:
                print(f"❌ {name} - Failed!")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"❌ Error testing {name}: {e}")

def start_oauth_flow():
    """Start the OAuth flow by opening the login URL."""
    print("\n🚀 Starting OAuth flow...")
    login_url = f"{BASE_URL}/auth/login"
    print(f"Opening: {login_url}")
    
    # Open the URL in the default browser
    webbrowser.open(login_url)
    
    print("\n📝 After you complete the Google login, you'll be redirected to a success page.")
    print("The success page will show your JWT token.")
    print("Copy the JWT token and paste it here:")
    
    token = input("\nPaste your JWT token here: ").strip()
    
    if token:
        print(f"\n✅ Token received (length: {len(token)})")
        return token
    else:
        print("❌ No token provided")
        return None

def main():
    print("🐰 RabbitReels OAuth Test Script")
    print("=" * 40)
    
    # Test 1: Unprotected endpoint
    if not test_unprotected_endpoint():
        print("❌ Server seems to be down or misconfigured")
        sys.exit(1)
    
    # Test 2: Protected endpoint without auth
    if not test_protected_endpoint_without_auth():
        print("❌ Authentication protection not working")
        sys.exit(1)
    
    # Test 3: OAuth flow
    print("\n" + "=" * 40)
    print("Now we'll test the OAuth flow...")
    print("This will open your browser for Google login.")
    
    proceed = input("Continue? (y/n): ").lower().strip()
    if proceed != 'y':
        print("Exiting...")
        sys.exit(0)
    
    token = start_oauth_flow()
    
    if token:
        # Test 4: Protected endpoints with auth
        test_protected_endpoint_with_auth(token)
        print("\n🎉 OAuth testing complete!")
    else:
        print("❌ Could not complete OAuth flow")
        sys.exit(1)

if __name__ == "__main__":
    main()
