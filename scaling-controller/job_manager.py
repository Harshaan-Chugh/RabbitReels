#!/usr/bin/env python3
"""
Job Manager for RabbitReels Auto-Scaling

This module provides job tracking, state persistence, and recovery mechanisms
to ensure jobs are not lost during scaling operations.
"""

import os
import json
import time
import redis
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    ABANDONED = "abandoned"

@dataclass
class JobState:
    """Job state tracking"""
    job_id: str
    status: JobStatus
    worker_id: Optional[str]
    assigned_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    retry_count: int
    max_retries: int
    error_message: Optional[str]
    job_data: Dict[str, Any]
    heartbeat_at: Optional[datetime]
    estimated_duration: Optional[int]  # seconds

class JobManager:
    """
    Manages job state, tracking, and recovery for the auto-scaling system
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client = None
        
        # Configuration
        self.job_timeout = int(os.getenv("JOB_TIMEOUT", "3600"))  # 1 hour
        self.heartbeat_timeout = int(os.getenv("JOB_HEARTBEAT_TIMEOUT", "300"))  # 5 minutes
        self.max_retries = int(os.getenv("JOB_MAX_RETRIES", "3"))
        
        # Redis keys
        self.jobs_key = "scaling_jobs"
        self.job_assignments_key = "job_assignments"
        self.job_history_key = "job_history"
        
    def connect_redis(self) -> bool:
        """Connect to Redis"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Job Manager connected to Redis")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    def create_job(self, job_id: str, job_data: Dict[str, Any], estimated_duration: Optional[int] = None) -> bool:
        """Create a new job in the tracking system"""
        try:
            if not self.redis_client:
                return False
            
            job_state = JobState(
                job_id=job_id,
                status=JobStatus.PENDING,
                worker_id=None,
                assigned_at=None,
                started_at=None,
                completed_at=None,
                retry_count=0,
                max_retries=self.max_retries,
                error_message=None,
                job_data=job_data,
                heartbeat_at=None,
                estimated_duration=estimated_duration
            )
            
            # Store job state
            job_state_dict = self._job_state_to_dict(job_state)
            self.redis_client.hset(self.jobs_key, job_id, json.dumps(job_state_dict))
            
            logger.info(f"Created job tracking for: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create job {job_id}: {e}")
            return False
    
    def assign_job(self, job_id: str, worker_id: str) -> bool:
        """Assign a job to a worker"""
        try:
            if not self.redis_client:
                return False
            
            job_state = self.get_job_state(job_id)
            if not job_state:
                logger.error(f"Job {job_id} not found")
                return False
            
            if job_state.status != JobStatus.PENDING:
                logger.warning(f"Job {job_id} is not in PENDING status: {job_state.status}")
                return False
            
            # Update job state
            job_state.status = JobStatus.ASSIGNED
            job_state.worker_id = worker_id
            job_state.assigned_at = datetime.now()
            
            # Store updated state
            job_state_dict = self._job_state_to_dict(job_state)
            self.redis_client.hset(self.jobs_key, job_id, json.dumps(job_state_dict))
            
            # Track assignment
            self.redis_client.hset(self.job_assignments_key, worker_id, job_id)
            
            logger.info(f"Assigned job {job_id} to worker {worker_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign job {job_id} to worker {worker_id}: {e}")
            return False
    
    def start_job(self, job_id: str, worker_id: str) -> bool:
        """Mark a job as started"""
        try:
            if not self.redis_client:
                return False
            
            job_state = self.get_job_state(job_id)
            if not job_state:
                logger.error(f"Job {job_id} not found")
                return False
            
            if job_state.worker_id != worker_id:
                logger.error(f"Job {job_id} is not assigned to worker {worker_id}")
                return False
            
            # Update job state
            job_state.status = JobStatus.PROCESSING
            job_state.started_at = datetime.now()
            job_state.heartbeat_at = datetime.now()
            
            # Store updated state
            job_state_dict = self._job_state_to_dict(job_state)
            self.redis_client.hset(self.jobs_key, job_id, json.dumps(job_state_dict))
            
            logger.info(f"Started job {job_id} on worker {worker_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start job {job_id}: {e}")
            return False
    
    def update_job_heartbeat(self, job_id: str, worker_id: str) -> bool:
        """Update job heartbeat"""
        try:
            if not self.redis_client:
                return False
            
            job_state = self.get_job_state(job_id)
            if not job_state:
                return False
            
            if job_state.worker_id != worker_id:
                return False
            
            job_state.heartbeat_at = datetime.now()
            
            # Store updated state
            job_state_dict = self._job_state_to_dict(job_state)
            self.redis_client.hset(self.jobs_key, job_id, json.dumps(job_state_dict))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update heartbeat for job {job_id}: {e}")
            return False
    
    def complete_job(self, job_id: str, worker_id: str, success: bool = True, error_message: Optional[str] = None) -> bool:
        """Mark a job as completed"""
        try:
            if not self.redis_client:
                return False
            
            job_state = self.get_job_state(job_id)
            if not job_state:
                logger.error(f"Job {job_id} not found")
                return False
            
            if job_state.worker_id != worker_id:
                logger.error(f"Job {job_id} is not assigned to worker {worker_id}")
                return False
            
            # Update job state
            job_state.status = JobStatus.COMPLETED if success else JobStatus.FAILED
            job_state.completed_at = datetime.now()
            job_state.error_message = error_message
            
            # Store updated state
            job_state_dict = self._job_state_to_dict(job_state)
            self.redis_client.hset(self.jobs_key, job_id, json.dumps(job_state_dict))
            
            # Remove from active assignments
            self.redis_client.hdel(self.job_assignments_key, worker_id)
            
            # Move to history
            self._archive_job(job_state)\n            
            # Remove from active jobs
            self.redis_client.hdel(self.jobs_key, job_id)
            
            logger.info(f"Completed job {job_id} on worker {worker_id}: {'success' if success else 'failed'}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete job {job_id}: {e}")
            return False
    
    def get_job_state(self, job_id: str) -> Optional[JobState]:
        """Get job state"""
        try:
            if not self.redis_client:
                return None
            
            job_state_str = self.redis_client.hget(self.jobs_key, job_id)
            if not job_state_str:
                return None
            
            job_state_dict = json.loads(job_state_str)
            return self._dict_to_job_state(job_state_dict)
            
        except Exception as e:
            logger.error(f"Failed to get job state for {job_id}: {e}")
            return None
    
    def get_worker_jobs(self, worker_id: str) -> List[JobState]:
        """Get all jobs assigned to a worker"""
        try:
            if not self.redis_client:
                return []
            
            all_jobs = self.redis_client.hgetall(self.jobs_key)
            worker_jobs = []
            
            for job_id, job_state_str in all_jobs.items():
                try:
                    job_state_dict = json.loads(job_state_str)
                    job_state = self._dict_to_job_state(job_state_dict)
                    if job_state.worker_id == worker_id:
                        worker_jobs.append(job_state)
                except Exception:
                    continue
            
            return worker_jobs
            
        except Exception as e:
            logger.error(f"Failed to get jobs for worker {worker_id}: {e}")
            return []
    
    def get_active_jobs(self) -> List[JobState]:
        """Get all active jobs"""
        try:
            if not self.redis_client:
                return []
            
            all_jobs = self.redis_client.hgetall(self.jobs_key)
            active_jobs = []
            
            for job_id, job_state_str in all_jobs.items():
                try:
                    job_state_dict = json.loads(job_state_str)
                    job_state = self._dict_to_job_state(job_state_dict)
                    active_jobs.append(job_state)
                except Exception:
                    continue
            
            return active_jobs
            
        except Exception as e:
            logger.error(f"Failed to get active jobs: {e}")
            return []
    
    def recover_abandoned_jobs(self) -> int:
        """Recover jobs that were abandoned due to worker failures"""
        try:
            if not self.redis_client:
                return 0
            
            recovered_count = 0
            now = datetime.now()
            
            active_jobs = self.get_active_jobs()
            
            for job_state in active_jobs:
                should_recover = False
                
                # Check for timeout
                if job_state.started_at:
                    job_duration = (now - job_state.started_at).total_seconds()
                    if job_duration > self.job_timeout:
                        should_recover = True
                        logger.warning(f"Job {job_state.job_id} timed out after {job_duration} seconds")
                
                # Check for heartbeat timeout
                if job_state.heartbeat_at:
                    heartbeat_age = (now - job_state.heartbeat_at).total_seconds()
                    if heartbeat_age > self.heartbeat_timeout:
                        should_recover = True
                        logger.warning(f"Job {job_state.job_id} heartbeat timeout: {heartbeat_age} seconds")
                
                if should_recover:
                    if job_state.retry_count < job_state.max_retries:
                        # Retry the job
                        self._retry_job(job_state)
                        recovered_count += 1
                    else:
                        # Mark as abandoned
                        self._abandon_job(job_state)
            
            if recovered_count > 0:
                logger.info(f"Recovered {recovered_count} abandoned jobs")
            
            return recovered_count
            
        except Exception as e:
            logger.error(f"Failed to recover abandoned jobs: {e}")
            return 0
    
    def _retry_job(self, job_state: JobState):
        """Retry a failed job"""
        try:
            job_state.status = JobStatus.RETRYING
            job_state.worker_id = None
            job_state.assigned_at = None
            job_state.started_at = None
            job_state.heartbeat_at = None
            job_state.retry_count += 1
            
            # Store updated state
            job_state_dict = self._job_state_to_dict(job_state)
            self.redis_client.hset(self.jobs_key, job_state.job_id, json.dumps(job_state_dict))
            
            # Remove from assignments
            if job_state.worker_id:
                self.redis_client.hdel(self.job_assignments_key, job_state.worker_id)
            
            # Re-queue the job (this would need integration with RabbitMQ)
            logger.info(f"Retrying job {job_state.job_id} (attempt {job_state.retry_count})")
            
        except Exception as e:
            logger.error(f"Failed to retry job {job_state.job_id}: {e}")
    
    def _abandon_job(self, job_state: JobState):
        """Mark a job as abandoned"""
        try:
            job_state.status = JobStatus.ABANDONED
            job_state.completed_at = datetime.now()
            job_state.error_message = "Job abandoned due to repeated failures"
            
            # Store updated state
            job_state_dict = self._job_state_to_dict(job_state)
            self.redis_client.hset(self.jobs_key, job_state.job_id, json.dumps(job_state_dict))
            
            # Archive and remove
            self._archive_job(job_state)
            self.redis_client.hdel(self.jobs_key, job_state.job_id)
            
            if job_state.worker_id:
                self.redis_client.hdel(self.job_assignments_key, job_state.worker_id)
            
            logger.warning(f"Abandoned job {job_state.job_id} after {job_state.retry_count} retries")
            
        except Exception as e:
            logger.error(f"Failed to abandon job {job_state.job_id}: {e}")
    
    def _archive_job(self, job_state: JobState):
        """Archive completed job to history"""
        try:
            job_state_dict = self._job_state_to_dict(job_state)
            self.redis_client.lpush(self.job_history_key, json.dumps(job_state_dict))
            self.redis_client.ltrim(self.job_history_key, 0, 999)  # Keep last 1000 jobs
            
        except Exception as e:
            logger.error(f"Failed to archive job {job_state.job_id}: {e}")
    
    def _job_state_to_dict(self, job_state: JobState) -> Dict[str, Any]:
        """Convert JobState to dictionary for storage"""
        result = asdict(job_state)
        
        # Convert datetime objects to ISO strings
        for field in ['assigned_at', 'started_at', 'completed_at', 'heartbeat_at']:
            if result[field]:
                result[field] = result[field].isoformat()
        
        # Convert enum to string
        result['status'] = job_state.status.value
        
        return result
    
    def _dict_to_job_state(self, job_dict: Dict[str, Any]) -> JobState:
        """Convert dictionary to JobState"""
        # Convert ISO strings to datetime objects
        for field in ['assigned_at', 'started_at', 'completed_at', 'heartbeat_at']:
            if job_dict[field]:
                job_dict[field] = datetime.fromisoformat(job_dict[field])
        
        # Convert string to enum
        job_dict['status'] = JobStatus(job_dict['status'])
        
        return JobState(**job_dict)
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """Get job processing statistics"""
        try:
            if not self.redis_client:
                return {}
            
            active_jobs = self.get_active_jobs()
            
            stats = {
                'total_active_jobs': len(active_jobs),
                'pending_jobs': len([j for j in active_jobs if j.status == JobStatus.PENDING]),
                'assigned_jobs': len([j for j in active_jobs if j.status == JobStatus.ASSIGNED]),
                'processing_jobs': len([j for j in active_jobs if j.status == JobStatus.PROCESSING]),
                'retrying_jobs': len([j for j in active_jobs if j.status == JobStatus.RETRYING]),
                'workers_with_jobs': len(set(j.worker_id for j in active_jobs if j.worker_id)),
                'average_processing_time': 0.0
            }
            
            # Calculate average processing time for active jobs
            processing_times = []
            now = datetime.now()
            for job in active_jobs:
                if job.started_at and job.status == JobStatus.PROCESSING:
                    processing_time = (now - job.started_at).total_seconds()
                    processing_times.append(processing_time)
            
            if processing_times:
                stats['average_processing_time'] = sum(processing_times) / len(processing_times)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get job statistics: {e}")
            return {}