import os
import json
import asyncio
import logging
import time
import sys
from typing import Optional
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import redis
import pika
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import uvicorn

from common.schemas import PromptJob, VideoStatus
from config import (
    RABBIT_URL,
    SCRIPTS_QUEUE,
    PUBLISH_QUEUE,
    VIDEO_OUT_DIR,
    REDIS_URL,
    AVAILABLE_THEMES
)
from auth import router as auth_router, get_current_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

redis_client = None
status_consumer_task = None

def get_redis():
    """Get Redis client connection."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return redis_client

def get_rabbit_channel():
    """Get RabbitMQ channel for publishing - create fresh connection each time."""
    try:
        logger.info("Creating fresh RabbitMQ connection")
        
        # Create fresh connection with more conservative heartbeat settings
        connection_params = pika.URLParameters(RABBIT_URL)
        connection_params.heartbeat = 0  # Disable heartbeat to avoid timeout issues
        connection_params.blocked_connection_timeout = 30  # 30 second timeout
        connection_params.connection_attempts = 5
        connection_params.retry_delay = 1
        connection_params.socket_timeout = 10  # 10 second socket timeout
        
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()
        
        # Declare the queue as durable
        channel.queue_declare(queue=SCRIPTS_QUEUE, durable=True)
        
        logger.info("Fresh RabbitMQ connection established successfully")
        return connection, channel
        
    except Exception as e:
        logger.error(f"Failed to create RabbitMQ connection: {e}")
        raise

async def status_consumer():
    """Background task to consume status updates from RabbitMQ."""
    logger.info("Starting status consumer...")
      # For now, we'll implement a simple approach:
    # 1. When jobs are submitted, they start as "queued"
    # 2. The video-creator service will update Redis status directly
    # 3. This consumer only handles transitioning from queued to rendering
    
    while True:
        try:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            r = get_redis()
            # Get all job keys
            job_keys = r.keys("*")
            
            for job_key in job_keys:
                # Skip non-job keys
                if job_key in ["health", "status", "video_generation_count"]:
                    continue
                    
                try:
                    job_data = r.get(job_key)
                    if not job_data:
                        continue
                        
                    status_info = json.loads(job_data)
                    
                    # Skip if already done or error
                    if status_info.get("status") in ["done", "error"]:
                        continue
                    
                    job_id = status_info.get("job_id", job_key)
                    
                    # Only update status from queued to rendering if it's been queued for a while
                    # The video-creator will handle updating to "done" status directly
                    if status_info.get("status") == "queued":
                        # Check if it's been queued for a while, assume rendering
                        # This is a simple heuristic - in production you'd want better tracking
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
            await asyncio.sleep(10)  # Wait longer on error

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global status_consumer_task
    
    # Startup
    logger.info("Starting up FastAPI application...")
    
    try:
        # Initialize Redis connection
        r = get_redis()
        r.ping()  # Test connection
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to establish Redis connection: {e}")
        raise
    
    try:
        # Initialize RabbitMQ connection with retry
        max_retries = 5
        for attempt in range(max_retries):
            try:
                get_rabbit_channel()
                logger.info("RabbitMQ connection established")
                break
            except Exception as e:
                logger.error(f"RabbitMQ connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error("Failed to establish RabbitMQ connection after all retries")
                    raise
                await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Failed to establish RabbitMQ connection: {e}")
        raise
    
    # Start background status consumer
    status_consumer_task = asyncio.create_task(status_consumer())
    logger.info("Background status consumer started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application...")
    
    if status_consumer_task:
        status_consumer_task.cancel()
        try:
            await status_consumer_task
        except asyncio.CancelledError:
            pass
    
    if redis_client:
        try:
            redis_client.close()
            logger.info("Redis connection closed")
        except:
            pass

# Create FastAPI app
app = FastAPI(
    title="Shorts-Generator API",
    version="1.0.0",
    description="HTTP façade for RabbitMQ-based video pipeline",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session middleware for OAuth
app.add_middleware(
    SessionMiddleware,
    secret_key="your-session-secret-key-change-this-in-production"
)

# Include auth router
app.include_router(auth_router)

# Include billing router
from billing import router as billing_router
app.include_router(billing_router)

# Mount static files for the login page
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Redirect root to login page
@app.get("/")
def root():
    """Serve the login page"""
    return RedirectResponse(url="/static/login.html")

@app.get("/test-login")
def test_login():
    """Test endpoint to serve login page directly"""
    try:
        with open(os.path.join(os.path.dirname(__file__), "static", "login.html"), "r") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except Exception as e:
        logger.error(f"Error serving login page: {e}")
        return {"error": "Failed to load login page", "message": str(e)}

# Success page redirect  
@app.get("/login/success")
async def login_success(request: Request):
    logger.info("LOGIN SUCCESS ROUTE CALLED - redirecting to /static/success.html")
    # Extract token from query parameters and pass it along
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
def submit_video(job: PromptJob, current_user: dict = Depends(get_current_user)):
    """Submit a new prompt for video generation. Requires authentication and credits."""
    logger.info(f"Received job submission from user {current_user.get('email', 'unknown')}: {job.job_id} with theme '{job.character_theme}' and prompt: '{job.prompt[:50]}...'")
    
    # Check and spend credit before processing
    from billing import spend_credit
    user_id = str(current_user.get("id", current_user.get("sub", "")))
    
    if not user_id:
        logger.error("No user ID found in current_user")
        raise HTTPException(status_code=400, detail="Invalid user session")
    
    try:
        spend_credit(user_id)
        logger.info(f"Credit spent for user {user_id} for job {job.job_id}")
    except HTTPException as e:
        logger.warning(f"Credit spending failed for user {user_id}: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error spending credit for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error processing payment")
    
    # Add user information to the job data for potential future use
    job_data = job.model_dump()
    job_data["user_email"] = current_user.get("email")
    job_data["user_sub"] = current_user.get("sub")
    job_data["user_id"] = user_id
    
    # Validate theme
    if job.character_theme not in AVAILABLE_THEMES:
        logger.error(f"Invalid theme '{job.character_theme}' for job {job.job_id}")
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid theme '{job.character_theme}'. Available themes: {AVAILABLE_THEMES}"
        )
    
    try:        # Store initial status in Redis
        logger.info(f"Storing initial status in Redis for job {job.job_id}")
        r = get_redis()
        status_data = {
            "job_id": job.job_id,
            "status": "queued",
            "user_email": current_user.get("email"),
            "user_sub": current_user.get("sub"),
            "submitted_at": int(time.time())
        }
        r.set(job.job_id, json.dumps(status_data))
        logger.info(f"Successfully stored initial status for job {job.job_id}")
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
                    properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
                )
                logger.info(f"Job {job.job_id} queued successfully")
                
                # Close connection immediately after use
                channel.close()
                connection.close()
                break  # Success, exit retry loop
                
            except Exception as e:
                logger.error(f"RabbitMQ publish attempt {attempt + 1} failed: {e}")
                  # Clean up connections on error
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
                    # Update status to error in Redis
                    error_status = {
                        "job_id": job.job_id,
                        "status": "error",
                        "error_msg": f"Failed to queue job after {max_retries} retries: {str(e)}"
                    }
                    r.set(job.job_id, json.dumps(error_status))
                    logger.error(f"Final failure for job {job.job_id}: {e}")
                    raise HTTPException(status_code=500, detail="Failed to queue job after retries")
                
                time.sleep(1)  # Brief pause before retry
        
        logger.info(f"Returning success response for job {job.job_id}")
        return VideoStatus(job_id=job.job_id, status="queued")
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Unexpected error submitting job {job.job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/videos/{job_id}", response_model=VideoStatus, tags=["Videos"])
def get_video_status(job_id: str):
    """Get current status of a video job."""
    try:
        r = get_redis()
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
def download_video(job_id: str):
    """Download the finished MP4 file."""
    try:
        r = get_redis()
        data = r.get(job_id)
        
        if not data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        status_info = json.loads(data)
        
        if status_info.get("status") != "done":
            status = status_info.get("status", "unknown")
            if status == "error":
                raise HTTPException(status_code=404, detail=f"Video generation failed: {status_info.get('error_msg', 'Unknown error')}")
            else:
                raise HTTPException(status_code=404, detail=f"Video not ready (status: {status})")
        
        # Check if file exists locally
        video_path = os.path.join(VIDEO_OUT_DIR, f"{job_id}.mp4")
        
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            raise HTTPException(status_code=404, detail="Video file not found")
        
        # Verify file size to ensure it's not corrupted
        file_size = os.path.getsize(video_path)
        if file_size < 1000:  # Less than 1KB is probably corrupted
            logger.error(f"Video file appears corrupted (size: {file_size}): {video_path}")
            raise HTTPException(status_code=404, detail="Video file appears corrupted")
        
        logger.info(f"Serving video file: {video_path} (size: {file_size} bytes)")
        
        # Serve the file directly
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

@app.get("/health")
def health_check():
    """Health check endpoint."""
    health_status = {"status": "healthy"}
    
    try:
        # Check Redis connection
        r = get_redis()
        r.ping()
        health_status["redis"] = "ok"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    try:
        # Check RabbitMQ connection
        connection, channel = get_rabbit_channel()
        if channel and not channel.is_closed:
            health_status["rabbitmq"] = "ok"
        else:
            health_status["rabbitmq"] = "channel closed"
            health_status["status"] = "unhealthy"
        
        # Clean up test connection
        if channel:
            channel.close()
        if connection:
            connection.close()
            
    except Exception as e:
        health_status["rabbitmq"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status

@app.get("/video-count", tags=["Statistics"])
def get_video_count():
    """Get the current video generation count."""
    try:
        r = get_redis()
        count = r.get("video_generation_count")
        return {"count": int(count) if count else 0}
    except Exception as e:
        logger.error(f"Error getting video count: {e}")
        return {"count": 0}

@app.post("/video-count/increment", tags=["Statistics"])
def increment_video_count():
    """Increment the video generation count."""
    try:
        r = get_redis()
        new_count = r.incr("video_generation_count")
        logger.info(f"Video count incremented to {new_count}")
        return {"count": new_count}
    except Exception as e:
        logger.error(f"Error incrementing video count: {e}")
        raise HTTPException(status_code=500, detail="Failed to increment video count")

if __name__ == "__main__":
    from config import API_HOST, API_PORT, API_RELOAD
    uvicorn.run(app, host=API_HOST, port=API_PORT, reload=API_RELOAD)
