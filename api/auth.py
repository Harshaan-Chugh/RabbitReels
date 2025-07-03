import time
import json
import uuid
import bcrypt #type: ignore
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks #type: ignore
from fastapi.responses import RedirectResponse, HTMLResponse #type: ignore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials #type: ignore
from authlib.integrations.starlette_client import OAuth, OAuthError #type: ignore
from jose import jwt #type: ignore
import redis #type: ignore
from pydantic import BaseModel #type: ignore
from sqlalchemy.orm import Session #type: ignore
import smtplib #type: ignore
import os
from email.mime.text import MIMEText
import random

from config import (
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_AUTH_REDIRECT,
    JWT_SECRET, JWT_ALG, JWT_EXPIRES_SEC, REDIS_URL, FRONTEND_URL
)
from user_models import UserRegistration, UserLogin, UserResponse, TokenResponse
from database import get_db, User, CreditBalance, CreditTransaction

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()

rdb = redis.from_url(REDIS_URL, decode_responses=True)
def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_jwt_token(user_data: Dict) -> str:
    """
    Create a JWT token for a user.
    """
    payload = {
        "sub": user_data["id"],
        "email": user_data["email"],
        "name": user_data["name"],
        "auth_provider": user_data.get("auth_provider", "email"),
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRES_SEC,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, JWT_SECRET or "", algorithm=JWT_ALG)

def get_user_by_email(email: str, db: Session = None) -> Optional[Dict]:
    """
    Get user data by email from database and Redis cache.
    """
    # Try Redis cache
    user_data = rdb.get(f"user_email:{email}")
    if user_data:
        return json.loads(user_data)
    
    # If not in Redis, try database
    if db:
        db_user = db.query(User).filter(User.email == email).first()
        if db_user:
            user_dict = {
                "id": db_user.id,
                "email": db_user.email,
                "name": db_user.name,
                "auth_provider": db_user.auth_provider,
                "google_sub": db_user.google_sub,
                "picture": db_user.picture,
                "created_at": int(db_user.created_at.timestamp()) if db_user.created_at else int(time.time())
            }
            # Cache in Redis
            rdb.set(f"user:{db_user.id}", json.dumps(user_dict), ex=30*24*3600)
            rdb.set(f"user_email:{email}", json.dumps(user_dict), ex=30*24*3600)
            return user_dict
    
    return None

def store_user(user_data: Dict, db: Session = None) -> str:
    """
    Store user data in both database and Redis cache.
    """
    user_id = str(uuid.uuid4())
    user_data["id"] = user_id
    user_data["created_at"] = int(time.time())
    
    # Store in Redis cache
    rdb.set(f"user:{user_id}", json.dumps(user_data), ex=30*24*3600)
    rdb.set(f"user_email:{user_data['email']}", json.dumps(user_data), ex=30*24*3600)
    
    # Store in database
    if db:
        db_user = User(
            id=user_id,
            email=user_data["email"],
            name=user_data["name"],
            auth_provider=user_data.get("auth_provider", "email"),
            google_sub=user_data.get("google_sub"),
            picture=user_data.get("picture"),
            password_hash=user_data.get("password_hash")
        )
        db.add(db_user)
        
        # Initialize users with 1 credit
        credit_balance = CreditBalance(user_id=user_id, credits=1)
        db.add(credit_balance)
        
        # Log the welcome credit transaction
        welcome_transaction = CreditTransaction(
            user_id=user_id,
            amount=1,
            description="Welcome credit for new account"
        )
        db.add(welcome_transaction)
        
        db.commit()
        print(f"🎉 Granted 1 welcome credit to new user {user_id}")
    
    return user_id

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@router.post("/register", response_model=TokenResponse)
async def register_user(user_data: UserRegistration, db: Session = Depends(get_db)):
    """
    Register a new user with email and password.
    """
    existing_user = get_user_by_email(user_data.email, db)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")    
    hashed_password = hash_password(user_data.password)
    user_info = {
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": hashed_password,
        "auth_provider": "email"
    }
    
    user_id = store_user(user_info, db)
    user_info["id"] = user_id
    
    token = create_jwt_token(user_info)
    
    user_response = UserResponse(
        id=user_id,
        email=user_info["email"],
        name=user_info["name"],
        created_at=user_info["created_at"],
        auth_provider="email"
    )
    
    return TokenResponse(access_token=token, user=user_response)

