import os
import sys
from dotenv import load_dotenv

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Docker Configuration
DOCKER_HOST = os.getenv("DOCKER_HOST")  # Use default Docker socket if not specified
DEPLOYMENT_MODE = os.getenv("DEPLOYMENT_MODE", "compose")  # "compose" or "swarm"

# Video Creator Service Configuration
VIDEO_CREATOR_SERVICE = os.getenv("VIDEO_CREATOR_SERVICE", "video-creator")
VIDEO_CREATOR_IMAGE = os.getenv("VIDEO_CREATOR_IMAGE", "rabbitreels/video-creator:latest")
DOCKER_NETWORK = os.getenv("DOCKER_NETWORK", "rabbitreels-network")

# Auto-scaling Configuration
MIN_WORKERS = int(os.getenv("MIN_WORKERS", "1"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "10"))
SCALE_UP_THRESHOLD = float(os.getenv("SCALE_UP_THRESHOLD", "2"))
SCALE_DOWN_THRESHOLD = float(os.getenv("SCALE_DOWN_THRESHOLD", "0.5"))
COOLDOWN_PERIOD = int(os.getenv("COOLDOWN_PERIOD", "60"))
SCALING_CHECK_INTERVAL = int(os.getenv("SCALING_CHECK_INTERVAL", "30"))

# Health Check Configuration
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "30"))
UNHEALTHY_WORKER_TIMEOUT = int(os.getenv("UNHEALTHY_WORKER_TIMEOUT", "300"))  # 5 minutes

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development" 