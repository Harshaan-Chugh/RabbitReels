"""Database models and configuration for RabbitReels."""

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text #type: ignore
from sqlalchemy.ext.declarative import declarative_base #type: ignore
from sqlalchemy.orm import sessionmaker #type: ignore
from datetime import datetime
import uuid
import sys
import config
import logging

logger = logging.getLogger(__name__)

print('PYTHONPATH:', sys.path)
DATABASE_URL = getattr(config, "DATABASE_URL", None)
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL could not be imported from config")

# Configure engine based on database type
if DATABASE_URL.startswith('sqlite'):
    logger.info(f"Using SQLite DATABASE_URL = {DATABASE_URL!r}")
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    logger.info(f"Using PostgreSQL DATABASE_URL = {DATABASE_URL!r}")
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    auth_provider = Column(String, default="email")  # "email" or "google"
    google_sub = Column(String, nullable=True)
    picture = Column(Text, nullable=True)
    password_hash = Column(String, nullable=True)  # Only for email auth users
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CreditBalance(Base):
    __tablename__ = "credit_balances"
    
    user_id = Column(String, primary_key=True)
    credits = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # Positive for credits added, negative for spent
    description = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemStats(Base):
    __tablename__ = "system_stats"
    
    key = Column(String, primary_key=True)
    value = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
