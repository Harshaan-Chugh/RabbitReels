"""Configuration settings for the RabbitReels script generator service."""

import os
from dotenv import load_dotenv # type: ignore

load_dotenv()

RABBIT_URL = os.getenv("RABBIT_URL")
SCRIPTS_QUEUE = os.getenv("SCRIPTS_QUEUE", "scripts-queue")
VIDEO_QUEUE = os.getenv("VIDEO_QUEUE", "video-queue")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")