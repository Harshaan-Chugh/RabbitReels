#!/usr/bin/env python3
"""
Interactive Stripe Key Setup Helper
This script will guide you through setting up your Stripe keys.
"""

import os
import re

def get_stripe_keys():
    """Interactive setup to get Stripe keys from user."""
    print("🔑 Stripe Key Setup Helper")
    print("=" * 40)
    print()
    print("First, get your Stripe keys:")
    print("1. Go to https://dashboard.stripe.com")
    print("2. Make sure you're in TEST mode")
    print("3. Go to Developers → API keys")
    print()
    
    # Get secret key
    while True:
        secret_key = input("Enter your STRIPE_SECRET_KEY (sk_test_...): ").strip()
        if secret_key.startswith("sk_test_"):
            break
        elif secret_key.startswith("sk_live_"):
            print("⚠️  You entered a LIVE key! Please use TEST keys for development.")
            continue
        else:
            print("❌ Invalid format. Should start with 'sk_test_'")
    
    # Get publishable key
    while True:
        pub_key = input("Enter your STRIPE_PUBLISHABLE_KEY (pk_test_...): ").strip()
        if pub_key.startswith("pk_test_"):
            break
        elif pub_key.startswith("pk_live_"):
            print("⚠️  You entered a LIVE key! Please use TEST keys for development.")
            continue
        else:
            print("❌ Invalid format. Should start with 'pk_test_'")
    
    print()
    print("Now set up webhooks:")
    print("1. Go to Developers → Webhooks")
    print("2. Click 'Add endpoint'")
    print("3. URL: http://localhost:8080/billing/webhook")
    print("4. Select these events:")
    print("   - checkout.session.completed")
    print("   - checkout.session.async_payment_succeeded")
    print("   - checkout.session.async_payment_failed")
    print("5. Copy the signing secret")
    print()
    
    webhook_secret = input("Enter your STRIPE_WEBHOOK_SECRET (whsec_...): ").strip()
    
    return secret_key, pub_key, webhook_secret

def update_env_files(secret_key, pub_key, webhook_secret):
    """Update .env files with the provided keys."""
    
    # Update main .env file
    env_path = "../.env"
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            content = f.read()
        
        # Replace the placeholder values
        content = re.sub(
            r'STRIPE_SECRET_KEY=.*',
            f'STRIPE_SECRET_KEY={secret_key}',
            content
        )
        content = re.sub(
            r'STRIPE_PUBLISHABLE_KEY=.*',
            f'STRIPE_PUBLISHABLE_KEY={pub_key}',
            content
        )
        content = re.sub(
            r'STRIPE_WEBHOOK_SECRET=.*',
            f'STRIPE_WEBHOOK_SECRET={webhook_secret}',
            content
        )
        
        with open(env_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated {env_path}")
    
    # Update frontend .env.local file
    frontend_env_path = "../web/.env.local"
    if os.path.exists(frontend_env_path):
        with open(frontend_env_path, 'r') as f:
            content = f.read()
        
        content = re.sub(
            r'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=.*',
            f'NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY={pub_key}',
            content
        )
        
        with open(frontend_env_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated {frontend_env_path}")

def main():
    print("Welcome to the RabbitReels Stripe Setup Helper!")
    print()
    
    # Check if keys are already set
    from dotenv import load_dotenv
    load_dotenv("../.env")
    
    current_secret = os.getenv("STRIPE_SECRET_KEY", "")
    if current_secret and not current_secret.endswith("_here"):
        print("🎉 Stripe keys appear to already be configured!")
        print("Run 'python test_stripe_setup.py' to test your configuration.")
        return
    
    try:
        secret_key, pub_key, webhook_secret = get_stripe_keys()
        update_env_files(secret_key, pub_key, webhook_secret)
        
        print()
        print("🎉 Stripe keys configured successfully!")
        print()
        print("Next steps:")
        print("1. Run: python test_stripe_setup.py")
        print("2. Start your application")
        print("3. Test purchasing credits!")
        
    except KeyboardInterrupt:
        print("\n👋 Setup cancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
