# RabbitReels Auto-Scaling Video Creator Plan

## Executive Summary

This plan outlines the implementation of an auto-scaling group for video creators that eliminates job conflicts and scales dynamically based on queue depth, achieving approximately 1:1 scaling between jobs and workers.

## Current Architecture Analysis

### Current System Flow
```
API → RabbitMQ (video-queue) → Single Video Creator → Redis/PostgreSQL
```

### Current Limitations
- Single video creator instance creates bottlenecks
- No load balancing between multiple workers
- No auto-scaling based on demand
- Jobs can stack up during peak usage
- No graceful scaling down during low usage

## Proposed Architecture

### New System Flow
```
API → RabbitMQ (video-queue) → Queue Monitor → Scaling Controller
                                     ↓
                            Multiple Video Creators (Auto-Scaled)
                                     ↓
                              Redis/PostgreSQL
```

### Key Components

#### 1. Queue Monitor Service
- **Purpose**: Monitors RabbitMQ queue depth and worker capacity
- **Metrics Collected**:
  - Queue depth (pending jobs)
  - Active workers count
  - Worker health status
  - Average job processing time
  - Queue throughput rate

#### 2. Scaling Controller
- **Purpose**: Makes scaling decisions and manages worker instances
- **Scaling Rules**:
  - Scale up: 1 worker per 1-2 jobs in queue
  - Scale down: Remove workers when queue depth < worker count
  - Minimum workers: 1 (always ready)
  - Maximum workers: Configurable (default: 10)

#### 3. Enhanced Video Creator Workers
- **Features**:
  - Graceful shutdown handling
  - Health check endpoints
  - Heartbeat system
  - Better error handling and retry logic
  - Proper resource cleanup

#### 4. Docker Swarm Orchestration
- **Benefits**:
  - Built-in load balancing
  - Service discovery
  - Rolling updates
  - Resource constraints
  - High availability

## Implementation Details

### Phase 1: Queue Monitoring System

#### 1.1 Queue Monitor Service (`queue-monitor/monitor.py`)
```python
import pika
import redis
import time
import json
from typing import Dict, Any

class QueueMonitor:
    def __init__(self, rabbit_url: str, redis_url: str):
        self.rabbit_url = rabbit_url
        self.redis_url = redis_url
        self.metrics = {}
    
    def get_queue_depth(self) -> int:
        """Get current queue depth from RabbitMQ"""
        pass
    
    def get_active_workers(self) -> int:
        """Get count of active workers from Redis"""
        pass
    
    def calculate_scaling_decision(self) -> Dict[str, Any]:
        """Calculate if scaling up/down is needed"""
        pass
    
    def publish_metrics(self):
        """Publish metrics to Redis for scaling controller"""
        pass
```

#### 1.2 Metrics Schema
```python
class QueueMetrics(BaseModel):
    queue_depth: int
    active_workers: int
    healthy_workers: int
    avg_processing_time: float
    queue_throughput: float
    timestamp: datetime
    scaling_recommendation: str  # "scale_up", "scale_down", "maintain"
    target_workers: int
```

### Phase 2: Scaling Controller

#### 2.1 Scaling Controller Service (`scaling-controller/controller.py`)
```python
import docker
import time
from typing import List

class ScalingController:
    def __init__(self, docker_client, min_workers=1, max_workers=10):
        self.docker = docker_client
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.current_workers = []
    
    def scale_up(self, target_count: int):
        """Scale up video creator workers"""
        pass
    
    def scale_down(self, target_count: int):
        """Scale down video creator workers gracefully"""
        pass
    
    def get_worker_health(self) -> List[Dict]:
        """Check health of all workers"""
        pass
    
    def remove_unhealthy_workers(self):
        """Remove workers that fail health checks"""
        pass
```

#### 2.2 Scaling Logic
```python
def calculate_target_workers(queue_depth: int, active_workers: int) -> int:
    """
    Scaling algorithm:
    - 1 worker per 1-2 jobs in queue
    - Minimum 1 worker
    - Maximum configurable
    """
    if queue_depth == 0:
        return max(1, min(active_workers, 2))  # Keep 1-2 workers for quick response
    
    # Scale up: 1 worker per job, with slight buffer
    target = min(queue_depth + 1, max_workers)
    
    # Don't scale down too aggressively
    if target < active_workers:
        return max(target, active_workers // 2)
    
    return target
```

