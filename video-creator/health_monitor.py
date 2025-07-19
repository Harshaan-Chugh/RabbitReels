#!/usr/bin/env python3
"""
Health Monitor for Video Creator Workers

This module provides health check endpoints and heartbeat functionality
for video creator workers in the auto-scaling system.
"""

import os
import json
import time
import signal
import threading
import redis
from datetime import datetime
from typing import Optional, Dict, Any
from flask import Flask, jsonify
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkerHealthMonitor:
    """Health monitoring system for video creator workers"""
    
    def __init__(self, redis_url: str, worker_id: Optional[str] = None):
        self.redis_url = redis_url
        self.worker_id = worker_id or self._generate_worker_id()
        self.redis_client = None
        self.is_healthy = True
        self.last_heartbeat = datetime.now()
        self.current_job = None
        self.started_at = datetime.now()
        self.jobs_processed = 0
        self.jobs_failed = 0
        self.is_shutting_down = False
        
        # Capacity tracking
        self.job_start_times = {}  # Track job start times for duration calculation
        self.capacity_tracker = None
        
        # Health check server
        self.health_app = Flask(__name__)
        self.health_server = None
        self.health_port = int(os.getenv("HEALTH_CHECK_PORT", "8000"))
        
        # Configuration
        self.heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL", "10"))
        self.graceful_shutdown_timeout = int(os.getenv("GRACEFUL_SHUTDOWN_TIMEOUT", "300"))
        
        # Threading
        self.heartbeat_thread = None
        self.shutdown_event = threading.Event()
        
        # Setup
        self._setup_health_endpoints()
        self._setup_signal_handlers()
        
        logger.info(f"Worker health monitor initialized: {self.worker_id}")
    
    def _generate_worker_id(self) -> str:
        """Generate a unique worker ID"""
        hostname = os.getenv("HOSTNAME", "unknown")
        pid = os.getpid()
        timestamp = int(time.time())
        return f"worker-{hostname}-{pid}-{timestamp}"
    
    def _setup_health_endpoints(self):
        """Setup Flask health check endpoints"""
        @self.health_app.route('/health')
        def health_check():
            """Health check endpoint"""
            return jsonify(self.get_health_status())
        
        @self.health_app.route('/metrics')
        def metrics():
            """Metrics endpoint"""
            return jsonify(self.get_worker_metrics())
        
        @self.health_app.route('/status')
        def status():
            """Detailed status endpoint"""
            return jsonify(self.get_detailed_status())
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.initiate_graceful_shutdown()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    def connect_redis(self) -> bool:
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Connected to Redis for health monitoring")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    def register_worker(self):
        """Register worker with Redis"""
        try:
            if not self.redis_client:
                return False
            
            worker_data = {
                'id': self.worker_id,
                'status': 'active',
                'health_status': 'healthy' if self.is_healthy else 'unhealthy',
                'started_at': self.started_at.isoformat(),
                'last_seen': datetime.now().isoformat(),
                'current_job': self.current_job,
                'jobs_processed': self.jobs_processed,
                'jobs_failed': self.jobs_failed,
                'is_shutting_down': self.is_shutting_down,
                'health_check_port': self.health_port
            }
            
            self.redis_client.hset('scaling_workers', self.worker_id, json.dumps(worker_data))
            logger.info(f"Worker registered: {self.worker_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register worker: {e}")
            return False
    
    def update_heartbeat(self):
        """Update worker heartbeat in Redis"""
        try:
            if not self.redis_client:
                return False
            
            self.last_heartbeat = datetime.now()
            
            # Get current worker data
            worker_data_str = self.redis_client.hget('scaling_workers', self.worker_id)
            if worker_data_str:
                worker_data = json.loads(worker_data_str)
            else:
                worker_data = {}
            
            # Update with current status
            worker_data.update({
                'health_status': 'healthy' if self.is_healthy else 'unhealthy',
                'last_seen': self.last_heartbeat.isoformat(),
                'current_job': self.current_job,
                'jobs_processed': self.jobs_processed,
                'jobs_failed': self.jobs_failed,
                'is_shutting_down': self.is_shutting_down
            })
            
            self.redis_client.hset('scaling_workers', self.worker_id, json.dumps(worker_data))
            return True
            
        except Exception as e:
            logger.error(f"Failed to update heartbeat: {e}")
            return False
    
    def unregister_worker(self):
        """Unregister worker from Redis"""
        try:
            if not self.redis_client:
                return False
            
            self.redis_client.hdel('scaling_workers', self.worker_id)
            logger.info(f"Worker unregistered: {self.worker_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister worker: {e}")
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return {
            'worker_id': self.worker_id,
            'status': 'healthy' if self.is_healthy else 'unhealthy',
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'current_job': self.current_job,
            'is_shutting_down': self.is_shutting_down,
            'uptime_seconds': (datetime.now() - self.started_at).total_seconds()
        }
    
    def get_worker_metrics(self) -> Dict[str, Any]:
        """Get worker performance metrics"""
        uptime = datetime.now() - self.started_at
        
        return {
            'worker_id': self.worker_id,
            'jobs_processed': self.jobs_processed,
            'jobs_failed': self.jobs_failed,
            'success_rate': self.jobs_processed / (self.jobs_processed + self.jobs_failed) if (self.jobs_processed + self.jobs_failed) > 0 else 0,
            'uptime_seconds': uptime.total_seconds(),
            'jobs_per_hour': (self.jobs_processed / uptime.total_seconds()) * 3600 if uptime.total_seconds() > 0 else 0
        }
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed worker status"""
        return {
            'worker_id': self.worker_id,
            'health': self.get_health_status(),
            'metrics': self.get_worker_metrics(),
            'config': {
                'heartbeat_interval': self.heartbeat_interval,
                'graceful_shutdown_timeout': self.graceful_shutdown_timeout,
                'health_check_port': self.health_port
            }
        }
    
    def set_current_job(self, job_id: str):
        """Set the current job being processed"""
        self.current_job = job_id
        self.job_start_times[job_id] = datetime.now()
        logger.info(f"Worker {self.worker_id} started processing job: {job_id}")
    
    def job_completed(self, job_id: str, success: bool = True):
        """Mark current job as completed"""
        job_duration = 0
        if job_id in self.job_start_times:
            job_duration = (datetime.now() - self.job_start_times[job_id]).total_seconds()
            del self.job_start_times[job_id]
        
        if success:
            self.jobs_processed += 1
            logger.info(f"Worker {self.worker_id} completed job: {job_id} in {job_duration:.1f}s")
        else:
            self.jobs_failed += 1
            logger.error(f"Worker {self.worker_id} failed job: {job_id} after {job_duration:.1f}s")
        
        # Update capacity tracker
        self._update_capacity_metrics(job_duration, success)
        
        self.current_job = None
        self.update_heartbeat()
    
    def set_health_status(self, healthy: bool, reason: str = ""):
        """Set worker health status"""
        self.is_healthy = healthy
        status = "healthy" if healthy else "unhealthy"
        logger.info(f"Worker {self.worker_id} health status: {status} - {reason}")
        self.update_heartbeat()
    
    def initiate_graceful_shutdown(self):
        """Initiate graceful shutdown process"""
        self.is_shutting_down = True
        self.is_healthy = False
        
        logger.info(f"Worker {self.worker_id} initiating graceful shutdown...")
        
        # Update Redis to indicate shutdown
        self.update_heartbeat()
        
        # Set shutdown event
        self.shutdown_event.set()
        
        # If there's a current job, wait for it to complete
        if self.current_job:
            logger.info(f"Waiting for current job {self.current_job} to complete...")
            # This will be handled by the main video creator loop
        
        # Stop heartbeat thread
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
        
        # Unregister worker
        self.unregister_worker()
        
        logger.info(f"Worker {self.worker_id} graceful shutdown completed")
    
    def start_heartbeat_thread(self):
        """Start the heartbeat thread"""
        def heartbeat_loop():
            while not self.shutdown_event.is_set():
                try:
                    self.update_heartbeat()
                    time.sleep(self.heartbeat_interval)
                except Exception as e:
                    logger.error(f"Error in heartbeat loop: {e}")
                    time.sleep(5)
        
        self.heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        logger.info(f"Heartbeat thread started for worker {self.worker_id}")
    
    def start_health_server(self):
        """Start the health check server"""
        def run_server():
            try:
                self.health_app.run(
                    host='0.0.0.0',
                    port=self.health_port,
                    debug=False,
                    use_reloader=False,
                    threaded=True
                )
            except Exception as e:
                logger.error(f"Health server error: {e}")
        
        self.health_server = threading.Thread(target=run_server, daemon=True)
        self.health_server.start()
        logger.info(f"Health server started on port {self.health_port}")
    
    def start(self):
        """Start the health monitoring system"""
        logger.info(f"Starting health monitor for worker {self.worker_id}")
        
        # Connect to Redis
        if not self.connect_redis():
            logger.error("Failed to connect to Redis, health monitoring disabled")
            return False
        
        # Initialize capacity tracker
        try:
            import sys
            import os
            sys.path.append('/app/scaling-controller')
            from capacity_tracker import CapacityTracker
            
            self.capacity_tracker = CapacityTracker(self.redis_url)
            if self.capacity_tracker.connect_redis():
                logger.info("Capacity tracker initialized")
            else:
                logger.warning("Failed to initialize capacity tracker")
                self.capacity_tracker = None
        except Exception as e:
            logger.warning(f"Failed to initialize capacity tracker: {e}")
            self.capacity_tracker = None
        
        # Register worker
        if not self.register_worker():
            logger.error("Failed to register worker")
            return False
        
        # Start health server
        self.start_health_server()
        
        # Start heartbeat thread
        self.start_heartbeat_thread()
        
        logger.info(f"Health monitor started for worker {self.worker_id}")
        return True
    
    def stop(self):
        """Stop the health monitoring system"""
        logger.info(f"Stopping health monitor for worker {self.worker_id}")
        self.initiate_graceful_shutdown()
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown was requested"""
        return self.shutdown_event.is_set()
    
    def should_accept_new_jobs(self) -> bool:
        """Check if worker should accept new jobs based on health and capacity"""
        if not self.is_healthy or self.is_shutting_down:
            return False
        
        # Check capacity limits
        if self.capacity_tracker:
            try:
                capacity = self.capacity_tracker.get_worker_capacity(self.worker_id)
                if capacity:
                    current_jobs = len([job for job in self.job_start_times.keys()])
                    if current_jobs >= capacity.concurrent_job_limit:
                        logger.debug(f"Worker {self.worker_id} at capacity limit: {current_jobs}/{capacity.concurrent_job_limit}")
                        return False
            except Exception as e:
                logger.warning(f"Failed to check capacity: {e}")
        
        return True
    
    def _update_capacity_metrics(self, job_duration: float, job_success: bool):
        """Update capacity metrics for this worker"""
        if not self.capacity_tracker:
            return
        
        try:
            # Get basic resource usage (simplified - in production, use psutil)
            import psutil
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_usage = psutil.virtual_memory().percent
            disk_usage = psutil.disk_usage('/').percent
        except ImportError:
            # Fallback if psutil not available
            cpu_usage = 50.0  # Default values
            memory_usage = 60.0
            disk_usage = 30.0
        except Exception:
            cpu_usage = 50.0
            memory_usage = 60.0
            disk_usage = 30.0
        
        current_jobs = len([job for job in self.job_start_times.keys()])
        
        try:
            self.capacity_tracker.update_worker_capacity(
                worker_id=self.worker_id,
                jobs_completed=1 if job_duration > 0 else 0,
                job_duration=job_duration,
                job_success=job_success,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                current_jobs=current_jobs
            )
        except Exception as e:
            logger.warning(f"Failed to update capacity metrics: {e}")

# Global health monitor instance
health_monitor = None

def initialize_health_monitor(redis_url: str, worker_id: Optional[str] = None) -> WorkerHealthMonitor:
    """Initialize the global health monitor"""
    global health_monitor
    health_monitor = WorkerHealthMonitor(redis_url, worker_id)
    return health_monitor

def get_health_monitor() -> Optional[WorkerHealthMonitor]:
    """Get the global health monitor instance"""
    return health_monitor 