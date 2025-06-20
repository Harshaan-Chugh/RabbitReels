import os
import sys
from dotenv import load_dotenv  # type: ignore

# Allow imports from the repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# RabbitMQ settings
RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@localhost:5672/")
SCRIPTS_QUEUE = os.getenv("SCRIPTS_QUEUE", "scripts-queue")
VIDEO_QUEUE = os.getenv("VIDEO_QUEUE", "video-queue")
PUBLISH_QUEUE = os.getenv("PUBLISH_QUEUE", "publish-queue")

# Redis settings for job status tracking
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Video storage directory
VIDEO_OUT_DIR = os.getenv("VIDEO_OUT_DIR", "../data/videos")

# Available character themes
AVAILABLE_THEMES = [
    "family_guy",
    "rick_and_morty"
]

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8080"))
API_RELOAD = os.getenv("API_RELOAD", "true").lower() == "true"
