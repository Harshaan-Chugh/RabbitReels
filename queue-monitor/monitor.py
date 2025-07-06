#!/usr/bin/env python3
"""
Queue Monitor Service for RabbitReels Auto-Scaling

This service monitors RabbitMQ queue depth and worker capacity to provide
metrics for scaling decisions.
"""

import pika
import redis
import time
import json
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
from threading import Thread, Event

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class QueueMetrics:
    """Metrics collected from queue and workers"""
    queue_depth: int
    active_workers: int
    healthy_workers: int
    avg_processing_time: float
    queue_throughput: float
    timestamp: datetime
    scaling_recommendation: str  # "scale_up", "scale_down", "maintain"
    target_workers: int

class QueueMonitor:
    """Monitor RabbitMQ queue depth and worker capacity"""
    
    def __init__(self, rabbit_url: str, redis_url: str, video_queue: str = "video-queue"):
        self.rabbit_url = rabbit_url
        self.redis_url = redis_url
        self.video_queue = video_queue
        self.redis_client = None
        self.running = False
        self.stop_event = Event()
        
        # Configuration
        self.min_workers = int(os.getenv("MIN_WORKERS", "1"))
        self.max_workers = int(os.getenv("MAX_WORKERS", "10"))
        self.scale_up_threshold = float(os.getenv("SCALE_UP_THRESHOLD", "2"))
        self.scale_down_threshold = float(os.getenv("SCALE_DOWN_THRESHOLD", "0.5"))
        self.cooldown_period = int(os.getenv("COOLDOWN_PERIOD", "60"))
        self.collection_interval = int(os.getenv("METRICS_COLLECTION_INTERVAL", "15"))
        
        # Metrics tracking
        self.last_scaling_action = datetime.now() - timedelta(seconds=self.cooldown_period)
        self.processing_times = []
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        logger.info(f"Queue Monitor initialized with config: "
                   f"min_workers={self.min_workers}, max_workers={self.max_workers}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop_event.set()
        self.running = False
    
    def connect_redis(self) -> bool:
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Connected to Redis")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    def get_queue_depth(self) -> int:
        """Get current queue depth from RabbitMQ"""
        try:
            connection = pika.BlockingConnection(pika.URLParameters(self.rabbit_url))
            channel = connection.channel()
            
            # Declare queue to ensure it exists
            channel.queue_declare(queue=self.video_queue, durable=True)
            
            # Get queue info
            method = channel.queue_declare(queue=self.video_queue, durable=True, passive=True)
            queue_depth = method.method.message_count
            
            connection.close()
            return queue_depth
            
        except Exception as e:
            logger.error(f"Failed to get queue depth: {e}")
            return 0
    
    def get_active_workers(self) -> int:
        """Get count of active workers from Redis"""
        try:
            if not self.redis_client:
                return 0
            
            # Count active workers in Redis hash
            workers = self.redis_client.hgetall('video_workers')
            active_count = 0
            
            for worker_id, worker_data_str in workers.items():
                try:
                    worker_data = json.loads(worker_data_str)
                    if worker_data.get('status') == 'active':
                        # Check if worker is still alive (last_seen within 2 minutes)
                        last_seen = datetime.fromisoformat(worker_data.get('last_seen', ''))
                        if datetime.now() - last_seen < timedelta(minutes=2):
                            active_count += 1
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Invalid worker data for {worker_id}: {e}")
                    continue
            
            return active_count
            
        except Exception as e:
            logger.error(f"Failed to get active workers: {e}")
            return 0
    
    def get_healthy_workers(self) -> int:
        """Get count of healthy workers from Redis"""
        try:
            if not self.redis_client:
                return 0
            
            # Count healthy workers
            workers = self.redis_client.hgetall('video_workers')
            healthy_count = 0
            
            for worker_id, worker_data_str in workers.items():
                try:
                    worker_data = json.loads(worker_data_str)
                    if (worker_data.get('status') == 'active' and 
                        worker_data.get('health_status') == 'healthy'):
                        healthy_count += 1
                except (json.JSONDecodeError, ValueError):
                    continue
            
            return healthy_count
            
        except Exception as e:
            logger.error(f"Failed to get healthy workers: {e}")
            return 0
    
    def get_avg_processing_time(self) -> float:
        """Get average processing time from recent jobs"""
        try:
            if not self.redis_client:
                return 0.0
            
            # Get recent processing times (last 10 jobs)
            times = self.redis_client.lrange('processing_times', 0, 9)
            if not times:
                return 0.0
            
            # Convert to float and calculate average
            float_times = [float(t) for t in times]
            return sum(float_times) / len(float_times)
            
        except Exception as e:
            logger.error(f"Failed to get average processing time: {e}")
            return 0.0
    
    def get_queue_throughput(self) -> float:
        """Get queue throughput (jobs per minute)"""
        try:
            if not self.redis_client:
                return 0.0
            
            # Get completed jobs count from the last minute
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)
            
            # This would require tracking job completion times
            # For now, return a calculated estimate based on active workers
            active_workers = self.get_active_workers()
            avg_time = self.get_avg_processing_time()
            
            if avg_time > 0:
                return (active_workers * 60) / avg_time  # jobs per minute
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to get queue throughput: {e}")
            return 0.0
    
    def calculate_scaling_decision(self, metrics: QueueMetrics) -> Dict[str, Any]:
        """Calculate if scaling up/down is needed"""
        now = datetime.now()
        
        # Check cooldown period
        if now - self.last_scaling_action < timedelta(seconds=self.cooldown_period):
            return {
                'action': 'maintain',
                'reason': 'cooldown_period_active',
                'target_workers': metrics.active_workers
            }
        
        queue_depth = metrics.queue_depth
        active_workers = metrics.active_workers
        healthy_workers = metrics.healthy_workers
        
        # Calculate target workers based on queue depth
        if queue_depth == 0:
            # Keep minimum workers for quick response
            target_workers = max(1, min(active_workers, 2))
        else:
            # Scale up: 1 worker per 1-2 jobs in queue
            target_workers = min(queue_depth + 1, self.max_workers)
        
        # Ensure we have minimum workers
        target_workers = max(target_workers, self.min_workers)
        
        # Determine scaling action
        if target_workers > active_workers:
            # Only scale up if we have healthy workers or queue is growing
            if healthy_workers >= active_workers * 0.8:  # 80% healthy threshold
                return {
                    'action': 'scale_up',
                    'reason': f'queue_depth={queue_depth}, active_workers={active_workers}',
                    'target_workers': target_workers
                }
        elif target_workers < active_workers:
            # Scale down if queue is manageable
            if queue_depth < active_workers * self.scale_down_threshold:
                return {
                    'action': 'scale_down',
                    'reason': f'queue_depth={queue_depth}, over_provisioned',
                    'target_workers': target_workers
                }
        
        return {
            'action': 'maintain',
            'reason': 'stable_state',
            'target_workers': active_workers
        }
    
    def collect_metrics(self) -> QueueMetrics:
        """Collect all metrics"""
        queue_depth = self.get_queue_depth()
        active_workers = self.get_active_workers()
        healthy_workers = self.get_healthy_workers()
        avg_processing_time = self.get_avg_processing_time()
        queue_throughput = self.get_queue_throughput()
        
        metrics = QueueMetrics(
            queue_depth=queue_depth,
            active_workers=active_workers,
            healthy_workers=healthy_workers,
            avg_processing_time=avg_processing_time,
            queue_throughput=queue_throughput,
            timestamp=datetime.now(),
            scaling_recommendation="maintain",
            target_workers=active_workers
        )
        
        # Calculate scaling decision
        scaling_decision = self.calculate_scaling_decision(metrics)
        metrics.scaling_recommendation = scaling_decision['action']
        metrics.target_workers = scaling_decision['target_workers']
        
        return metrics
    
    def publish_metrics(self, metrics: QueueMetrics):
        """Publish metrics to Redis for scaling controller"""
        try:
            if not self.redis_client:
                return
            
            # Publish current metrics
            metrics_data = {
                'queue_depth': metrics.queue_depth,
                'active_workers': metrics.active_workers,
                'healthy_workers': metrics.healthy_workers,
                'avg_processing_time': metrics.avg_processing_time,
                'queue_throughput': metrics.queue_throughput,
                'timestamp': metrics.timestamp.isoformat(),
                'scaling_recommendation': metrics.scaling_recommendation,
                'target_workers': metrics.target_workers
            }
            
            # Store current metrics
            self.redis_client.set('current_metrics', json.dumps(metrics_data))
            
            # Store historical metrics (keep last 100 entries)
            self.redis_client.lpush('metrics_history', json.dumps(metrics_data))
            self.redis_client.ltrim('metrics_history', 0, 99)
            
            # Publish scaling recommendation
            if metrics.scaling_recommendation != 'maintain':
                scaling_msg = {
                    'action': metrics.scaling_recommendation,
                    'target_workers': metrics.target_workers,
                    'timestamp': metrics.timestamp.isoformat(),
                    'reason': 'queue_monitor_recommendation'
                }
                self.redis_client.publish('scaling_events', json.dumps(scaling_msg))
                
                # Update last scaling action time
                self.last_scaling_action = datetime.now()
            
            logger.info(f"Published metrics: depth={metrics.queue_depth}, "
                       f"workers={metrics.active_workers}, "
                       f"healthy={metrics.healthy_workers}, "
                       f"recommendation={metrics.scaling_recommendation}")
            
        except Exception as e:
            logger.error(f"Failed to publish metrics: {e}")
    
    def run_monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting queue monitoring loop...")
        
        while self.running and not self.stop_event.is_set():
            try:
                # Collect metrics
                metrics = self.collect_metrics()
                
                # Publish metrics
                self.publish_metrics(metrics)
                
                # Log current status
                logger.info(f"Queue depth: {metrics.queue_depth}, "
                           f"Active workers: {metrics.active_workers}, "
                           f"Healthy workers: {metrics.healthy_workers}, "
                           f"Recommendation: {metrics.scaling_recommendation}")
                
                # Wait for next collection interval
                time.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Wait before retrying
    
    def start(self):
        """Start the queue monitor"""
        logger.info("Starting Queue Monitor...")
        
        # Connect to Redis
        if not self.connect_redis():
            logger.error("Failed to connect to Redis, exiting...")
            return
        
        self.running = True
        
        # Start monitoring loop
        self.run_monitoring_loop()
        
        logger.info("Queue Monitor stopped")
    
    def stop(self):
        """Stop the queue monitor"""
        logger.info("Stopping Queue Monitor...")
        self.running = False
        self.stop_event.set()

def main():
    """Main entry point"""
    # Get configuration from environment
    rabbit_url = os.getenv("RABBIT_URL", "amqp://guest:guest@rabbitmq:5672/")
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    video_queue = os.getenv("VIDEO_QUEUE", "video-queue")
    
    if not rabbit_url:
        logger.error("RABBIT_URL environment variable is required")
        sys.exit(1)
    
    if not redis_url:
        logger.error("REDIS_URL environment variable is required")
        sys.exit(1)
    
    # Create and start monitor
    monitor = QueueMonitor(rabbit_url, redis_url, video_queue)
    
    try:
        monitor.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        monitor.stop()

if __name__ == "__main__":
    main() 