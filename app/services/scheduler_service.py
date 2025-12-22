"""
Scheduler service for managing cron jobs using APScheduler.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from threading import Lock

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Service for managing background scheduled jobs using APScheduler.
    Implements singleton pattern to ensure only one scheduler instance.
    """
    
    _instance: Optional['SchedulerService'] = None
    _lock = Lock()
    
    def __new__(cls) -> 'SchedulerService':
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the scheduler service."""
        if self._initialized:
            return
        
        # Configure job stores and executors
        jobstores = {
            'default': MemoryJobStore()
        }
        
        executors = {
            'default': ThreadPoolExecutor(max_workers=5),
        }
        
        job_defaults = {
            'coalesce': True,  # Combine multiple missed executions into one
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 3600  # 1 hour grace time for misfired jobs
        }
        
        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        self._is_running = False
        self._job_callbacks: Dict[int, Callable] = {}
        self._initialized = True
        
        logger.info("SchedulerService initialized")
    
    def start(self) -> bool:
        """
        Start the scheduler.
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            if not self._is_running:
                self._scheduler.start()
                self._is_running = True
                logger.info("Scheduler started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False
    
    def stop(self, wait: bool = True) -> bool:
        """
        Stop the scheduler.
        
        Args:
            wait: Whether to wait for running jobs to complete
            
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            if self._is_running:
                self._scheduler.shutdown(wait=wait)
                self._is_running = False
                logger.info("Scheduler stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            return False
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._is_running
    
    def add_job(
        self,
        job_id: int,
        func: Callable,
        hour: int,
        minute: int,
        args: tuple = None,
        kwargs: dict = None
    ) -> bool:
        """
        Add a cron job to the scheduler.
        
        Args:
            job_id: Unique job identifier (from database)
            func: Function to execute
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            
        Returns:
            True if job added successfully, False otherwise
        """
        try:
            job_name = f"cron_job_{job_id}"
            
            # Remove existing job if any
            self.remove_job(job_id)
            
            # Create cron trigger for daily execution
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                timezone='UTC'
            )
            
            # Add the job
            self._scheduler.add_job(
                func,
                trigger=trigger,
                id=job_name,
                name=job_name,
                args=args or (),
                kwargs=kwargs or {},
                replace_existing=True
            )
            
            self._job_callbacks[job_id] = func
            logger.info(f"Added cron job {job_id} scheduled at {hour:02d}:{minute:02d}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add job {job_id}: {e}")
            return False
    
    def remove_job(self, job_id: int) -> bool:
        """
        Remove a job from the scheduler.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if removed successfully, False otherwise
        """
        try:
            job_name = f"cron_job_{job_id}"
            
            if self._scheduler.get_job(job_name):
                self._scheduler.remove_job(job_name)
                logger.info(f"Removed cron job {job_id}")
            
            if job_id in self._job_callbacks:
                del self._job_callbacks[job_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
            return False
    
    def update_job(
        self,
        job_id: int,
        hour: int,
        minute: int
    ) -> bool:
        """
        Update job schedule.
        
        Args:
            job_id: Job identifier
            hour: New hour (0-23)
            minute: New minute (0-59)
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            job_name = f"cron_job_{job_id}"
            job = self._scheduler.get_job(job_name)
            
            if job:
                trigger = CronTrigger(
                    hour=hour,
                    minute=minute,
                    timezone='UTC'
                )
                job.reschedule(trigger)
                logger.info(f"Updated cron job {job_id} to {hour:02d}:{minute:02d}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {e}")
            return False
    
    def pause_job(self, job_id: int) -> bool:
        """Pause a job."""
        try:
            job_name = f"cron_job_{job_id}"
            self._scheduler.pause_job(job_name)
            logger.info(f"Paused cron job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")
            return False
    
    def resume_job(self, job_id: int) -> bool:
        """Resume a paused job."""
        try:
            job_name = f"cron_job_{job_id}"
            self._scheduler.resume_job(job_name)
            logger.info(f"Resumed cron job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")
            return False
    
    def run_job_now(self, job_id: int) -> bool:
        """
        Immediately run a job (bypass schedule).
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if triggered successfully, False otherwise
        """
        try:
            job_name = f"cron_job_{job_id}"
            job = self._scheduler.get_job(job_name)
            
            if job:
                # Modify job to run immediately
                self._scheduler.modify_job(
                    job_name,
                    next_run_time=datetime.utcnow()
                )
                logger.info(f"Triggered immediate run for job {job_id}")
                return True
            
            # If job not in scheduler, try to run callback directly
            if job_id in self._job_callbacks:
                self._job_callbacks[job_id](job_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to run job {job_id} immediately: {e}")
            return False
    
    def get_job_info(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a scheduled job."""
        try:
            job_name = f"cron_job_{job_id}"
            job = self._scheduler.get_job(job_name)
            
            if job:
                return {
                    'id': job_id,
                    'name': job.name,
                    'next_run_time': job.next_run_time,
                    'pending': job.pending
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get job info {job_id}: {e}")
            return None
    
    def get_all_jobs(self) -> list:
        """Get all scheduled jobs."""
        try:
            jobs = self._scheduler.get_jobs()
            return [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time,
                    'pending': job.pending
                }
                for job in jobs
            ]
        except Exception as e:
            logger.error(f"Failed to get all jobs: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get scheduler status.
        
        Returns:
            Dict with scheduler status information
        """
        jobs = self.get_all_jobs()
        
        # Find next job to run
        next_job = None
        next_run_at = None
        
        for job in jobs:
            if job['next_run_time']:
                if next_run_at is None or job['next_run_time'] < next_run_at:
                    next_run_at = job['next_run_time']
                    next_job = job['name']
        
        return {
            'is_running': self._is_running,
            'job_count': len(jobs),
            'active_jobs': len([j for j in jobs if j['next_run_time']]),
            'running_jobs': 0,  # Would need to track this separately
            'next_job': next_job,
            'next_run_at': next_run_at
        }
    
    def calculate_next_run(self, hour: int, minute: int) -> datetime:
        """
        Calculate the next run time for a given schedule.
        
        Args:
            hour: Hour (0-23)
            minute: Minute (0-59)
            
        Returns:
            Next scheduled datetime
        """
        now = datetime.utcnow()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If time has passed today, schedule for tomorrow
        if next_run <= now:
            next_run += timedelta(days=1)
        
        return next_run


# Global scheduler instance
scheduler_service = SchedulerService()







