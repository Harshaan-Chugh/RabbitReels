import os
import sys
from dotenv import load_dotenv #type: ignore

# allow imports from the repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# load our .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# RabbitMQ settings
RABBIT_URL    = os.getenv("RABBIT_URL")
VIDEO_QUEUE   = os.getenv("VIDEO_QUEUE", "video-queue")
PUBLISH_QUEUE = os.getenv("PUBLISH_QUEUE", "publish-queue")

# Publisher settings
ENABLE_PUBLISHER = os.getenv("ENABLE_PUBLISHER", "false").lower() == "true"

# Where to write out MP4s
VIDEO_OUT_DIR = os.getenv("VIDEO_OUT_DIR", "./data/videos")

# ElevenLabs TTS credentials (Peter voice)
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
PETER_VOICE_ID = os.getenv("PETER_VOICE_ID", "tP8wEHVL4B2h4NuNcRtl")
STEWIE_VOICE_ID = os.getenv("STEWIE_VOICE_ID", "u58sF2rOukCb342nzwpN")

# NEW: Add voice IDs for new characters
RICK_VOICE_ID = os.getenv("RICK_VOICE_ID")
MORTY_VOICE_ID = os.getenv("MORTY_VOICE_ID")

# TTS API Retry Configuration
TTS_MAX_RETRIES = int(os.getenv("TTS_MAX_RETRIES", "3"))
TTS_RETRY_DELAY = int(os.getenv("TTS_RETRY_DELAY", "2"))
TTS_BACKOFF_MULTIPLIER = int(os.getenv("TTS_BACKOFF_MULTIPLIER", "2"))

# Redis settings for status updates
REDIS_URL = os.getenv("REDIS_URL")

# Local path to our long-form background video
LONG_BG_VIDEO = os.getenv(
    "LONG_BG_VIDEO",
    os.path.join(os.path.dirname(__file__), 'assets', 'long_bg.mp4')
)

# Directory for additional audio assets (MP3s)
AUDIO_ASSETS_DIR = os.getenv(
    "AUDIO_ASSETS_DIR",
    os.path.join(os.path.dirname(__file__), 'assets')
)