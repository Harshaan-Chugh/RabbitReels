import os, sys
from dotenv import load_dotenv # type: ignore

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

RABBIT_URL     = os.getenv("RABBIT_URL")
VIDEO_QUEUE    = os.getenv("VIDEO_QUEUE", "video-queue")
PUBLISH_QUEUE  = os.getenv("PUBLISH_QUEUE", "publish-queue")
VIDEO_OUT_DIR  = os.getenv("VIDEO_OUT_DIR", "../data/videos")
REVID_API_KEY  = os.getenv("REVID_API_KEY", "")
