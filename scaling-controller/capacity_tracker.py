#!/usr/bin/env python3
"""
Worker Capacity Tracker for RabbitReels Auto-Scaling

This module tracks worker capacity beyond just count, including:
- Worker performance metrics
- Resource utilization
- Job throughput rates
- Worker efficiency scoring
"""

import os
import json
import time
import redis
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class WorkerPerformanceTier(Enum):
    """Worker performance tier classification"""
    EXCELLENT = "excellent"  # Top 25%
    GOOD = "good"           # 25-75%
    AVERAGE = "average"     # 75-90%
    POOR = "poor"          # Bottom 10%

@dataclass
class WorkerCapacity:
    """Worker capacity metrics"""
    worker_id: str
    concurrent_job_limit: int
    current_jobs: int
    jobs_per_hour: float
    average_job_duration: float
    success_rate: float
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    performance_tier: WorkerPerformanceTier
    efficiency_score: float  # 0-100
    last_updated: datetime

@dataclass
class WorkerResourceLimits:
    """Resource limits for workers"""
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 85.0
    max_disk_percent: float = 90.0
    max_concurrent_jobs: int = 2  # Most video workers should handle 1-2 jobs max

class CapacityTracker:
    """
    Tracks and manages worker capacity beyond simple counting
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client = None
        
        # Configuration
        self.capacity_window = int(os.getenv("CAPACITY_TRACKING_WINDOW", "3600"))  # 1 hour
        self.performance_samples = int(os.getenv("PERFORMANCE_SAMPLES", "10"))
        self.efficiency_threshold = float(os.getenv("EFFICIENCY_THRESHOLD", "70.0"))
        
        # Redis keys
        self.capacity_key = "worker_capacity"
        self.performance_history_key = "worker_performance_history"
        self.resource_limits = WorkerResourceLimits()
        
    def connect_redis(self) -> bool:
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Capacity Tracker connected to Redis")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    def update_worker_capacity(self, worker_id: str, 
                              jobs_completed: int = 0,
                              job_duration: float = 0,
                              job_success: bool = True,
                              cpu_usage: float = 0,
                              memory_usage: float = 0,
                              disk_usage: float = 0,
                              current_jobs: int = 0) -> bool:
        """Update worker capacity metrics"""
        try:
            if not self.redis_client:
                return False
            
            # Get existing capacity data
            capacity_data = self.get_worker_capacity(worker_id)
            if not capacity_data:
                capacity_data = WorkerCapacity(
                    worker_id=worker_id,
                    concurrent_job_limit=self.resource_limits.max_concurrent_jobs,
                    current_jobs=current_jobs,
                    jobs_per_hour=0.0,
                    average_job_duration=0.0,
                    success_rate=100.0,
                    cpu_usage_percent=cpu_usage,
                    memory_usage_percent=memory_usage,
                    disk_usage_percent=disk_usage,
                    performance_tier=WorkerPerformanceTier.AVERAGE,
                    efficiency_score=50.0,
                    last_updated=datetime.now()
                )
            
            # Update current status
            capacity_data.current_jobs = current_jobs
            capacity_data.cpu_usage_percent = cpu_usage
            capacity_data.memory_usage_percent = memory_usage
            capacity_data.disk_usage_percent = disk_usage
            capacity_data.last_updated = datetime.now()
            
            # Update performance metrics if job completed
            if jobs_completed > 0:
                self._update_performance_metrics(capacity_data, job_duration, job_success)\n            
            # Calculate efficiency score\n            capacity_data.efficiency_score = self._calculate_efficiency_score(capacity_data)\n            \n            # Determine performance tier\n            capacity_data.performance_tier = self._determine_performance_tier(capacity_data)\n            \n            # Adjust concurrent job limit based on performance and resources\n            capacity_data.concurrent_job_limit = self._calculate_concurrent_limit(capacity_data)\n            \n            # Store updated capacity\n            capacity_dict = self._capacity_to_dict(capacity_data)\n            self.redis_client.hset(self.capacity_key, worker_id, json.dumps(capacity_dict))\n            \n            # Store performance history sample\n            self._store_performance_sample(capacity_data)\n            \n            logger.debug(f\"Updated capacity for worker {worker_id}: score={capacity_data.efficiency_score:.1f}\")\n            return True\n            \n        except Exception as e:\n            logger.error(f\"Failed to update worker capacity for {worker_id}: {e}\")\n            return False\n    \n    def get_worker_capacity(self, worker_id: str) -> Optional[WorkerCapacity]:\n        \"\"\"Get worker capacity data\"\"\"\n        try:\n            if not self.redis_client:\n                return None\n            \n            capacity_str = self.redis_client.hget(self.capacity_key, worker_id)\n            if not capacity_str:\n                return None\n            \n            capacity_dict = json.loads(capacity_str)\n            return self._dict_to_capacity(capacity_dict)\n            \n        except Exception as e:\n            logger.error(f\"Failed to get worker capacity for {worker_id}: {e}\")\n            return None\n    \n    def get_all_worker_capacities(self) -> List[WorkerCapacity]:\n        \"\"\"Get all worker capacity data\"\"\"\n        try:\n            if not self.redis_client:\n                return []\n            \n            all_capacity = self.redis_client.hgetall(self.capacity_key)\n            capacities = []\n            \n            for worker_id, capacity_str in all_capacity.items():\n                try:\n                    capacity_dict = json.loads(capacity_str)\n                    capacity = self._dict_to_capacity(capacity_dict)\n                    capacities.append(capacity)\n                except Exception:\n                    continue\n            \n            return capacities\n            \n        except Exception as e:\n            logger.error(f\"Failed to get all worker capacities: {e}\")\n            return []\n    \n    def calculate_cluster_capacity(self) -> Dict[str, Any]:\n        \"\"\"Calculate overall cluster capacity metrics\"\"\"\n        try:\n            capacities = self.get_all_worker_capacities()\n            if not capacities:\n                return {\n                    'total_workers': 0,\n                    'effective_capacity': 0.0,\n                    'avg_efficiency': 0.0,\n                    'resource_constrained_workers': 0,\n                    'high_performers': 0,\n                    'total_concurrent_limit': 0\n                }\n            \n            total_workers = len(capacities)\n            total_concurrent_limit = sum(c.concurrent_job_limit for c in capacities)\n            avg_efficiency = sum(c.efficiency_score for c in capacities) / total_workers\n            \n            # Calculate effective capacity (weighted by efficiency)\n            effective_capacity = sum(\n                c.concurrent_job_limit * (c.efficiency_score / 100.0) \n                for c in capacities\n            )\n            \n            # Count resource-constrained workers\n            resource_constrained = sum(\n                1 for c in capacities \n                if (c.cpu_usage_percent > self.resource_limits.max_cpu_percent or\n                    c.memory_usage_percent > self.resource_limits.max_memory_percent or\n                    c.disk_usage_percent > self.resource_limits.max_disk_percent)\n            )\n            \n            # Count high performers\n            high_performers = sum(\n                1 for c in capacities \n                if c.performance_tier in [WorkerPerformanceTier.EXCELLENT, WorkerPerformanceTier.GOOD]\n            )\n            \n            return {\n                'total_workers': total_workers,\n                'effective_capacity': effective_capacity,\n                'avg_efficiency': avg_efficiency,\n                'resource_constrained_workers': resource_constrained,\n                'high_performers': high_performers,\n                'total_concurrent_limit': total_concurrent_limit,\n                'capacity_utilization': self._calculate_capacity_utilization(capacities)\n            }\n            \n        except Exception as e:\n            logger.error(f\"Failed to calculate cluster capacity: {e}\")\n            return {}\n    \n    def get_scaling_recommendation(self, queue_depth: int, current_workers: int) -> Dict[str, Any]:\n        \"\"\"Get capacity-aware scaling recommendation\"\"\"\n        try:\n            cluster_capacity = self.calculate_cluster_capacity()\n            \n            if not cluster_capacity:\n                return {\n                    'action': 'maintain',\n                    'reason': 'no_capacity_data',\n                    'target_workers': current_workers\n                }\n            \n            effective_capacity = cluster_capacity['effective_capacity']\n            capacity_utilization = cluster_capacity['capacity_utilization']\n            resource_constrained = cluster_capacity['resource_constrained_workers']\n            \n            # Calculate capacity-based target\n            if queue_depth == 0:\n                target_workers = max(1, current_workers // 2)\n                action = 'scale_down' if target_workers < current_workers else 'maintain'\n                reason = 'no_queue_demand'\n            elif capacity_utilization > 0.8:  # Over 80% capacity utilization\n                # Need more workers due to capacity constraints\n                target_workers = current_workers + max(1, resource_constrained)\n                action = 'scale_up'\n                reason = f'high_capacity_utilization={capacity_utilization:.2f}'\n            elif effective_capacity < queue_depth:\n                # Not enough effective capacity for queue\n                needed_capacity = queue_depth - effective_capacity\n                target_workers = current_workers + max(1, int(needed_capacity / 1.5))\n                action = 'scale_up'\n                reason = f'insufficient_effective_capacity={effective_capacity:.1f}'\n            else:\n                target_workers = current_workers\n                action = 'maintain'\n                reason = f'adequate_capacity={effective_capacity:.1f}'\n            \n            return {\n                'action': action,\n                'target_workers': target_workers,\n                'reason': reason,\n                'capacity_metrics': {\n                    'effective_capacity': effective_capacity,\n                    'capacity_utilization': capacity_utilization,\n                    'resource_constrained_workers': resource_constrained\n                }\n            }\n            \n        except Exception as e:\n            logger.error(f\"Failed to get scaling recommendation: {e}\")\n            return {\n                'action': 'maintain',\n                'reason': 'capacity_calculation_error',\n                'target_workers': current_workers\n            }\n    \n    def _update_performance_metrics(self, capacity: WorkerCapacity, job_duration: float, job_success: bool):\n        \"\"\"Update performance metrics for a worker\"\"\"\n        # Update average job duration (exponential moving average)\n        if capacity.average_job_duration == 0:\n            capacity.average_job_duration = job_duration\n        else:\n            alpha = 0.3  # Smoothing factor\n            capacity.average_job_duration = (alpha * job_duration + \n                                           (1 - alpha) * capacity.average_job_duration)\n        \n        # Calculate jobs per hour\n        if capacity.average_job_duration > 0:\n            capacity.jobs_per_hour = 3600.0 / capacity.average_job_duration\n        \n        # Update success rate (exponential moving average)\n        current_success = 100.0 if job_success else 0.0\n        if capacity.success_rate == 100.0 and not job_success:\n            capacity.success_rate = 95.0  # First failure\n        else:\n            alpha = 0.2\n            capacity.success_rate = (alpha * current_success + \n                                   (1 - alpha) * capacity.success_rate)\n    \n    def _calculate_efficiency_score(self, capacity: WorkerCapacity) -> float:\n        \"\"\"Calculate worker efficiency score (0-100)\"\"\"\n        try:\n            # Base score from success rate\n            score = capacity.success_rate * 0.4\n            \n            # Add throughput component\n            if capacity.jobs_per_hour > 0:\n                # Normalize based on expected throughput (assuming ~2 jobs/hour baseline)\n                throughput_score = min(capacity.jobs_per_hour / 2.0, 1.0) * 30\n                score += throughput_score\n            \n            # Subtract resource usage penalties\n            cpu_penalty = max(0, capacity.cpu_usage_percent - 70) * 0.3\n            memory_penalty = max(0, capacity.memory_usage_percent - 70) * 0.3\n            disk_penalty = max(0, capacity.disk_usage_percent - 80) * 0.2\n            \n            score -= (cpu_penalty + memory_penalty + disk_penalty)\n            \n            # Add stability bonus (if worker has been consistent)\n            if capacity.success_rate > 95 and capacity.jobs_per_hour > 1:\n                score += 10\n            \n            return max(0, min(100, score))\n            \n        except Exception:\n            return 50.0  # Default average score\n    \n    def _determine_performance_tier(self, capacity: WorkerCapacity) -> WorkerPerformanceTier:\n        \"\"\"Determine performance tier based on efficiency score\"\"\"\n        score = capacity.efficiency_score\n        \n        if score >= 80:\n            return WorkerPerformanceTier.EXCELLENT\n        elif score >= 60:\n            return WorkerPerformanceTier.GOOD\n        elif score >= 40:\n            return WorkerPerformanceTier.AVERAGE\n        else:\n            return WorkerPerformanceTier.POOR\n    \n    def _calculate_concurrent_limit(self, capacity: WorkerCapacity) -> int:\n        \"\"\"Calculate optimal concurrent job limit for worker\"\"\"\n        base_limit = self.resource_limits.max_concurrent_jobs\n        \n        # Reduce limit if resources are constrained\n        if (capacity.cpu_usage_percent > self.resource_limits.max_cpu_percent or\n            capacity.memory_usage_percent > self.resource_limits.max_memory_percent):\n            return 1  # Conservative limit for resource-constrained workers\n        \n        # Adjust based on performance tier\n        if capacity.performance_tier == WorkerPerformanceTier.EXCELLENT:\n            return min(base_limit + 1, 3)  # Allow up to 3 concurrent jobs\n        elif capacity.performance_tier == WorkerPerformanceTier.POOR:\n            return 1  # Limit poor performers to 1 job\n        \n        return base_limit\n    \n    def _calculate_capacity_utilization(self, capacities: List[WorkerCapacity]) -> float:\n        \"\"\"Calculate current capacity utilization\"\"\"\n        if not capacities:\n            return 0.0\n        \n        total_limit = sum(c.concurrent_job_limit for c in capacities)\n        total_current = sum(c.current_jobs for c in capacities)\n        \n        return total_current / total_limit if total_limit > 0 else 0.0\n    \n    def _store_performance_sample(self, capacity: WorkerCapacity):\n        \"\"\"Store performance sample for historical analysis\"\"\"\n        try:\n            sample = {\n                'worker_id': capacity.worker_id,\n                'timestamp': capacity.last_updated.isoformat(),\n                'efficiency_score': capacity.efficiency_score,\n                'jobs_per_hour': capacity.jobs_per_hour,\n                'success_rate': capacity.success_rate,\n                'cpu_usage': capacity.cpu_usage_percent,\n                'memory_usage': capacity.memory_usage_percent\n            }\n            \n            # Store in time-series format\n            key = f\"{self.performance_history_key}:{capacity.worker_id}\"\n            self.redis_client.lpush(key, json.dumps(sample))\n            self.redis_client.ltrim(key, 0, self.performance_samples - 1)\n            self.redis_client.expire(key, self.capacity_window)\n            \n        except Exception as e:\n            logger.error(f\"Failed to store performance sample: {e}\")\n    \n    def _capacity_to_dict(self, capacity: WorkerCapacity) -> Dict[str, Any]:\n        \"\"\"Convert WorkerCapacity to dictionary\"\"\"\n        result = {\n            'worker_id': capacity.worker_id,\n            'concurrent_job_limit': capacity.concurrent_job_limit,\n            'current_jobs': capacity.current_jobs,\n            'jobs_per_hour': capacity.jobs_per_hour,\n            'average_job_duration': capacity.average_job_duration,\n            'success_rate': capacity.success_rate,\n            'cpu_usage_percent': capacity.cpu_usage_percent,\n            'memory_usage_percent': capacity.memory_usage_percent,\n            'disk_usage_percent': capacity.disk_usage_percent,\n            'performance_tier': capacity.performance_tier.value,\n            'efficiency_score': capacity.efficiency_score,\n            'last_updated': capacity.last_updated.isoformat()\n        }\n        return result\n    \n    def _dict_to_capacity(self, capacity_dict: Dict[str, Any]) -> WorkerCapacity:\n        \"\"\"Convert dictionary to WorkerCapacity\"\"\"\n        capacity_dict['performance_tier'] = WorkerPerformanceTier(capacity_dict['performance_tier'])\n        capacity_dict['last_updated'] = datetime.fromisoformat(capacity_dict['last_updated'])\n        return WorkerCapacity(**capacity_dict)\n    \n    def cleanup_stale_capacity_data(self) -> int:\n        \"\"\"Remove capacity data for workers that haven't been seen recently\"\"\"\n        try:\n            if not self.redis_client:\n                return 0\n            \n            capacities = self.get_all_worker_capacities()\n            now = datetime.now()\n            stale_threshold = timedelta(minutes=10)\n            removed_count = 0\n            \n            for capacity in capacities:\n                if now - capacity.last_updated > stale_threshold:\n                    self.redis_client.hdel(self.capacity_key, capacity.worker_id)\n                    removed_count += 1\n                    logger.info(f\"Removed stale capacity data for worker: {capacity.worker_id}\")\n            \n            return removed_count\n            \n        except Exception as e:\n            logger.error(f\"Failed to cleanup stale capacity data: {e}\")\n            return 0