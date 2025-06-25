#!/usr/bin/env python3
"""Migration script to move data from Redis to PostgreSQL."""

import redis
import json
from sqlalchemy.orm import Session
from database import SessionLocal, User, CreditBalance, CreditTransaction
from datetime import datetime

def migrate_redis_to_db():
    """Migrate user data and credits from Redis to PostgreSQL."""
    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Migrate users
        print("Migrating users...")
        user_keys = r.keys("user_email:*")
        for key in user_keys:
            email = key.replace("user_email:", "")
            user_data = r.get(key)
            if user_data:
                user = json.loads(user_data)
                
                # Check if user already exists in database
                existing_user = db.query(User).filter(User.email == email).first()
                if not existing_user:
                    db_user = User(
                        id=user.get("id"),
                        email=user.get("email"),
                        name=user.get("name"),
                        auth_provider=user.get("auth_provider", "email"),
                        google_sub=user.get("google_sub"),
                        picture=user.get("picture"),
                        password_hash=user.get("password_hash"),
                        created_at=datetime.fromtimestamp(user.get("created_at", 0))
                    )
                    db.add(db_user)
                    print(f"Added user: {email}")
        
        # Migrate credits
        print("Migrating credits...")
        credit_keys = r.keys("credits:*")
        for key in credit_keys:
            user_id = key.replace("credits:", "")
            credits = r.get(key)
            if credits:
                credits_int = int(credits)
                if credits_int > 0:
                    # Check if credit balance already exists
                    existing_balance = db.query(CreditBalance).filter(CreditBalance.user_id == user_id).first()
                    if not existing_balance:
                        balance = CreditBalance(user_id=user_id, credits=credits_int)
                        db.add(balance)
                        print(f"Added {credits_int} credits for user {user_id}")
        
        # Commit all changes
        db.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_redis_to_db() 