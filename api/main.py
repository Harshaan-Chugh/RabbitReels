import os
import json
import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

import redis
import pika
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from common.schemas import PromptJob, RenderJob, VideoStatus
from config import (
    RABBIT_URL,
    SCRIPTS_QUEUE,
    PUBLISH_QUEUE,
    VIDEO_OUT_DIR,
    REDIS_URL,
    AVAILABLE_THEMES
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for connections
redis_client = None
rabbit_connection = None
rabbit_channel = None  # Type as object since pika types are not exposed
status_consumer_task = None

def get_redis():
    """Get Redis client connection."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return redis_client

def get_rabbit_channel():
    """Get RabbitMQ channel for publishing with retry logic."""
    global rabbit_connection, rabbit_channel
    
    # Always test the connection and channel before using
    connection_is_valid = (
        rabbit_connection is not None and 
        not rabbit_connection.is_closed
    )
    
    channel_is_valid = (
        rabbit_channel is not None and 
        not rabbit_channel.is_closed
    )
    
    # If either connection or channel is invalid, recreate both
    if not connection_is_valid or not channel_is_valid:
        # Clean up existing connections
        if rabbit_channel and not rabbit_channel.is_closed:
            try:
                rabbit_channel.close()
            except:
                pass
                
        if rabbit_connection and not rabbit_connection.is_closed:
            try:
                rabbit_connection.close()
            except:
                pass
        
        rabbit_connection = None
        rabbit_channel = None
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to RabbitMQ (attempt {attempt + 1})")
                rabbit_connection = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
                rabbit_channel = rabbit_connection.channel()
                rabbit_channel.queue_declare(queue=SCRIPTS_QUEUE, durable=True)
                logger.info("RabbitMQ connection established successfully")
                break
            except Exception as e:
                logger.error(f"RabbitMQ connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
    
    return rabbit_channel

async def status_consumer():
    """Background task to consume status updates from RabbitMQ."""
    logger.info("Starting status consumer...")
    
    # For now, we'll implement a simple approach:
    # 1. When jobs are submitted, they start as "queued"
    # 2. We'll have a periodic task to check for completed MP4 files
    # 3. When MP4 exists, we mark status as "done"
    
    while True:
        try:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            r = get_redis()
            # Get all job keys
            job_keys = r.keys("*")
            
            for job_key in job_keys:
                if job_key in ["health", "status"]:  # Skip non-job keys
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
                    
                    # Check if MP4 file exists
                    video_path = os.path.join(VIDEO_OUT_DIR, f"{job_id}.mp4")
                    
                    if os.path.exists(video_path):
                        # Update status to done
                        status_info["status"] = "done"
                        status_info["download_url"] = f"/videos/{job_id}/file"
                        r.set(job_key, json.dumps(status_info))
                        logger.info(f"Updated job {job_id} status to 'done' (file detected)")
                    elif status_info.get("status") == "queued":
                        # Check if it's been queued for a while, assume rendering
                        # This is a simple heuristic - in production you'd want better tracking
                        status_info["status"] = "rendering" 
                        status_info["progress"] = 0.5
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
    
    if rabbit_connection and not rabbit_connection.is_closed:
        try:
            rabbit_connection.close()
            logger.info("RabbitMQ connection closed")
        except:
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

@app.get("/themes", tags=["Themes"])
def list_themes():
    """List available character themes."""
    return AVAILABLE_THEMES

@app.post("/videos", status_code=202, response_model=VideoStatus, tags=["Videos"])
def submit_video(job: PromptJob):
    """Submit a new prompt for video generation."""
    logger.info(f"Received job submission: {job.job_id} with theme '{job.character_theme}' and prompt: '{job.prompt[:50]}...'")
    
    # Validate theme
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
        status_data = {
            "job_id": job.job_id,
            "status": "queued"
        }
        r.set(job.job_id, json.dumps(status_data))
        logger.info(f"Successfully stored initial status for job {job.job_id}")
        
        # Publish to RabbitMQ with retry logic
        logger.info(f"Starting RabbitMQ publish for job {job.job_id}")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                channel = get_rabbit_channel()
                # Test channel before using it
                if channel is None or channel.is_closed:
                    raise Exception("Channel is closed or None")
                    
                channel.basic_publish(
                    exchange="",
                    routing_key=SCRIPTS_QUEUE,
                    body=job.model_dump_json(),
                    properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
                )
                logger.info(f"Job {job.job_id} queued successfully")
                break
            except Exception as e:
                logger.error(f"RabbitMQ publish attempt {attempt + 1} failed: {e}")
                
                # Reset connection for retry
                global rabbit_connection, rabbit_channel
                if rabbit_connection and not rabbit_connection.is_closed:
                    try:
                        rabbit_connection.close()
                    except:
                        pass
                if rabbit_channel and not rabbit_channel.is_closed:
                    try:
                        rabbit_channel.close()
                    except:
                        pass
                rabbit_connection = None
                rabbit_channel = None
                
                if attempt == max_retries - 1:
                    # Update status to error in Redis
                    status_data["status"] = "error"
                    status_data["error_msg"] = f"Failed to queue job after {max_retries} retries: {str(e)}"
                    r.set(job.job_id, json.dumps(status_data))
                    logger.error(f"Final failure for job {job.job_id}: {e}")
                    raise HTTPException(status_code=500, detail="Failed to queue job after retries")
                
                import time
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
        logger.error(f"Error getting status for job {job_id}: {e}")
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
            raise HTTPException(status_code=404, detail="Video not ready")
        
        # Check if file exists locally
        video_path = os.path.join(VIDEO_OUT_DIR, f"{job_id}.mp4")
        
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            raise HTTPException(status_code=404, detail="Video file not found")
        
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
        channel = get_rabbit_channel()
        if channel and not channel.is_closed:
            health_status["rabbitmq"] = "ok"
        else:
            health_status["rabbitmq"] = "channel closed"
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["rabbitmq"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
