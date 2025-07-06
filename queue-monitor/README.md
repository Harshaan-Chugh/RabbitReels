# Queue Monitor Service

## Overview

The Queue Monitor service is a critical component of the RabbitReels auto-scaling system. It continuously monitors RabbitMQ queue depth and worker capacity to provide real-time metrics for scaling decisions.

## Features

- **Real-time Queue Monitoring**: Tracks RabbitMQ queue depth and message counts
- **Worker Health Tracking**: Monitors active and healthy worker instances
- **Performance Metrics**: Calculates average processing times and throughput
- **Scaling Recommendations**: Provides intelligent scaling suggestions based on current load
- **Historical Data**: Stores metrics history for trend analysis
- **Redis Integration**: Publishes metrics to Redis for other services to consume

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RABBIT_URL` | `amqp://guest:guest@rabbitmq:5672/` | RabbitMQ connection URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `VIDEO_QUEUE` | `video-queue` | Name of the video processing queue |
| `MIN_WORKERS` | `1` | Minimum number of workers to maintain |
| `MAX_WORKERS` | `10` | Maximum number of workers allowed |
| `SCALE_UP_THRESHOLD` | `2` | Scale up when queue depth > workers * threshold |
| `SCALE_DOWN_THRESHOLD` | `0.5` | Scale down when queue depth < workers * threshold |
| `COOLDOWN_PERIOD` | `60` | Seconds to wait between scaling actions |
| `METRICS_COLLECTION_INTERVAL` | `15` | Seconds between metric collection cycles |

### Scaling Algorithm

The queue monitor uses the following logic for scaling recommendations:

1. **Scale Up**: When queue depth > active workers * scale_up_threshold
2. **Scale Down**: When queue depth < active workers * scale_down_threshold
3. **Maintain**: When the system is in a stable state
4. **Cooldown**: Wait for cooldown period between scaling actions

## Metrics Published

The service publishes the following metrics to Redis:

```json
{
  "queue_depth": 5,
  "active_workers": 3,
  "healthy_workers": 3,
  "avg_processing_time": 120.5,
  "queue_throughput": 0.5,
  "timestamp": "2024-01-15T10:30:00",
  "scaling_recommendation": "scale_up",
  "target_workers": 5
}
```

## Redis Keys

- `current_metrics`: Latest metrics snapshot
- `metrics_history`: Historical metrics (last 100 entries)
- `video_workers`: Hash of active worker information
- `scaling_events`: Pub/Sub channel for scaling events

## Health Checks

The service provides health checks through:

- **Container Health**: Built-in Docker health check
- **Redis Connectivity**: Validates Redis connection
- **RabbitMQ Connectivity**: Validates RabbitMQ connection

## Usage

### Docker Deployment

```bash
# Build the image
docker build -t rabbitreels/queue-monitor:latest .

# Run the service
docker run -d \
  --name queue-monitor \
  --env-file .env \
  --network rabbitreels-network \
  rabbitreels/queue-monitor:latest
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export RABBIT_URL="amqp://guest:guest@localhost:5672/"
export REDIS_URL="redis://localhost:6379/0"

# Run the monitor
python monitor.py
```

## Monitoring

The service logs important events and metrics:

- Queue depth changes
- Worker health status
- Scaling recommendations
- Connection issues
- Performance metrics

## Integration

The Queue Monitor integrates with:

- **RabbitMQ**: Monitors queue depth and message counts
- **Redis**: Stores metrics and publishes scaling events
- **Scaling Controller**: Provides scaling recommendations
- **Video Creator Workers**: Tracks worker health and capacity

## Troubleshooting

### Common Issues

1. **Connection Errors**: Check RabbitMQ and Redis connectivity
2. **Missing Workers**: Ensure workers are registering with Redis
3. **Scaling Not Triggered**: Check cooldown period and thresholds
4. **High Memory Usage**: Adjust metrics retention settings

### Debug Mode

Enable debug logging by setting:

```bash
export LOG_LEVEL=DEBUG
```

## Architecture

```
Queue Monitor
├── Metrics Collection
│   ├── Queue Depth (RabbitMQ)
│   ├── Worker Count (Redis)
│   └── Processing Times (Redis)
├── Scaling Logic
│   ├── Calculate Target Workers
│   ├── Apply Cooldown Logic
│   └── Generate Recommendations
└── Publishing
    ├── Current Metrics (Redis)
    ├── Historical Data (Redis)
    └── Scaling Events (Pub/Sub)
```

## Contributing

When modifying the queue monitor:

1. Update configuration documentation
2. Add appropriate logging
3. Test with different queue depths
4. Validate scaling recommendations
5. Update health checks if needed 