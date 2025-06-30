"""Configuration settings for the RabbitReels video creator service."""

import os
import sys
from dotenv import load_dotenv #type: ignore

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

RABBIT_URL = os.getenv("RABBIT_URL")
VIDEO_QUEUE = os.getenv("VIDEO_QUEUE", "video-queue")
PUBLISH_QUEUE = os.getenv("PUBLISH_QUEUE", "publish-queue")

ENABLE_PUBLISHER = os.getenv("ENABLE_PUBLISHER", "false").lower() == "true"

VIDEO_OUT_DIR = os.getenv("VIDEO_OUT_DIR", "./data/videos")

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
PETER_VOICE_ID = os.getenv("PETER_VOICE_ID", "tP8wEHVL4B2h4NuNcRtl")
STEWIE_VOICE_ID = os.getenv("STEWIE_VOICE_ID", "u58sF2rOukCb342nzwpN")

RICK_VOICE_ID = os.getenv("RICK_VOICE_ID")
MORTY_VOICE_ID = os.getenv("MORTY_VOICE_ID")

TTS_MAX_RETRIES = int(os.getenv("TTS_MAX_RETRIES", "3"))
TTS_RETRY_DELAY = int(os.getenv("TTS_RETRY_DELAY", "2"))
TTS_BACKOFF_MULTIPLIER = int(os.getenv("TTS_BACKOFF_MULTIPLIER", "2"))

REDIS_URL = os.getenv("REDIS_URL")

# PostgreSQL configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rabbitreels:IjnxShgB1CfpKs0Oj9gpMn2rmWJ2siS5LRsASUPQLx0=@postgres:5432/rabbitreels")

LONG_BG_VIDEO = os.getenv(    "LONG_BG_VIDEO",
    os.path.join(os.path.dirname(__file__), 'assets', 'long_bg.mp4')
)

AUDIO_ASSETS_DIR = os.getenv(
    "AUDIO_ASSETS_DIR",
    os.path.join(os.path.dirname(__file__), 'assets')
)