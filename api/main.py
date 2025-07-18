import os
import json
import asyncio
import logging
import time
import sys
from typing import Optional
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session #type: ignore

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import redis #type: ignore
import pika #type: ignore
from fastapi import FastAPI, HTTPException, Depends, Request #type: ignore
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse #type: ignore
from fastapi.staticfiles import StaticFiles #type: ignore
from fastapi.middleware.cors import CORSMiddleware #type: ignore
from starlette.middleware.sessions import SessionMiddleware #type: ignore
from fastapi import APIRouter #type: ignore
import uvicorn #type: ignore

from common.schemas import PromptJob, VideoStatus
from config import (
    RABBIT_URL,
    SCRIPTS_QUEUE,
    PUBLISH_QUEUE,
    VIDEO_OUT_DIR,
    REDIS_URL,
    AVAILABLE_THEMES,
    SESSION_SECRET,
    FRONTEND_URL,
    DEBUG
)
from auth import router as auth_router, get_current_user
from database import init_db, get_db, UserVideo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_client = None
status_consumer_task = None

def get_redis():
    """
    Get Redis client connection.
    """
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            return None
    return redis_client

def get_rabbit_channel():
    """
    Get RabbitMQ channel for publishing - create fresh connection each time.
    """
    try:
        logger.info("Creating fresh RabbitMQ connection")
        
        connection_params = pika.URLParameters(RABBIT_URL)
        connection_params.heartbeat = 0
        connection_params.blocked_connection_timeout = 30
        connection_params.connection_attempts = 5
        connection_params.retry_delay = 1
        connection_params.socket_timeout = 10
        
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()
        
        channel.queue_declare(queue=SCRIPTS_QUEUE, durable=True)
        
        logger.info("Fresh RabbitMQ connection established successfully")
        return connection, channel
        
    except Exception as e:
        logger.error(f"Failed to create RabbitMQ connection: {e}")
        raise