@router.post("/login", response_model=TokenResponse)
async def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password.
    """
    user = get_user_by_email(login_data.email, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_jwt_token(user)
    
    user_response = UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        created_at=user["created_at"],
        auth_provider=user.get("auth_provider", "email")
    )
    
    return TokenResponse(access_token=token, user=user_response)

@router.get("/login")
async def login(request: Request):
    """
    Redirect user to Google OAuth login page.
    """
    redirect_uri = GOOGLE_AUTH_REDIRECT
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handle Google OAuth callback and issue JWT token.
    """
    print("DEBUG: Callback endpoint hit!")
    try:
        token = await oauth.google.authorize_access_token(request)
        print("DEBUG: Got token from Google")   
        user = token["userinfo"]
        print(f"DEBUG: User info: {user.get('email')}")
    except OAuthError as e:
        print(f"DEBUG: OAuth error: {e}")
        raise HTTPException(400, f"OAuth error: {e.error}")

    google_sub = user["sub"]
    
    existing_user = get_user_by_email(user.get("email"), db)
    
    if existing_user:
        token_str = create_jwt_token(existing_user)
        user_id = existing_user["id"]
    else:
        user_data = {
            "email": user.get("email"),
            "name": user.get("name"),
            "picture": user.get("picture"),
            "google_sub": google_sub,
            "auth_provider": "google"
        }
        user_id = store_user(user_data, db)
        user_data["id"] = user_id
        token_str = create_jwt_token(user_data)

    redirect_frontend = f"{FRONTEND_URL}/auth/callback?token={token_str}"
    print(f"DEBUG: Redirecting to: {redirect_frontend}")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Redirecting...</title>
        <meta http-equiv="refresh" content="0; url={redirect_frontend}">
        <script>
            console.log("Redirecting to: {redirect_frontend}");
            // Fallback JavaScript redirect
            setTimeout(function() {{
                window.location.href = "{redirect_frontend}";
            }}, 1000);
        </script>
    </head>
    <body>
        <p>Redirecting to application...</p>
        <p>If you are not redirected automatically, <a href="{redirect_frontend}">click here</a>.</p>
        <p>Target URL: <code>{redirect_frontend}</code></p>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content, status_code=200)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Extract and verify JWT token from Authorization header.
    """
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, JWT_SECRET or "", algorithms=[JWT_ALG])
        return payload
    except jwt.ExpiredSignatureError: #type: ignore
        raise HTTPException(401, "Token has expired")
    except jwt.JWTError: #type: ignore
        raise HTTPException(401, "Token is invalid")

def get_current_user_profile(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Get full user profile from Redis using the JWT subject.
    """
    user_id = current_user["sub"]
    user_data = rdb.get(f"user:{user_id}")
    
    if not user_data:
        raise HTTPException(404, "User profile not found")
    
    return json.loads(user_data)
@router.get("/me")
async def get_me(user: Dict = Depends(get_current_user)):
    """
    Get current user's JWT claims.
    """
    return {"user": user, "message": "You are authenticated!"}

@router.get("/profile")
async def get_profile(profile: Dict = Depends(get_current_user_profile)):
    """
    Get current user's full profile from Redis.
    """
    return {"profile": profile}

@router.post("/logout")
async def logout(user: Dict = Depends(get_current_user)):
    """
    Logout endpoint (client should discard the JWT).
    """
    return {"message": "Logged out successfully. Please discard your token."}

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Change user password (only for email auth users).
    """
    user_id = current_user["sub"]
    user_data = rdb.get(f"user:{user_id}")
    
    if not user_data:
        raise HTTPException(404, "User profile not found")
    
    user_profile = json.loads(user_data)
    
    if user_profile.get("auth_provider") != "email":
        raise HTTPException(400, "Password change not available for OAuth users")
    
    if not verify_password(request.current_password, user_profile["password_hash"]):
        raise HTTPException(401, "Current password is incorrect")
    
    if len(request.new_password) < 6:
        raise HTTPException(400, "New password must be at least 6 characters long")
    
    user_profile["password_hash"] = hash_password(request.new_password)
    
    rdb.set(f"user:{user_profile['id']}", json.dumps(user_profile), ex=30*24*3600)
    rdb.set(f"user_email:{user_profile['email']}", json.dumps(user_profile), ex=30*24*3600)
    
    return {"message": "Password changed successfully"}

VERIFICATION_CODE_EXPIRY = 15 * 60

# Helper to send email (Gmail SMTP)
def send_verification_email(to_email: str, code: str):
    gmail_user = os.getenv('GMAIL_USER')
    gmail_pass = os.getenv('GMAIL_PASS')
    print(f"[EMAIL] Attempting to send verification code to {to_email} using {gmail_user}")
    if not gmail_user or not gmail_pass:
        print("[EMAIL] GMAIL_USER or GMAIL_PASS not set in environment")
        raise Exception('GMAIL_USER or GMAIL_PASS not set in environment')
    msg = MIMEText(f"Your RabbitReels verification code is: {code}")
    msg['Subject'] = 'Your RabbitReels Verification Code'
    msg['From'] = gmail_user
    msg['To'] = to_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, [to_email], msg.as_string())
        print(f"[EMAIL] Successfully sent verification code to {to_email}")
    except Exception as e:
        print(f"[EMAIL] Failed to send verification code to {to_email}: {e}")
        raise

# Endpoint: Request verification code
class RequestCodeModel(BaseModel):
    email: str

@router.post("/request-code")
def request_verification_code(data: RequestCodeModel, background_tasks: BackgroundTasks):
    email = data.email.strip().lower()
    code = f"{random.randint(0, 999999):06d}"
    rdb.setex(f"signup_code:{email}", VERIFICATION_CODE_EXPIRY, code)
    background_tasks.add_task(send_verification_email, email, code)
    return {"message": "Verification code sent to your Gmail."}

# Endpoint: Verify code and register
class VerifyCodeModel(BaseModel):
    email: str
    code: str
    password: str
    name: str

@router.post("/verify-code", response_model=TokenResponse)
def verify_code_and_register(data: VerifyCodeModel, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    stored_code = rdb.get(f"signup_code:{email}")
    if not stored_code or stored_code != data.code:
        raise HTTPException(400, "Invalid or expired verification code.")
    rdb.delete(f"signup_code:{email}")
    existing_user = get_user_by_email(email, db)
    if existing_user:
        raise HTTPException(400, "Email already registered.")
    if len(data.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters long.")
    hashed_password = hash_password(data.password)
    user_info = {
        "email": email,
        "name": data.name,
        "password_hash": hashed_password,
        "auth_provider": "email"
    }
    user_id = store_user(user_info, db)
    user_info["id"] = user_id
    token = create_jwt_token(user_info)
    user_response = UserResponse(
        id=user_id,
        email=user_info["email"],
        name=user_info["name"],
        created_at=user_info["created_at"],
        auth_provider="email"
    )
    return TokenResponse(access_token=token, user=user_response)
