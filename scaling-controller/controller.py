#!/usr/bin/env python3
"""
Scaling Controller for RabbitReels Auto-Scaling

This service manages video creator instances based on queue metrics and scaling decisions.
Supports both Docker Compose and Docker Swarm deployments.
"""

import os
import sys
import time
import json
import signal
import logging
import docker
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from threading import Thread, Event
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScalingAction(Enum):
    """Scaling actions"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    MAINTAIN = "maintain"

@dataclass
class ScalingEvent:
    """Scaling event data"""
    action: ScalingAction
    target_workers: int
    current_workers: int
    queue_depth: int
    timestamp: datetime
    reason: str

class ScalingController:
    """
    Scaling controller that manages video creator instances
    """
    
    def __init__(self, redis_url: str, docker_host: Optional[str] = None):
        self.redis_url = redis_url
        self.redis_client = None
        self.docker_client = None
        self.docker_host = docker_host
        self.running = False
        self.stop_event = Event()
        
        # Configuration
        self.min_workers = int(os.getenv("MIN_WORKERS", "1"))
        self.max_workers = int(os.getenv("MAX_WORKERS", "10"))
        self.cooldown_period = int(os.getenv("COOLDOWN_PERIOD", "60"))
        self.check_interval = int(os.getenv("SCALING_CHECK_INTERVAL", "30"))
        self.service_name = os.getenv("VIDEO_CREATOR_SERVICE", "video-creator")
        self.image_name = os.getenv("VIDEO_CREATOR_IMAGE", "rabbitreels/video-creator:latest")
        self.network_name = os.getenv("DOCKER_NETWORK", "rabbitreels-network")
        
        # Job-aware scaling configuration
        self.job_drain_timeout = int(os.getenv("JOB_DRAIN_TIMEOUT", "1800"))  # 30 minutes
        self.graceful_shutdown_timeout = int(os.getenv("GRACEFUL_SHUTDOWN_TIMEOUT", "300"))  # 5 minutes
        
        # Scaling state
        self.last_scaling_action = datetime.now() - timedelta(seconds=self.cooldown_period)
        self.scaling_history: List[ScalingEvent] = []
        self.last_job_completion_check = datetime.now()
        
        # Enhanced cooldown tracking
        self.scaling_reasons = {}
        self.job_completion_cooldown = int(os.getenv("JOB_COMPLETION_COOLDOWN", "120"))  # 2 minutes
        
        # Docker deployment mode
        self.deployment_mode = os.getenv("DEPLOYMENT_MODE", "compose")  # "compose" or "swarm"
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        logger.info(f"Scaling Controller initialized: "
                   f"min_workers={self.min_workers}, max_workers={self.max_workers}, "
                   f"mode={self.deployment_mode}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
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
    
    def connect_docker(self) -> bool:
        """Connect to Docker"""
        connection_methods = [
            ("from_env", lambda: docker.from_env()),
            ("unix_socket", lambda: docker.DockerClient(base_url="unix:///var/run/docker.sock")),
            ("npipe", lambda: docker.DockerClient(base_url="npipe:////./pipe/docker_engine")),
            ("tcp", lambda: docker.DockerClient(base_url="tcp://localhost:2375")),
        ]
        
        for method_name, method_func in connection_methods:
            try:
                logger.info(f"Trying Docker connection method: {method_name}")
                self.docker_client = method_func()
                self.docker_client.ping()
                logger.info(f"Connected to Docker via {method_name} ({self.deployment_mode} mode)")
                return True
            except Exception as e:
                logger.debug(f"Docker connection method {method_name} failed: {e}")
                continue
        
        logger.error("All Docker connection methods failed")
        return False
    
    def get_current_metrics(self) -> Optional[Dict[str, Any]]:
        """Get current metrics from Redis"""
        try:
            if not self.redis_client:
                return None
            
            metrics_str = self.redis_client.get('current_metrics')
            if not metrics_str:
                return None
            
            return json.loads(metrics_str)
        except Exception as e:
            logger.error(f"Failed to get current metrics: {e}")
            return None
    
    def get_current_workers_count(self) -> int:
        """Get current number of worker instances"""
        try:
            if not self.docker_client:
                return 0
            
            if self.deployment_mode == "swarm":
                return self._get_swarm_workers_count()
            else:
                return self._get_compose_workers_count()
        except Exception as e:
            logger.error(f"Failed to get current workers count: {e}")
            return 0
    
    def _get_swarm_workers_count(self) -> int:
        """Get worker count in Docker Swarm mode"""
        try:
            services = self.docker_client.services.list(
                filters={"name": self.service_name}
            )
            
            if not services:
                logger.warning(f"Service {self.service_name} not found")
                return 0
            
            service = services[0]
            replicas = service.attrs['Spec']['Mode']['Replicated']['Replicas']
            return replicas
        except Exception as e:
            logger.error(f"Failed to get swarm workers count: {e}")
            return 0
    
    def _get_compose_workers_count(self) -> int:
        """Get worker count in Docker Compose mode"""
        try:
            containers = self.docker_client.containers.list(
                filters={"name": self.service_name}
            )
            return len(containers)
        except Exception as e:
            logger.error(f"Failed to get compose workers count: {e}")
            return 0
    
    def scale_workers(self, target_count: int, reason: str) -> bool:
        """Scale workers to target count"""
        try:
            current_count = self.get_current_workers_count()
            
            if current_count == target_count:
                logger.info(f"Already at target worker count: {target_count}")
                return True
            
            logger.info(f"Scaling workers from {current_count} to {target_count}: {reason}")
            
            if self.deployment_mode == "swarm":
                success = self._scale_swarm_workers(target_count)
            else:
                success = self._scale_compose_workers(target_count)
            
            if success:
                # Record scaling event
                action = ScalingAction.SCALE_UP if target_count > current_count else ScalingAction.SCALE_DOWN
                event = ScalingEvent(
                    action=action,
                    target_workers=target_count,
                    current_workers=current_count,
                    queue_depth=self._get_queue_depth(),
                    timestamp=datetime.now(),
                    reason=reason
                )
                self.scaling_history.append(event)
                
                # Keep only last 100 scaling events
                if len(self.scaling_history) > 100:
                    self.scaling_history = self.scaling_history[-100:]
                
                # Update last scaling action time
                self.last_scaling_action = datetime.now()
                
                # Store scaling event in Redis
                self._store_scaling_event(event)
                
                logger.info(f"Successfully scaled workers to {target_count}")
                return True
            else:
                logger.error(f"Failed to scale workers to {target_count}")
                return False
                
        except Exception as e:
            logger.error(f"Error scaling workers: {e}")
            return False
    
    def _scale_swarm_workers(self, target_count: int) -> bool:
        """Scale workers in Docker Swarm mode"""
        try:
            services = self.docker_client.services.list(
                filters={"name": self.service_name}
            )
            
            if not services:
                logger.error(f"Service {self.service_name} not found")
                return False
            
            service = services[0]
            service.scale(target_count)
            
            # Wait for scaling to complete
            self._wait_for_scaling_complete(target_count)
            
            return True
        except Exception as e:
            logger.error(f"Failed to scale swarm workers: {e}")
            return False
    
    def _scale_compose_workers(self, target_count: int) -> bool:
        """Scale workers in Docker Compose mode with graceful job draining"""
        try:
            current_containers = self.docker_client.containers.list(
                filters={"name": self.service_name}
            )
            current_count = len(current_containers)
            
            if target_count > current_count:
                # Scale up - create new containers
                for i in range(current_count, target_count):
                    container_name = f"{self.service_name}-{i+1}"
                    
                    # Get environment variables from existing container
                    env_vars = {}
                    if current_containers:
                        env_vars = current_containers[0].attrs['Config']['Env']
                    
                    # Add worker-specific environment variables
                    env_vars.append(f"WORKER_ID={container_name}")
                    env_vars.append(f"HEALTH_CHECK_PORT={8000 + i}")
                    
                    self.docker_client.containers.run(
                        image=self.image_name,
                        name=container_name,
                        environment=env_vars,
                        network=self.network_name,
                        detach=True,
                        restart_policy={"Name": "on-failure", "MaximumRetryCount": 3}
                    )
                    
                    logger.info(f"Created container: {container_name}")
                
            elif target_count < current_count:
                # Scale down with graceful job draining
                containers_to_remove = current_containers[target_count:]
                
                # First, mark workers for shutdown (stop accepting new jobs)
                for container in containers_to_remove:
                    worker_id = container.name
                    self._mark_worker_for_shutdown(worker_id)
                
                # Wait for current jobs to complete
                max_drain_time = int(os.getenv("JOB_DRAIN_TIMEOUT", "900"))  # 15 minutes
                if self._wait_for_job_completion(containers_to_remove, max_drain_time):
                    logger.info("All jobs completed, proceeding with container removal")
                else:
                    logger.warning("Job drain timeout reached, forcing container removal")
                
                # Remove containers
                for container in containers_to_remove:
                    try:
                        # Send graceful shutdown signal
                        container.kill(signal="SIGTERM")
                        
                        # Wait for graceful shutdown
                        container.wait(timeout=60)  # Reduced timeout since jobs should be done
                        
                        # Remove container
                        container.remove()
                        
                        logger.info(f"Removed container: {container.name}")
                    except Exception as e:
                        logger.error(f"Failed to remove container {container.name}: {e}")
                        # Force remove if graceful shutdown fails
                        try:
                            container.kill()
                            container.remove(force=True)
                        except:
                            pass
            
            return True
        except Exception as e:
            logger.error(f"Failed to scale compose workers: {e}")
            return False
    
    def _wait_for_scaling_complete(self, target_count: int, timeout: int = 120):
        """Wait for scaling to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_count = self.get_current_workers_count()
            if current_count == target_count:
                return True
            
            time.sleep(2)
        
        logger.warning(f"Scaling did not complete within {timeout} seconds")
        return False
    
    def _get_queue_depth(self) -> int:
        """Get current queue depth"""
        try:
            metrics = self.get_current_metrics()
            if metrics:
                return metrics.get('queue_depth', 0)
            return 0
        except Exception:
            return 0
    
    def _store_scaling_event(self, event: ScalingEvent):
        """Store scaling event in Redis"""
        try:
            if not self.redis_client:
                return
            
            event_data = {
                'action': event.action.value,
                'target_workers': event.target_workers,
                'current_workers': event.current_workers,
                'queue_depth': event.queue_depth,
                'timestamp': event.timestamp.isoformat(),
                'reason': event.reason
            }
            
            # Store in scaling history
            self.redis_client.lpush('scaling_history', json.dumps(event_data))
            self.redis_client.ltrim('scaling_history', 0, 99)  # Keep last 100 events
            
            # Publish scaling event
            self.redis_client.publish('scaling_events', json.dumps(event_data))
            
        except Exception as e:
            logger.error(f"Failed to store scaling event: {e}")
    
    def check_and_scale(self):
        """Check metrics and scale if needed"""
        try:
            # Get current metrics
            metrics = self.get_current_metrics()
            if not metrics:
                logger.debug("No metrics available, skipping scaling check")
                return
            
            # Check cooldown period with job completion awareness
            now = datetime.now()
            if now - self.last_scaling_action < timedelta(seconds=self.cooldown_period):
                # During cooldown, still check if we have urgent scaling needs
                job_stats = self.get_job_statistics()
                processing_jobs = job_stats.get('processing_jobs', 0)
                pending_jobs = job_stats.get('pending_jobs', 0)
                
                # Enhanced cooldown override logic
                cooldown_remaining = (self.cooldown_period - (now - self.last_scaling_action).total_seconds())
                
                # Allow scaling up during cooldown if:
                # 1. Queue is backing up significantly
                # 2. Recent job completions indicate workers are available
                # 3. Capacity utilization is very high
                should_override = False
                override_reason = ""
                
                if pending_jobs > current_workers * 3:
                    should_override = True
                    override_reason = f"high queue depth: {pending_jobs} pending jobs"
                elif self._recent_job_completions() > current_workers * 0.5:
                    should_override = True
                    override_reason = "recent job completions indicate available capacity"
                elif self._get_capacity_utilization() > 0.9:
                    should_override = True
                    override_reason = "very high capacity utilization"
                
                if should_override:
                    logger.info(f"Overriding cooldown ({cooldown_remaining:.1f}s remaining) due to {override_reason}")
                else:
                    logger.debug(f"Cooldown period active ({cooldown_remaining:.1f}s remaining), skipping scaling check")
                    return
            
            # Get current state
            queue_depth = metrics.get('queue_depth', 0)
            current_workers = self.get_current_workers_count()
            healthy_workers = metrics.get('healthy_workers', current_workers)
            
            # Calculate target workers
            target_workers = self.calculate_target_workers(queue_depth, current_workers, healthy_workers)
            
            # Determine scaling action
            if target_workers > current_workers:
                reason = f"Queue depth: {queue_depth}, Current workers: {current_workers}"
                self.scale_workers(target_workers, reason)
            elif target_workers < current_workers:
                reason = f"Queue depth: {queue_depth}, Over-provisioned workers: {current_workers}"
                self.scale_workers(target_workers, reason)
            else:
                logger.debug(f"No scaling needed: queue={queue_depth}, workers={current_workers}")
                
        except Exception as e:
            logger.error(f"Error in check_and_scale: {e}")
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """Get job processing statistics from job manager"""
        try:
            import sys
            import os
            sys.path.append('/app/scaling-controller')
            from job_manager import JobManager
            
            job_manager = JobManager(self.redis_url)
            if job_manager.connect_redis():
                return job_manager.get_job_statistics()
            return {}
        except Exception as e:
            logger.error(f"Failed to get job statistics: {e}")
            return {}
    
    def calculate_target_workers(self, queue_depth: int, current_workers: int, healthy_workers: int) -> int:
        """Calculate target number of workers with job awareness"""
        # Get job statistics for informed decisions
        job_stats = self.get_job_statistics()
        processing_jobs = job_stats.get('processing_jobs', 0)
        workers_with_jobs = job_stats.get('workers_with_jobs', 0)
        avg_processing_time = job_stats.get('average_processing_time', 0)
        
        if queue_depth == 0 and processing_jobs == 0:
            # No work, scale down to minimum but keep some workers ready
            return max(self.min_workers, min(current_workers, 2))
        
        # Calculate based on total workload
        total_workload = queue_depth + processing_jobs
        
        # Estimate target workers based on job processing time
        if avg_processing_time > 0:
            # If jobs take a long time, we need more workers
            time_factor = min(avg_processing_time / 300, 2.0)  # Cap at 2x for 5+ minute jobs
            target = max(total_workload, int(total_workload * time_factor))
        else:
            # Default scaling: 1 worker per 1-2 jobs
            target = max(total_workload, total_workload // 2 + 1)
        
        # Apply constraints
        target = max(self.min_workers, min(target, self.max_workers))
        
        # Don't scale below workers with active jobs
        target = max(target, workers_with_jobs)
        
        # Consider worker health
        if healthy_workers < current_workers * 0.8:  # Less than 80% healthy
            target = max(target, current_workers + 1)  # Add at least one more worker
        
        logger.debug(f"Target calculation: queue={queue_depth}, processing={processing_jobs}, "
                    f"workers_with_jobs={workers_with_jobs}, target={target}")
        
        return target
    
    def get_worker_health(self) -> List[Dict[str, Any]]:
        """Get health status of all workers"""
        try:
            if not self.redis_client:
                return []
            
            workers_data = self.redis_client.hgetall('scaling_workers')
            workers = []
            
            for worker_id, worker_data_str in workers_data.items():
                try:
                    worker_data = json.loads(worker_data_str)
                    workers.append({
                        'worker_id': worker_id,
                        'status': worker_data.get('status', 'unknown'),
                        'health_status': worker_data.get('health_status', 'unknown'),
                        'last_seen': worker_data.get('last_seen', ''),
                        'current_job': worker_data.get('current_job'),
                        'jobs_processed': worker_data.get('jobs_processed', 0),
                        'jobs_failed': worker_data.get('jobs_failed', 0)
                    })
                except (json.JSONDecodeError, KeyError):
                    continue
            
            return workers
        except Exception as e:
            logger.error(f"Failed to get worker health: {e}")
            return []
    
    def _mark_worker_for_shutdown(self, worker_id: str):
        """Mark a worker for shutdown (stop accepting new jobs)"""
        try:
            if not self.redis_client:
                return
            
            # Update worker status in Redis
            worker_data_str = self.redis_client.hget('scaling_workers', worker_id)
            if worker_data_str:
                worker_data = json.loads(worker_data_str)
                worker_data['is_shutting_down'] = True
                worker_data['shutdown_requested_at'] = datetime.now().isoformat()
                self.redis_client.hset('scaling_workers', worker_id, json.dumps(worker_data))
                logger.info(f"Marked worker {worker_id} for shutdown")
        except Exception as e:
            logger.error(f"Failed to mark worker {worker_id} for shutdown: {e}")
    
    def _wait_for_job_completion(self, containers, timeout: int) -> bool:
        """Wait for workers to complete their current jobs"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_jobs_complete = True
            
            for container in containers:
                worker_id = container.name
                try:
                    worker_data_str = self.redis_client.hget('scaling_workers', worker_id)
                    if worker_data_str:
                        worker_data = json.loads(worker_data_str)
                        current_job = worker_data.get('current_job')
                        if current_job and current_job != 'None':
                            all_jobs_complete = False
                            logger.info(f"Worker {worker_id} still processing job: {current_job}")
                            break
                except Exception as e:
                    logger.error(f"Error checking job status for {worker_id}: {e}")
            
            if all_jobs_complete:
                return True
            
            time.sleep(10)  # Check every 10 seconds
        
        return False
    
    def remove_unhealthy_workers(self):
        """Remove workers that are unhealthy for too long"""
        try:
            workers = self.get_worker_health()
            now = datetime.now()
            unhealthy_timeout = int(os.getenv("UNHEALTHY_WORKER_TIMEOUT", "300"))  # 5 minutes
            
            for worker in workers:
                try:
                    last_seen = datetime.fromisoformat(worker['last_seen'])
                    if now - last_seen > timedelta(seconds=unhealthy_timeout):
                        # Check if worker has a current job
                        current_job = worker.get('current_job')
                        if current_job and current_job != 'None':
                            logger.warning(f"Worker {worker['worker_id']} unhealthy but has job {current_job}, waiting...")
                            continue
                        
                        logger.info(f"Removing unhealthy worker: {worker['worker_id']}")
                        # Remove from Redis
                        self.redis_client.hdel('scaling_workers', worker['worker_id'])
                        
                        # In Docker Compose mode, try to remove the container
                        if self.deployment_mode == "compose":
                            try:
                                container = self.docker_client.containers.get(worker['worker_id'])
                                container.remove(force=True)
                                logger.info(f"Removed container: {worker['worker_id']}")
                            except docker.errors.NotFound:
                                pass  # Container already removed
                            except Exception as e:
                                logger.error(f"Failed to remove container {worker['worker_id']}: {e}")
                
                except (ValueError, KeyError):
                    continue
                    
        except Exception as e:
            logger.error(f"Error removing unhealthy workers: {e}")
    
    def _check_job_completion_events(self):
        """Check for recent job completions and adjust scaling logic"""
        try:
            now = datetime.now()
            if now - self.last_job_completion_check < timedelta(seconds=30):
                return  # Check every 30 seconds
            
            self.last_job_completion_check = now
            
            # Get job statistics
            job_stats = self.get_job_statistics()
            
            # Check if jobs have completed recently
            # This would ideally subscribe to job completion events
            # For now, we track changes in processing job counts
            current_processing = job_stats.get('processing_jobs', 0)
            
            # Store for trend analysis
            self.scaling_reasons['last_processing_jobs'] = current_processing
            self.scaling_reasons['job_check_time'] = now
            
        except Exception as e:
            logger.error(f"Error checking job completion events: {e}")
    
    def _recent_job_completions(self) -> int:
        """Get count of recent job completions"""
        try:
            # This is a simplified implementation
            # In production, you'd track actual completion events
            job_stats = self.get_job_statistics()
            current_processing = job_stats.get('processing_jobs', 0)
            
            last_processing = self.scaling_reasons.get('last_processing_jobs', current_processing)
            
            # If processing jobs decreased, jobs completed
            completions = max(0, last_processing - current_processing)
            
            return completions
            
        except Exception:
            return 0
    
    def _get_capacity_utilization(self) -> float:
        """Get current capacity utilization"""
        try:
            import sys
            sys.path.append('/app/scaling-controller')
            from capacity_tracker import CapacityTracker
            
            capacity_tracker = CapacityTracker(self.redis_url)
            if capacity_tracker.connect_redis():
                cluster_capacity = capacity_tracker.calculate_cluster_capacity()
                return cluster_capacity.get('capacity_utilization', 0.0)
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _cleanup_capacity_data(self):
        """Cleanup stale capacity data"""
        try:
            import sys
            sys.path.append('/app/scaling-controller')
            from capacity_tracker import CapacityTracker
            
            capacity_tracker = CapacityTracker(self.redis_url)
            if capacity_tracker.connect_redis():
                removed = capacity_tracker.cleanup_stale_capacity_data()
                if removed > 0:
                    logger.info(f"Cleaned up {removed} stale capacity entries")
            
        except Exception as e:
            logger.debug(f"Failed to cleanup capacity data: {e}")
    
    def run_scaling_loop(self):
        """Main scaling loop with job completion awareness"""
        logger.info("Starting scaling loop...")
        
        while self.running and not self.stop_event.is_set():
            try:
                # Check for completed jobs and adjust cooldown
                self._check_job_completion_events()
                
                # Check and scale
                self.check_and_scale()
                
                # Remove unhealthy workers
                self.remove_unhealthy_workers()
                
                # Cleanup capacity tracker if available
                self._cleanup_capacity_data()
                
                # Wait for next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in scaling loop: {e}")
                time.sleep(10)  # Wait before retrying
    
    def start(self):
        """Start the scaling controller"""
        logger.info("Starting Scaling Controller...")
        
        # Connect to Redis
        if not self.connect_redis():
            logger.error("Failed to connect to Redis, exiting...")
            return False
        
        # Connect to Docker
        if not self.connect_docker():
            logger.error("Failed to connect to Docker, exiting...")
            return False
        
        self.running = True
        
        # Start scaling loop
        self.run_scaling_loop()
        
        logger.info("Scaling Controller stopped")
        return True
    
    def stop(self):
        """Stop the scaling controller"""
        logger.info("Stopping Scaling Controller...")
        self.running = False
        self.stop_event.set()

def main():
    """Main entry point"""
    # Get configuration from environment
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    docker_host = os.getenv("DOCKER_HOST")
    
    if not redis_url:
        logger.error("REDIS_URL environment variable is required")
        sys.exit(1)
    
    # Create and start controller
    controller = ScalingController(redis_url, docker_host)
    
    try:
        controller.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        controller.stop()

if __name__ == "__main__":
    main() 