### Phase 3: Enhanced Video Creator

#### 3.1 Health Check System
```python
# Add to video_creator.py
import signal
import threading
from flask import Flask
from datetime import datetime

class VideoCreatorWorker:
    def __init__(self):
        self.health_app = Flask(__name__)
        self.is_healthy = True
        self.last_heartbeat = datetime.now()
        self.current_job = None
        self.setup_health_endpoints()
        self.setup_signal_handlers()
    
    def setup_health_endpoints(self):
        @self.health_app.route('/health')
        def health_check():
            return {
                'status': 'healthy' if self.is_healthy else 'unhealthy',
                'last_heartbeat': self.last_heartbeat.isoformat(),
                'current_job': self.current_job,
                'worker_id': os.environ.get('WORKER_ID')
            }
    
    def setup_signal_handlers(self):
        signal.signal(signal.SIGTERM, self.graceful_shutdown)
        signal.signal(signal.SIGINT, self.graceful_shutdown)
    
    def graceful_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        print("Received shutdown signal, finishing current job...")
        self.is_healthy = False
        # Finish current job, then exit
```

#### 3.2 Worker Registration
```python
def register_worker():
    """Register worker with Redis for tracking"""
    try:
        r = redis.from_url(REDIS_URL)
        worker_id = os.environ.get('WORKER_ID', f"worker-{os.getpid()}")
        worker_data = {
            'id': worker_id,
            'status': 'active',
            'started_at': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat()
        }
        r.hset('video_workers', worker_id, json.dumps(worker_data))
        return worker_id
    except Exception as e:
        print(f"Failed to register worker: {e}")
        return None
```

### Phase 4: Docker Swarm Configuration

#### 4.1 Docker Swarm Setup
```yaml
# docker-compose.swarm.yml
version: '3.8'

services:
  queue-monitor:
    image: rabbitreels/queue-monitor:latest
    deploy:
      replicas: 1
      placement:
        constraints: [node.role == manager]
    networks:
      - rabbitreels-network
    environment:
      - RABBIT_URL=${RABBIT_URL}
      - REDIS_URL=${REDIS_URL}

  scaling-controller:
    image: rabbitreels/scaling-controller:latest
    deploy:
      replicas: 1
      placement:
        constraints: [node.role == manager]
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - rabbitreels-network
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
      - MIN_WORKERS=1
      - MAX_WORKERS=10

  video-creator:
    image: rabbitreels/video-creator:latest
    deploy:
      replicas: 1  # Starting replicas, will be scaled dynamically
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
        monitor: 60s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    networks:
      - rabbitreels-network
    volumes:
      - videos-data:/app/data/videos
    environment:
      - RABBIT_URL=${RABBIT_URL}
      - REDIS_URL=${REDIS_URL}
      - WORKER_ID={{.Task.Slot}}
```

#### 4.2 Scaling Commands
```bash
# Scale up video creators
docker service scale rabbitreels_video-creator=5

# Scale down video creators
docker service scale rabbitreels_video-creator=2

# Check service status
docker service ps rabbitreels_video-creator
```

### Phase 5: Monitoring and Metrics

#### 5.1 Metrics Collection
```python
class MetricsCollector:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    def collect_metrics(self) -> Dict:
        """Collect all scaling metrics"""
        return {
            'queue_depth': self.get_queue_depth(),
            'active_workers': self.get_active_workers(),
            'healthy_workers': self.get_healthy_workers(),
            'avg_processing_time': self.get_avg_processing_time(),
            'jobs_per_minute': self.get_jobs_per_minute(),
            'cpu_usage': self.get_system_metrics(),
            'memory_usage': self.get_memory_usage()
        }
    
    def store_metrics(self, metrics: Dict):
        """Store metrics in time series format"""
        timestamp = time.time()
        self.redis.zadd('metrics_timeline', {json.dumps(metrics): timestamp})
```

