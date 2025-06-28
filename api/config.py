"""Configuration settings for the RabbitReels API service."""

import os
import sys
from dotenv import load_dotenv  # type: ignore

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
SCRIPTS_QUEUE = os.getenv("SCRIPTS_QUEUE", "scripts-queue")
VIDEO_QUEUE = os.getenv("VIDEO_QUEUE", "video-queue")
PUBLISH_QUEUE = os.getenv("PUBLISH_QUEUE", "publish-queue")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# PostgreSQL configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rabbitreels:IjnxShgB1CfpKs0Oj9gpMn2rmWJ2siS5LRsASUPQLx0=@postgres:5432/rabbitreels")

VIDEO_OUT_DIR = os.getenv("VIDEO_OUT_DIR", "/app/data/videos")

AVAILABLE_THEMES = [
    "family_guy",
    "rick_and_morty"
]

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8080"))
API_RELOAD = os.getenv("API_RELOAD", "false").lower() == "true"  # Disable reload in production

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_AUTH_REDIRECT = os.getenv("GOOGLE_AUTH_REDIRECT", "http://localhost:8080/api/auth/callback")

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable is required for production")
JWT_ALG = "HS256"
JWT_EXPIRES_SEC = 7 * 24 * 3600

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3001")

# Production settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"

# Session configuration
SESSION_SECRET = os.getenv("SESSION_SECRET")
if ENVIRONMENT == "production" and not SESSION_SECRET:
    raise ValueError("SESSION_SECRET environment variable is required for production")
elif not SESSION_SECRET:
    SESSION_SECRET = "dev-session-secret-change-in-production"

# Stripe configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Credit prices (in cents)
CREDIT_PRICES = {
    2: 100,   # $1.00 for 2 credits
    10: 450,  # $4.50 for 10 credits (10% discount)
    50: 2000, # $20.00 for 50 credits (20% discount)
}
