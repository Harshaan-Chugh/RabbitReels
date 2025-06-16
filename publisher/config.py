import os, sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..")))

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

RABBIT_URL       = os.getenv("RABBIT_URL")
PUBLISH_QUEUE    = os.getenv("PUBLISH_QUEUE", "publish-queue")
VIDEOS_DIR       = os.getenv("VIDEO_OUT_DIR", "./data/videos")
CLIENT_SECRETS   = os.getenv("YOUTUBE_CLIENT_SECRETS")
TOKEN_PATH       = os.getenv("YOUTUBE_TOKEN")
