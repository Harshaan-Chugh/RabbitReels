import time
import json
import uuid
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from authlib.integrations.starlette_client import OAuth, OAuthError
from jose import jwt
import redis

from config import (
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_AUTH_REDIRECT,
    JWT_SECRET, JWT_ALG, JWT_EXPIRES_SEC, REDIS_URL, FRONTEND_URL
)

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()

# Redis client for user storage
rdb = redis.from_url(REDIS_URL, decode_responses=True)

# OAuth configuration
oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# 1️⃣ Entry point - redirect to Google OAuth
@router.get("/login")
async def login(request: Request):
    """Redirect user to Google OAuth login page."""
    redirect_uri = GOOGLE_AUTH_REDIRECT
    return await oauth.google.authorize_redirect(request, redirect_uri)

# 2️⃣ Google sends user back here with authorization code
@router.get("/callback")
async def auth_callback(request: Request):
    """Handle Google OAuth callback and issue JWT token."""
    try:
        token = await oauth.google.authorize_access_token(request)
        user = token["userinfo"]
    except OAuthError as e:
        raise HTTPException(400, f"OAuth error: {e.error}")

    google_sub = user["sub"]  # unique per Google account
    
    # Persist user profile in Redis (30 days TTL)
    user_data = {
        "sub": user["sub"],
        "email": user.get("email"),
        "name": user.get("name"),
        "picture": user.get("picture"),
        "created_at": int(time.time())
    }
    rdb.set(f"user:{google_sub}", json.dumps(user_data), ex=30*24*3600)

    # Create our own JWT
    payload = {
        "sub": google_sub,
        "email": user.get("email"),
        "name": user.get("name"),
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRES_SEC,
        "jti": str(uuid.uuid4()),    }
    token_str = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)    # Instead of redirecting, return HTML that does the redirect
    # This ensures we have full control over the URL
    # Note: Adding trailing slash to match Next.js static export config
    redirect_frontend = f"http://127.0.0.1/auth/callback/?token={token_str}"
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

# 3️⃣ JWT verification dependency
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

# Optional: Get full user profile from Redis
def get_current_user_profile(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Get full user profile from Redis using the JWT subject."""
    google_sub = current_user["sub"]
    user_data = rdb.get(f"user:{google_sub}")
    
    if not user_data:
        raise HTTPException(404, "User profile not found")
    
    return json.loads(user_data)

# 4️⃣ Test endpoints
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
    # In a more sophisticated setup, you might maintain a blacklist of JWTs
    return {"message": "Logged out successfully. Please discard your token."}