async def status_consumer():
    """
    Background task to consume status updates from RabbitMQ.
    """
    logger.info("Starting status consumer...")
    
    while True:
        try:
            await asyncio.sleep(5)
            
            r = get_redis()
            if r is None:
                logger.warning("Redis not available, skipping status consumer iteration")
                await asyncio.sleep(10)
                continue
                
            all_keys = r.keys("*")
            if all_keys is None:
                all_keys = []
            job_keys = [key for key in all_keys if not key.startswith("processed_session:")]
            
            for job_key in job_keys:
                if job_key in ["health", "status", "video_generation_count"]:
                    continue
                    
                try:
                    job_data = r.get(job_key)
                    if not job_data:
                        continue
                        
                    if not isinstance(job_data, str):
                        continue
                        
                    status_info = json.loads(job_data)
                    
                    if status_info.get("status") in ["done", "error"]:
                        continue
                    
                    job_id = status_info.get("job_id", job_key)
                    
                    if status_info.get("status") == "queued":
                        status_info["status"] = "rendering" 
                        status_info["progress"] = 0.3
                        r.set(job_key, json.dumps(status_info))
                        logger.info(f"Updated job {job_id} status to 'rendering'")
                        
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.error(f"Error checking job {job_key}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Status consumer error: {e}")
            await asyncio.sleep(10)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    """
    global redis_client, status_consumer_task
    
    logger.info("Starting up FastAPI application...")
    
    try:
        redis_client = get_redis()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        redis_client = None
    
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    try:
        from video_count import initialize_video_count
        from database import SessionLocal
        db = SessionLocal()
        try:
            count = initialize_video_count(db, 104)
            logger.info(f"Video count initialized/verified: {count}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to initialize video count: {e}")
    
    try:
        get_rabbit_channel()
        logger.info("RabbitMQ connection established")
    except Exception as e:
        logger.warning(f"RabbitMQ connection failed: {e}")
    
    if redis_client:
        status_consumer_task = asyncio.create_task(status_consumer())
        logger.info("Background status consumer started")
    else:
        status_consumer_task = None
        logger.info("Skipping background status consumer (Redis not available)")
    
    yield
    
    logger.info("Shutting down FastAPI application...")
    if status_consumer_task:
        status_consumer_task.cancel()
        try:
            await status_consumer_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="Shorts-Generator API",
    version="1.0.0",
    description="HTTP façade for RabbitMQ-based video pipeline",
    lifespan=lifespan
)
app.router.prefix = "/api"

allowed_origins = [FRONTEND_URL]
if DEBUG:
    allowed_origins.extend(["http://localhost:3001", "http://localhost:3000", "http://127.0.0.1:3001"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET
)

from billing import router as billing_router
app.include_router(billing_router)
app.include_router(auth_router)

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def root():
    """
    Serve the login page
    """
    return RedirectResponse(url="/static/login.html")

@app.get("/test-login")
def test_login():
    """
    Test endpoint to serve login page directly
    """
    try:
        with open(os.path.join(os.path.dirname(__file__), "static", "login.html"), "r") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except Exception as e:
        logger.error(f"Error serving login page: {e}")
        return {"error": "Failed to load login page", "message": str(e)}

@app.get("/login/success")
async def login_success(request: Request):
    """
    Success page redirect
    """
    logger.info("LOGIN SUCCESS ROUTE CALLED - redirecting to /static/success.html")
    token = request.query_params.get('token')
    if token:
        return RedirectResponse(url=f"/static/success.html?token={token}")
    else:
        return RedirectResponse(url="/static/success.html")

@app.get("/themes", tags=["Themes"])
def list_themes():
    """List available character themes."""
    return AVAILABLE_THEMES

@app.post("/videos", status_code=202, response_model=VideoStatus, tags=["Videos"])
def submit_video(job: PromptJob, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Submit a new prompt for video generation. Requires authentication and credits.
    """
    logger.info(f"Received job submission from user {current_user.get('email', 'unknown')}: {job.job_id} with theme '{job.character_theme}' and prompt: '{job.prompt[:50]}...'")
    
    from billing import spend_credit
    user_id = str(current_user.get("id", current_user.get("sub", "")))
    
    if not user_id:
        logger.error("No user ID found in current_user")
        raise HTTPException(status_code=400, detail="Invalid user session")
    
    # Store user video in database FIRST (before charging credits)
    try:
        # Generate a title from the prompt if none provided
        video_title = job.title
        if not video_title:
            # Create a title from the first 50 characters of the prompt
            video_title = job.prompt[:50].strip()
            if len(job.prompt) > 50:
                video_title += "..."
        
        user_video = UserVideo(
            user_id=user_id,
            job_id=job.job_id,
            title=video_title,
            character_theme=job.character_theme,
            prompt=job.prompt,
            status="queued"
        )
        db.add(user_video)
        db.commit()
        logger.info(f"User video record created for job {job.job_id} with title: {video_title}")
    except Exception as e:
        logger.error(f"Failed to create user video record: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating video record")
    
    # Only charge credits AFTER successful video record creation
    try:
        spend_credit(user_id, db)
        logger.info(f"Credit spent for user {user_id} for job {job.job_id}")
    except HTTPException as e:
        logger.warning(f"Credit spending failed for user {user_id}: {e.detail}")
        # If credit spending fails, delete the video record we just created
        try:
            db.delete(user_video)
            db.commit()
            logger.info(f"Deleted video record for failed credit spending: {job.job_id}")
        except Exception as cleanup_e:
            logger.error(f"Failed to cleanup video record after credit failure: {cleanup_e}")
            db.rollback()
        raise e
    except Exception as e:
        logger.error(f"Unexpected error spending credit for user {user_id}: {e}")
        # If credit spending fails, delete the video record we just created
        try:
            db.delete(user_video)
            db.commit()
            logger.info(f"Deleted video record for failed credit spending: {job.job_id}")
        except Exception as cleanup_e:
            logger.error(f"Failed to cleanup video record after credit failure: {cleanup_e}")
            db.rollback()
        raise HTTPException(status_code=500, detail="Error processing payment")
    
    job_data = job.model_dump()
    job_data["user_email"] = current_user.get("email")
    job_data["user_sub"] = current_user.get("sub")
    job_data["user_id"] = user_id
    
    if job.character_theme not in AVAILABLE_THEMES:
        logger.error(f"Invalid theme '{job.character_theme}' for job {job.job_id}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid theme '{job.character_theme}'. Available themes: {AVAILABLE_THEMES}"
        )
    
    try:
        # Store initial status in Redis
        logger.info(f"Storing initial status in Redis for job {job.job_id}")
        r = get_redis()
        if r is not None:
            status_data = {
                "job_id": job.job_id,
                "status": "queued",
                "user_email": current_user.get("email"),
                "user_sub": current_user.get("sub"),
                "submitted_at": int(time.time())
            }
            r.set(job.job_id, json.dumps(status_data))
            logger.info(f"Successfully stored initial status for job {job.job_id}")
        else:
            logger.warning("Redis not available, skipping status storage")
        
        # Publish to RabbitMQ with retry logic
        logger.info(f"Starting RabbitMQ publish for job {job.job_id}")
        max_retries = 3
        for attempt in range(max_retries):
            connection = None
            channel = None
            try:
                connection, channel = get_rabbit_channel()
                
                channel.basic_publish(
                    exchange="",
                    routing_key=SCRIPTS_QUEUE,
                    body=job.model_dump_json(),
                    properties=pika.BasicProperties(delivery_mode=2)
                )
                logger.info(f"Job {job.job_id} queued successfully")
                
                channel.close()
                connection.close()
                break
                
            except Exception as e:
                logger.error(f"RabbitMQ publish attempt {attempt + 1} failed: {e}")
                if channel:
                    try:
                        channel.close()
                    except:
                        pass
                if connection:
                    try:
                        connection.close()
                    except:
                        pass
                
                if attempt == max_retries - 1:
                    if r is not None:
                        error_status = {
                            "job_id": job.job_id,
                            "status": "error",
                            "error_msg": f"Failed to queue job after {max_retries} retries: {str(e)}"
                        }
                        r.set(job.job_id, json.dumps(error_status))
                    logger.error(f"Final failure for job {job.job_id}: {e}")
                    raise HTTPException(status_code=500, detail="Failed to queue job after retries")
                
                time.sleep(1)
        
        logger.info(f"Returning success response for job {job.job_id}")
        return VideoStatus(job_id=job.job_id, status="queued")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error submitting job {job.job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/videos/{job_id}", response_model=VideoStatus, tags=["Videos"])
def get_video_status(job_id: str):
    """
    Get current status of a video job.
    """
    try:
        r = get_redis()
        if r is None:
            raise HTTPException(status_code=503, detail="Status service unavailable")
            
        data = r.get(job_id)
        
        if not data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        status_info = json.loads(data)
        return VideoStatus(**status_info)
        
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON data for job {job_id}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Error getting status for job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/videos/{job_id}/file", tags=["Videos"])
def download_video(job_id: str, db: Session = Depends(get_db)):
    """
    Download the finished MP4 file.
    """
    try:
        # First check Redis for status
        r = get_redis()
        status_from_redis = None
        
        if r is not None:
            data = r.get(job_id)
            if data:
                try:
                    status_info = json.loads(data)
                    status_from_redis = status_info.get("status")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in Redis for job {job_id}")
        
        # If Redis doesn't have the data or status isn't "done", check the database
        if status_from_redis != "done":
            logger.info(f"Redis status is '{status_from_redis}' for {job_id}, checking database")
            user_video = db.query(UserVideo).filter(UserVideo.job_id == job_id).first()
            
            if not user_video:
                raise HTTPException(status_code=404, detail="Video not found")
            
            if user_video.status == "error":
                error_msg = user_video.error_message or "Unknown error"
                raise HTTPException(status_code=404, detail=f"Video generation failed: {error_msg}")
            elif user_video.status != "done":
                raise HTTPException(status_code=404, detail=f"Video not ready (status: {user_video.status})")
        
        # Video is ready, serve the file
        video_path = os.path.join(VIDEO_OUT_DIR, f"{job_id}.mp4")
        
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            raise HTTPException(status_code=404, detail="Video file not found")
        
        file_size = os.path.getsize(video_path)
        if file_size < 1000:
            logger.error(f"Video file appears corrupted (size: {file_size}): {video_path}")
            raise HTTPException(status_code=404, detail="Video file appears corrupted")
        
        logger.info(f"Serving video file: {video_path} (size: {file_size} bytes)")
        
        return FileResponse(
            path=video_path,
            media_type="video/mp4",
            filename=f"{job_id}.mp4"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading video for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/user/videos", tags=["Videos"])
def get_user_videos(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get all videos created by the current user.
    """
    user_id = str(current_user.get("id", current_user.get("sub", "")))
    
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid user session")
    
    try:
        # Get user videos from database, ordered by creation date (newest first)
        user_videos = db.query(UserVideo).filter(UserVideo.user_id == user_id).order_by(UserVideo.created_at.desc()).all()
        
        # Format the response
        videos = []
        for video in user_videos:
            # Get current status from Redis if available
            current_status = video.status
            download_url = video.download_url
            error_message = video.error_message
            
            # Check Redis for more up-to-date status
            try:
                r = get_redis()
                if r is not None:
                    redis_data = r.get(video.job_id)
                    if redis_data:
                        redis_status = json.loads(redis_data)
                        current_status = redis_status.get("status", current_status)
                        if current_status == "done":
                            download_url = f"/api/videos/{video.job_id}/file"
                        elif current_status == "error":
                            error_message = redis_status.get("error_msg", error_message)
            except Exception as e:
                logger.warning(f"Failed to get Redis status for job {video.job_id}: {e}")
            
            videos.append({
                "id": video.id,
                "job_id": video.job_id,
                "title": video.title,
                "character_theme": video.character_theme,
                "prompt": video.prompt,
                "status": current_status,
                "download_url": download_url,
                "error_message": error_message,
                "created_at": video.created_at.isoformat(),
                "updated_at": video.updated_at.isoformat()
            })
        
        return {"videos": videos}
        
    except Exception as e:
        logger.error(f"Error getting user videos for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/user/videos/update-status", tags=["Videos"])
def update_user_video_status(
    status_update: dict,
    db: Session = Depends(get_db)
):
    """
    Update user video status (called by video creator service).
    """
    try:
        job_id = status_update.get("job_id")
        status = status_update.get("status")
        file_path = status_update.get("file_path")
        download_url = status_update.get("download_url")
        error_message = status_update.get("error_message")
        
        if not job_id or not status:
            raise HTTPException(status_code=400, detail="job_id and status are required")
        
        # Find the user video record
        user_video = db.query(UserVideo).filter(UserVideo.job_id == job_id).first()
        
        if not user_video:
            logger.warning(f"User video not found for job_id: {job_id}")
            return {"success": False, "message": "Video not found"}
        
        # If video generation failed, refund the credit
        if status == "error" and user_video.status != "error":
            try:
                from billing import refund_credit
                refund_credit(user_video.user_id, db, f"Video generation failed: {error_message or 'Unknown error'}")
                logger.info(f"Refunded credit for failed video generation: {job_id}")
            except Exception as e:
                logger.error(f"Failed to refund credit for job {job_id}: {e}")
                # Continue with status update even if refund fails
        
        # Update the status
        user_video.status = status
        
        if file_path:
            user_video.file_path = file_path
        
        if download_url:
            user_video.download_url = download_url
        
        if error_message:
            user_video.error_message = error_message
        
        db.commit()
        logger.info(f"Updated user video status for job {job_id} to {status}")
        
        return {"success": True, "message": "Status updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating user video status: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/user/videos/refund-credit", tags=["Videos"])
def refund_user_credit(
    refund_request: dict,
    db: Session = Depends(get_db)
):
    """
    Refund credit for failed video generation (called by video creator service).
    """
    try:
        job_id = refund_request.get("job_id")
        user_id = refund_request.get("user_id")
        reason = refund_request.get("reason", "Video generation failed")
        
        if not job_id or not user_id:
            raise HTTPException(status_code=400, detail="job_id and user_id are required")
        
        # Verify the job exists and belongs to the user
        user_video = db.query(UserVideo).filter(
            UserVideo.job_id == job_id,
            UserVideo.user_id == user_id
        ).first()
        
        if not user_video:
            logger.warning(f"User video not found for job_id: {job_id}, user_id: {user_id}")
            return {"success": False, "message": "Video not found or doesn't belong to user"}
        
        # Only refund if not already refunded (check if status is not already error)
        if user_video.status == "error":
            logger.info(f"Credit already refunded for job {job_id}")
            return {"success": True, "message": "Credit already refunded"}
        
        # Refund the credit
        from billing import refund_credit
        refund_credit(user_id, db, reason)
        
        logger.info(f"Refunded credit for job {job_id} to user {user_id}")
        
        return {"success": True, "message": "Credit refunded successfully"}
        
    except Exception as e:
        logger.error(f"Error refunding credit: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
def health_check():
    """
    Health check endpoint.
    """
    health_status = {"status": "healthy"}
    
    try:
        r = get_redis()
        if r is not None:
            r.ping()
            health_status["redis"] = "ok"
        else:
            health_status["redis"] = "not available"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    try:
        connection, channel = get_rabbit_channel()
        if channel and not channel.is_closed:
            health_status["rabbitmq"] = "ok"
        else:
            health_status["rabbitmq"] = "channel closed"
            health_status["status"] = "unhealthy"
        
        if channel:
            channel.close()
        if connection:
            connection.close()
    except Exception as e:
        health_status["rabbitmq"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status

def get_backup_count():
    """
    Get backup video count from Redis.
    """
    try:
        r = get_redis()
        if r is not None:
            count = r.get("video_generation_count")
            return int(count) if count else 0
        else:
            return 0
    except Exception as e:
        logger.error(f"Error getting backup count: {e}")
        return 0

def save_backup_count(count):
    """
    Save backup video count to Redis.
    """
    try:
        r = get_redis()
        if r is not None:
            r.set("video_generation_count", count)
    except Exception as e:
        logger.error(f"Error saving backup count: {e}")

@app.get("/video-count", tags=["Statistics"])
def get_video_count_endpoint(db: Session = Depends(get_db)):
    """
    Get total video generation count from PostgreSQL.
    """
    from video_count import get_video_count
    try:
        count = get_video_count(db)
        return {"count": count}
    except Exception as e:
        logger.error(f"Error getting video count: {e}")
        return {"count": 0}

@app.post("/video-count/increment", tags=["Statistics"])
def increment_video_count_endpoint(db: Session = Depends(get_db)):
    """
    Increment video generation count in PostgreSQL.
    """
    from video_count import increment_video_count
    try:
        count = increment_video_count(db)
        return {"count": count}
    except Exception as e:
        logger.error(f"Error incrementing video count: {e}")
        return {"count": 0}

@app.post("/video-count/set", tags=["Statistics"])
def set_video_count_endpoint(count: int, db: Session = Depends(get_db)):
    """
    Set video generation count to a specific value in PostgreSQL (admin only).
    """
    from video_count import set_video_count
    try:
        new_count = set_video_count(db, count)
        return {"count": new_count, "message": f"Video count set to {new_count}"}
    except Exception as e:
        logger.error(f"Error setting video count: {e}")
        return {"count": 0, "error": str(e)}

@app.post("/video-count/add", tags=["Statistics"])
def add_to_video_count_endpoint(amount: int, db: Session = Depends(get_db)):
    """
    Add a specific amount to the video generation count in PostgreSQL (admin only).
    """
    from video_count import increment_video_count
    try:
        new_count = increment_video_count(db, amount)
        return {"count": new_count, "message": f"Added {amount} to video count. New total: {new_count}"}
    except Exception as e:
        logger.error(f"Error adding to video count: {e}")
        return {"count": 0, "error": str(e)}

@app.post("/video-count/restore", tags=["Statistics"])
def restore_video_count_endpoint(db: Session = Depends(get_db)):
    """
    Restore video count from backup file (admin only).
    """
    from video_count import get_video_count, set_video_count
    try:
        backup_file = "/app/data/video_count_backup.txt"
        if not os.path.exists(backup_file):
            return {"count": 0, "error": "Backup file not found"}

        with open(backup_file, 'r') as f:
            backup_count = f.read().strip()

        if not backup_count.isdigit():
            return {"count": 0, "error": f"Invalid backup count format: {backup_count}"}

        current_count = get_video_count(db)
        backup_count = int(backup_count)

        if backup_count > current_count:
            new_count = set_video_count(db, backup_count)
            return {"count": new_count, "message": f"Restored video count from backup: {new_count}"}
        else:
            return {"count": current_count, "message": f"Database count ({current_count}) is higher than backup ({backup_count}), keeping database value"}
    except Exception as e:
        logger.error(f"Error restoring video count: {e}")
        return {"count": 0, "error": str(e)}

@app.post("/video-count/init", tags=["Statistics"])
def initialize_video_count_endpoint(db: Session = Depends(get_db)):
    """
    Initialize video count to 104 (admin only).
    """
    from video_count import initialize_video_count
    try:
        count = initialize_video_count(db, 104)
        return {"count": count, "message": f"Video count initialized to {count}"}
    except Exception as e:
        logger.error(f"Error initializing video count: {e}")
        return {"count": 0, "error": str(e)}

if __name__ == "__main__":
    from config import API_HOST, API_PORT, API_RELOAD
    uvicorn.run(app, host=API_HOST, port=API_PORT, reload=API_RELOAD)