#### 5.2 Dashboard API
```python
@app.get("/metrics/dashboard")
def get_dashboard_metrics():
    """Get metrics for dashboard display"""
    return {
        'current_status': get_current_status(),
        'scaling_history': get_scaling_history(),
        'performance_metrics': get_performance_metrics(),
        'worker_health': get_worker_health_summary()
    }
```

### Phase 6: Configuration Management

#### 6.1 Scaling Configuration
```python
# scaling-config.yml
scaling:
  min_workers: 1
  max_workers: 10
  scale_up_threshold: 2  # Scale up when queue_depth > active_workers * 2
  scale_down_threshold: 0.5  # Scale down when queue_depth < active_workers * 0.5
  cooldown_period: 60  # Seconds to wait between scaling actions
  health_check_interval: 30  # Seconds between health checks
  metrics_collection_interval: 15  # Seconds between metrics collection

worker:
  graceful_shutdown_timeout: 300  # 5 minutes to finish current job
  health_check_timeout: 30  # Seconds for health check response
  heartbeat_interval: 10  # Seconds between heartbeats
```

#### 6.2 Environment Variables
```bash
# Auto-scaling configuration
MIN_WORKERS=1
MAX_WORKERS=10
SCALE_UP_THRESHOLD=2
SCALE_DOWN_THRESHOLD=0.5
COOLDOWN_PERIOD=60
HEALTH_CHECK_INTERVAL=30
GRACEFUL_SHUTDOWN_TIMEOUT=300

# Monitoring configuration
METRICS_RETENTION_DAYS=7
DASHBOARD_REFRESH_INTERVAL=5
ALERT_THRESHOLDS_CONFIG_PATH=/app/config/alerts.yml
```

## Implementation Roadmap

### Week 1: Foundation
- [ ] Create queue monitor service
- [ ] Implement basic metrics collection
- [ ] Add health check endpoints to video creator

### Week 2: Scaling Logic
- [ ] Implement scaling controller
- [ ] Add graceful shutdown handling
- [ ] Create worker registration system

### Week 3: Container Orchestration
- [ ] Set up Docker Swarm configuration
- [ ] Test scaling up/down functionality
- [ ] Implement worker health monitoring

### Week 4: Monitoring & Optimization
- [ ] Create metrics dashboard
- [ ] Add performance monitoring
- [ ] Optimize scaling algorithms
- [ ] Load testing and tuning

## Benefits of This Approach

1. **Eliminates Job Conflicts**: Each worker processes one job at a time
2. **Dynamic Scaling**: Automatically scales based on demand
3. **Resource Efficiency**: Scales down during low usage
4. **High Availability**: Unhealthy workers are automatically replaced
5. **Performance Monitoring**: Real-time metrics and dashboards
6. **Graceful Handling**: Jobs complete before workers are terminated

## Deployment Strategy

### Development Environment
1. Use Docker Compose with manual scaling
2. Test scaling logic with simulated load
3. Validate metrics collection and health checks

### Production Environment
1. Deploy with Docker Swarm for orchestration
2. Set up monitoring and alerting
3. Configure auto-scaling parameters based on usage patterns
4. Implement gradual rollout

## Monitoring and Alerts

### Key Metrics to Monitor
- Queue depth trend
- Worker scaling events
- Job processing times
- Worker health status
- System resource usage

### Alert Conditions
- Queue depth > 50 for > 5 minutes
- Worker failure rate > 10%
- Scaling controller unresponsive
- Average processing time > 10 minutes

## Security Considerations

1. **Docker Socket Access**: Limit scaling controller access
2. **Resource Limits**: Set CPU/memory limits per worker
3. **Health Check Authentication**: Secure health endpoints
4. **Metrics Access**: Restrict dashboard access

## Cost Optimization

1. **Intelligent Scaling**: Don't over-provision workers
2. **Resource Constraints**: Limit worker resource usage
3. **Scheduled Scaling**: Predictive scaling based on usage patterns
4. **Spot Instances**: Use cheaper compute when available

This plan provides a comprehensive auto-scaling solution that will eliminate job conflicts between video creators and provide efficient 1:1ish scaling based on queue depth. 