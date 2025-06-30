"""Video count management using PostgreSQL."""

from sqlalchemy.orm import Session
from database import SystemStats
import logging

logger = logging.getLogger(__name__)

VIDEO_COUNT_KEY = "video_generation_count"

def get_video_count(db: Session) -> int:
    """Get the current video generation count from PostgreSQL."""
    try:
        stat = db.query(SystemStats).filter(SystemStats.key == VIDEO_COUNT_KEY).first()
        return int(stat.value) if stat else 0
    except Exception as e:
        logger.error(f"Error getting video count from database: {e}")
        return 0

def set_video_count(db: Session, count: int) -> int:
    """Set the video generation count in PostgreSQL."""
    try:
        stat = db.query(SystemStats).filter(SystemStats.key == VIDEO_COUNT_KEY).first()
        if stat:
            stat.value = count
        else:
            stat = SystemStats(key=VIDEO_COUNT_KEY, value=count)
            db.add(stat)
        
        db.commit()
        logger.info(f"Video count set to {count}")
        return count
    except Exception as e:
        logger.error(f"Error setting video count in database: {e}")
        db.rollback()
        return 0

def increment_video_count(db: Session, amount: int = 1) -> int:
    """Increment the video generation count in PostgreSQL."""
    try:
        stat = db.query(SystemStats).filter(SystemStats.key == VIDEO_COUNT_KEY).first()
        if stat:
            current_value = int(stat.value)
            stat.value = current_value + amount
        else:
            stat = SystemStats(key=VIDEO_COUNT_KEY, value=amount)
            db.add(stat)
        
        db.commit()
        new_value = int(stat.value)
        logger.info(f"Video count incremented by {amount} to {new_value}")
        return new_value
    except Exception as e:
        logger.error(f"Error incrementing video count in database: {e}")
        db.rollback()
        return 0

def initialize_video_count(db: Session, initial_count: int = 0) -> int:
    """Initialize the video count if it doesn't exist."""
    try:
        stat = db.query(SystemStats).filter(SystemStats.key == VIDEO_COUNT_KEY).first()
        if not stat:
            stat = SystemStats(key=VIDEO_COUNT_KEY, value=initial_count)
            db.add(stat)
            db.commit()
            logger.info(f"Initialized video count to {initial_count}")
            return initial_count
        else:
            current_value = int(stat.value)
            logger.info(f"Video count already exists: {current_value}")
            return current_value
    except Exception as e:
        logger.error(f"Error initializing video count: {e}")
        db.rollback()
        return 0 