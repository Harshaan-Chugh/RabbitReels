# RabbitReels API

FastAPI HTTP gateway for the RabbitReels video generation pipeline.

## Features

- **HTTP Interface**: REST API for video generation requests
- **Status Tracking**: Real-time job status via Redis
- **File Serving**: Direct MP4 download endpoints
- **Theme Discovery**: List available character themes
- **Health Monitoring**: Built-in health checks

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start all services including API
docker-compose up -d

# Check API health
curl http://localhost:8080/health
```

### Local Development

```bash
# Install dependencies
cd api
pip install -r requirements.txt

# Start Redis (required)
docker run -d -p 6379:6379 redis:7-alpine

# Set environment variables
export REDIS_URL="redis://localhost:6379/0"
export RABBIT_URL="amqp://guest:guest@localhost:5672/"
export VIDEO_OUT_DIR="../data/videos"

# Start API server
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

## API Endpoints

### GET /themes
List available character themes.

```bash
curl http://localhost:8080/themes
# Response: ["family_guy", "rick_and_morty"]
```

### POST /videos
Submit a new video generation job.

```bash
curl -X POST http://localhost:8080/videos \
     -H "Content-Type: application/json" \
     -d '{
       "job_id": "my-job-123",
       "prompt": "Explain hash tables",
       "character_theme": "family_guy"
     }'

# Response: {"job_id": "my-job-123", "status": "queued"}
```

### GET /videos/{job_id}
Check job status.

```bash
curl http://localhost:8080/videos/my-job-123

# Responses:
# {"job_id": "my-job-123", "status": "queued"}
# {"job_id": "my-job-123", "status": "rendering", "progress": 0.5}
# {"job_id": "my-job-123", "status": "done", "download_url": "/videos/my-job-123/file"}
# {"job_id": "my-job-123", "status": "error", "error_msg": "..."}
```

### GET /videos/{job_id}/file
Download the finished MP4.

```bash
curl -L -o video.mp4 http://localhost:8080/videos/my-job-123/file
```

### GET /health
Health check endpoint.

```bash
curl http://localhost:8080/health
# Response: {"status": "healthy", "redis": "ok", "rabbitmq": "ok"}
```

## Testing

Run the test script to verify everything works:

```bash
cd api
python test_api.py
```

## Architecture

```
Frontend → API → RabbitMQ → Workers → Video Files
                ↓
              Redis (Status)
```

1. **API receives HTTP requests** and publishes `PromptJob` to `scripts-queue`
2. **script-generator** consumes prompt, generates dialog, publishes `DialogJob` to `video-queue`
3. **video-creator** consumes dialog, renders MP4, publishes `RenderJob` to `publish-queue`
4. **publisher** (optional) uploads to YouTube
5. **API tracks status** by monitoring file system and updating Redis

## Configuration

Key environment variables:

- `RABBIT_URL`: RabbitMQ connection string
- `REDIS_URL`: Redis connection string  
- `VIDEO_OUT_DIR`: Directory where MP4 files are stored
- `API_PORT`: Port to run API server (default: 8080)

## Production Deployment

For production, consider:

1. **Reverse Proxy**: Use nginx/traefik in front of the API
2. **Authentication**: Add JWT/API key authentication
3. **Rate Limiting**: Implement request rate limiting
4. **File Storage**: Use S3/GCS instead of local files
5. **Monitoring**: Add proper logging and metrics
6. **Scaling**: Run multiple API instances behind a load balancer

## Troubleshooting

**API won't start:**
- Check Redis and RabbitMQ are running
- Verify environment variables are set correctly

**Status stuck at "queued":**
- Check that worker containers are running
- Verify RabbitMQ queues are being processed

**File download fails:**
- Check `VIDEO_OUT_DIR` is mounted correctly
- Verify MP4 file exists in the expected location

**Health check fails:**
- Check Redis and RabbitMQ connectivity
- Review API logs for connection errors
