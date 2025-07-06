import os
import sys
from dotenv import load_dotenv

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../.env'))

# RabbitMQ Configuration
RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
VIDEO_QUEUE = os.getenv("VIDEO_QUEUE", "video-queue")

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Auto-scaling Configuration
MIN_WORKERS = int(os.getenv("MIN_WORKERS", "1"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "10"))
SCALE_UP_THRESHOLD = float(os.getenv("SCALE_UP_THRESHOLD", "2"))
SCALE_DOWN_THRESHOLD = float(os.getenv("SCALE_DOWN_THRESHOLD", "0.5"))
COOLDOWN_PERIOD = int(os.getenv("COOLDOWN_PERIOD", "60"))
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
METRICS_COLLECTION_INTERVAL = int(os.getenv("METRICS_COLLECTION_INTERVAL", "15"))

# Worker Configuration
GRACEFUL_SHUTDOWN_TIMEOUT = int(os.getenv("GRACEFUL_SHUTDOWN_TIMEOUT", "300"))
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "30"))
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "10"))

# Monitoring Configuration
METRICS_RETENTION_DAYS = int(os.getenv("METRICS_RETENTION_DAYS", "7"))
DASHBOARD_REFRESH_INTERVAL = int(os.getenv("DASHBOARD_REFRESH_INTERVAL", "5"))
ALERT_THRESHOLDS_CONFIG_PATH = os.getenv("ALERT_THRESHOLDS_CONFIG_PATH", "/app/config/alerts.yml")

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development" 