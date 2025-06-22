#!/usr/bin/env python3
"""
Test script to verify the video creator fix by publishing directly to video-queue
"""
import json
import uuid
import pika
import redis

# Configuration
RABBIT_URL = "amqp://guest:guest@localhost:5672/"
VIDEO_QUEUE = "video-queue"
REDIS_URL = "redis://localhost:6379/0"

def test_video_creation():
    """Test video creation by publishing directly to video-queue."""
    test_job_id = f"test-fix-{uuid.uuid4().hex[:8]}"
    
    print(f"🧪 Testing video creator fix")
    print(f"Test Job ID: {test_job_id}")
    print()
    
    # Create test DialogJob message
    dialog_job = {
        "job_id": test_job_id,
        "title": "Test Fix Video",
        "character_theme": "family_guy",
        "turns": [
            {
                "speaker": "stewie",
                "text": "Peter, what is a hash table?"
            },
            {
                "speaker": "peter",
                "text": "Oh that's easy Stewie! A hash table is like a phone book where you can look up anyone's number super fast!"
            },
            {
                "speaker": "stewie",
                "text": "Fascinating! How does it work so quickly?"
            },
            {
                "speaker": "peter",
                "text": "Well, it uses a special hash function to turn your search into a magic number that points right to the answer!"
            }
        ]
    }
    
    # Set initial status in Redis
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        status_data = {
            "job_id": test_job_id,
            "status": "queued",
            "submitted_at": int(time.time())
        }
        r.set(test_job_id, json.dumps(status_data))
        print(f"✅ Set initial Redis status for {test_job_id}")
    except Exception as e:
        print(f"❌ Failed to set Redis status: {e}")
        return
    
    # Publish to RabbitMQ video-queue
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
        channel = connection.channel()
        
        # Declare the queue to make sure it exists
        channel.queue_declare(queue=VIDEO_QUEUE, durable=True)
        
        # Publish the message
        channel.basic_publish(
            exchange="",
            routing_key=VIDEO_QUEUE,
            body=json.dumps(dialog_job),
            properties=pika.BasicProperties(delivery_mode=2)  # Make message persistent
        )
        
        connection.close()
        print(f"✅ Published test job to {VIDEO_QUEUE}")
        
    except Exception as e:
        print(f"❌ Failed to publish to RabbitMQ: {e}")
        return
    
    print(f"\n🎬 Video creation job submitted!")
    print(f"Job ID: {test_job_id}")
    print(f"You can monitor the job by checking:")
    print(f"- Redis status: docker exec rabbitreels-redis-1 redis-cli GET {test_job_id}")
    print(f"- Video creator logs: docker logs rabbitreels-video-creator-1 --tail 50")
    print(f"- Download URL (when done): http://localhost:8080/videos/{test_job_id}/file")

if __name__ == "__main__":
    import time
    test_video_creation()
