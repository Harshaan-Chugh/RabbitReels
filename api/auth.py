import time
import json
import uuid
import bcrypt
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from authlib.integrations.starlette_client import OAuth, OAuthError
from jose import jwt
import redis
from pydantic import BaseModel

from config import (
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_AUTH_REDIRECT,
    JWT_SECRET, JWT_ALG, JWT_EXPIRES_SEC, REDIS_URL, FRONTEND_URL
)
from user_models import UserRegistration, UserLogin, UserResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()

rdb = redis.from_url(REDIS_URL, decode_responses=True)
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_jwt_token(user_data: Dict) -> str:
    """Create a JWT token for a user."""
    payload = {
        "sub": user_data["id"],
        "email": user_data["email"],
        "name": user_data["name"],
        "auth_provider": user_data.get("auth_provider", "email"),
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRES_SEC,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user data by email from Redis."""
    user_data = rdb.get(f"user_email:{email}")
    if user_data:
        return json.loads(user_data)
    return None

def store_user(user_data: Dict) -> str:
    """Store user data in Redis and return user ID."""
    user_id = str(uuid.uuid4())
    user_data["id"] = user_id
    user_data["created_at"] = int(time.time())
    
    rdb.set(f"user:{user_id}", json.dumps(user_data), ex=30*24*3600)
    rdb.set(f"user_email:{user_data['email']}", json.dumps(user_data), ex=30*24*3600)
    
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
async def register_user(user_data: UserRegistration):
    """Register a new user with email and password."""
    existing_user = get_user_by_email(user_data.email)
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
    
    user_id = store_user(user_info)
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
async def login_user(login_data: UserLogin):
    """Login with email and password."""
    user = get_user_by_email(login_data.email)
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
    """Redirect user to Google OAuth login page."""
    redirect_uri = GOOGLE_AUTH_REDIRECT
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/callback")
async def auth_callback(request: Request):
    """Handle Google OAuth callback and issue JWT token."""
    try:
        token = await oauth.google.authorize_access_token(request)
        user = token["userinfo"]
    except OAuthError as e:
        raise HTTPException(400, f"OAuth error: {e.error}")

    google_sub = user["sub"]
    
    existing_user = get_user_by_email(user.get("email"))
    
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
        user_id = store_user(user_data)
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
    """Extract and verify JWT token from Authorization header."""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired")
    except jwt.JWTError:
        raise HTTPException(401, "Token is invalid")

def get_current_user_profile(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Get full user profile from Redis using the JWT subject."""
    user_id = current_user["sub"]
    user_data = rdb.get(f"user:{user_id}")
    
    if not user_data:
        raise HTTPException(404, "User profile not found")
    
    return json.loads(user_data)
@router.get("/me")
async def get_me(user: Dict = Depends(get_current_user)):
    """Get current user's JWT claims."""
    return {"user": user, "message": "You are authenticated!"}

@router.get("/profile")
async def get_profile(profile: Dict = Depends(get_current_user_profile)):
    """Get current user's full profile from Redis."""
    return {"profile": profile}

@router.post("/logout")
async def logout(user: Dict = Depends(get_current_user)):
    """Logout endpoint (client should discard the JWT)."""
    return {"message": "Logged out successfully. Please discard your token."}

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Change user password (only for email auth users)."""
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
