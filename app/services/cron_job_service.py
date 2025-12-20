"""
Cron Job service for managing scheduled zone import tasks.
"""
import logging
from datetime import datetime, date
from typing import Optional, List, Tuple
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.cron_job import CronJob, CronJobLog, JobType, JobStatus, LogStatus
from app.models.tld import Tld
from app.schemas.cron import CronJobCreate, CronJobUpdate
from app.services.scheduler_service import scheduler_service
from app.services.czds_client import CZDSClient
from app.services.zone_parser import extract_slds_from_zone
from app.services.drop_detector import load_sld_set_for_day, compute_dropped_slds, persist_drops
from app.core.database import SessionLocal
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CronJobService:
    """Service for managing cron jobs and their execution."""
    
    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
    
    # ============== CRUD Operations ==============
    
    def get_all(self, skip: int = 0, limit: int = 100) -> Tuple[List[CronJob], int]:
        """Get all cron jobs with pagination."""
        total = self.db.query(func.count(CronJob.id)).scalar()
        jobs = (
            self.db.query(CronJob)
            .order_by(CronJob.priority.asc(), CronJob.cron_hour.asc(), CronJob.cron_minute.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return jobs, total
    
    def get_by_id(self, job_id: int) -> Optional[CronJob]:
        """Get a cron job by ID."""
        return self.db.query(CronJob).filter(CronJob.id == job_id).first()
    
    def get_by_tld(self, tld: str) -> Optional[CronJob]:
        """Get a cron job by TLD."""
        return self.db.query(CronJob).filter(CronJob.tld == tld.lower()).first()
    
    def get_enabled_jobs(self) -> List[CronJob]:
        """Get all enabled cron jobs."""
        return (
            self.db.query(CronJob)
            .filter(CronJob.is_enabled == True)
            .order_by(CronJob.priority.asc())
            .all()
        )
    
    def get_enabled_count(self) -> int:
        """Get count of enabled jobs."""
        return self.db.query(func.count(CronJob.id)).filter(CronJob.is_enabled == True).scalar()
    
    def get_running_count(self) -> int:
        """Get count of currently running jobs."""
        return (
            self.db.query(func.count(CronJob.id))
            .filter(CronJob.last_status == JobStatus.RUNNING)
            .scalar()
        )
    
    def create(self, data: CronJobCreate) -> CronJob:
        """Create a new cron job."""
        # Check if job for this TLD already exists
        existing = self.get_by_tld(data.tld)
        if existing:
            raise ValueError(f"A cron job for TLD '{data.tld}' already exists")
        
        job = CronJob(
            name=data.name,
            tld=data.tld.lower(),
            cron_hour=data.cron_hour,
            cron_minute=data.cron_minute,
            job_type=data.job_type,
            is_enabled=data.is_enabled,
            priority=data.priority,
            timeout_minutes=data.timeout_minutes,
            retry_count=data.retry_count,
            next_run_at=scheduler_service.calculate_next_run(data.cron_hour, data.cron_minute)
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        
        # Register with scheduler if enabled
        if job.is_enabled:
            self._register_job_with_scheduler(job)
        
        logger.info(f"Created cron job {job.id} for TLD {job.tld}")
        return job
    
    def update(self, job_id: int, data: CronJobUpdate) -> Optional[CronJob]:
        """Update a cron job."""
        job = self.get_by_id(job_id)
        if not job:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(job, field, value)
        
        # Recalculate next run time if schedule changed
        if 'cron_hour' in update_data or 'cron_minute' in update_data:
            job.next_run_at = scheduler_service.calculate_next_run(job.cron_hour, job.cron_minute)
            
            # Update scheduler
            if job.is_enabled:
                scheduler_service.update_job(job.id, job.cron_hour, job.cron_minute)
        
        # Handle enabled/disabled state
        if 'is_enabled' in update_data:
            if job.is_enabled:
                self._register_job_with_scheduler(job)
            else:
                scheduler_service.remove_job(job.id)
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Updated cron job {job.id}")
        return job
    
    def delete(self, job_id: int) -> bool:
        """Delete a cron job."""
        job = self.get_by_id(job_id)
        if not job:
            return False
        
        # Remove from scheduler
        scheduler_service.remove_job(job_id)
        
        self.db.delete(job)
        self.db.commit()
        
        logger.info(f"Deleted cron job {job_id}")
        return True
    
    def toggle_enabled(self, job_id: int) -> Optional[CronJob]:
        """Toggle job enabled status."""
        job = self.get_by_id(job_id)
        if not job:
            return None
        
        job.is_enabled = not job.is_enabled
        
        if job.is_enabled:
            job.next_run_at = scheduler_service.calculate_next_run(job.cron_hour, job.cron_minute)
            self._register_job_with_scheduler(job)
        else:
            scheduler_service.remove_job(job.id)
        
        self.db.commit()
        self.db.refresh(job)
        
        logger.info(f"Toggled cron job {job_id} to {'enabled' if job.is_enabled else 'disabled'}")
        return job
    
    # ============== Bulk Operations ==============
    
    def bulk_create(
        self,
        tlds: List[str],
        start_hour: int = 0,
        interval_minutes: int = 30,
        job_type: JobType = JobType.FULL
    ) -> List[CronJob]:
        """
        Create cron jobs for multiple TLDs with staggered schedules.
        
        Args:
            tlds: List of TLDs to create jobs for
            start_hour: Starting hour for first job
            interval_minutes: Minutes between each job
            job_type: Type of job to create
            
        Returns:
            List of created jobs
        """
        created_jobs = []
        current_hour = start_hour
        current_minute = 0
        
        for tld in tlds:
            # Skip if job already exists
            if self.get_by_tld(tld):
                continue
            
            try:
                job_data = CronJobCreate(
                    name=f"{tld.upper()} Zone Import",
                    tld=tld.lower(),
                    cron_hour=current_hour,
                    cron_minute=current_minute,
                    job_type=job_type,
                    is_enabled=True
                )
                
                job = self.create(job_data)
                created_jobs.append(job)
                
                # Increment time
                current_minute += interval_minutes
                if current_minute >= 60:
                    current_minute = current_minute % 60
                    current_hour = (current_hour + 1) % 24
                    
            except Exception as e:
                logger.error(f"Failed to create job for TLD {tld}: {e}")
                continue
        
        logger.info(f"Bulk created {len(created_jobs)} cron jobs")
        return created_jobs
    
    # ============== Job Execution ==============
    
    def run_job(self, job_id: int) -> Optional[CronJobLog]:
        """
        Execute a cron job immediately.
        
        Args:
            job_id: Job ID to run
            
        Returns:
            CronJobLog entry or None if failed
        """
        job = self.get_by_id(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return None
        
        return self._execute_job(job)
    
    def _execute_job(self, job: CronJob) -> CronJobLog:
        """
        Internal method to execute a job.
        
        Args:
            job: CronJob to execute
            
        Returns:
            CronJobLog entry
        """
        from datetime import timedelta
        
        # Create log entry
        log = CronJobLog(
            job_id=job.id,
            started_at=datetime.utcnow(),
            status=LogStatus.SUCCESS
        )
        self.db.add(log)
        
        # Update job status
        job.last_status = JobStatus.RUNNING
        job.last_run_at = datetime.utcnow()
        self.db.commit()
        
        try:
            logger.info(f"Starting execution of job {job.id} for TLD {job.tld}")
            
            today = date.today()
            yesterday = today - timedelta(days=1)
            domains_found = 0
            drops_detected = 0
            file_size_mb = 0.0
            
            settings = get_settings()
            zone_path = Path(settings.DATA_DIR) / "zones" / job.tld.lower() / f"{today.strftime('%Y%m%d')}.zone"
            
            # Execute based on job type
            if job.job_type in [JobType.DOWNLOAD_ONLY, JobType.FULL]:
                # Download zone file
                client = CZDSClient()
                zone_path = client.download_zone_by_tld(job.tld, today)
                
                if zone_path.exists():
                    file_size_mb = zone_path.stat().st_size / (1024 * 1024)
                    logger.info(f"Downloaded zone file: {zone_path} ({file_size_mb:.2f} MB)")
            
            if job.job_type in [JobType.PARSE_ONLY, JobType.FULL]:
                # Parse zone file and detect drops
                try:
                    # Load today's SLDs
                    today_slds = load_sld_set_for_day(job.tld, today)
                    domains_found = len(today_slds)
                    
                    # Try to load yesterday's SLDs for comparison
                    try:
                        yesterday_slds = load_sld_set_for_day(job.tld, yesterday)
                        
                        # Compute dropped SLDs
                        dropped_slds = compute_dropped_slds(yesterday_slds, today_slds)
                        
                        if dropped_slds:
                            # Get or create TLD record
                            tld_record = self.db.query(Tld).filter(Tld.name == job.tld.lower()).first()
                            if not tld_record:
                                tld_record = Tld(name=job.tld.lower(), is_active=True)
                                self.db.add(tld_record)
                                self.db.commit()
                                self.db.refresh(tld_record)
                            
                            # Persist drops
                            drops_detected = persist_drops(self.db, tld_record, today, dropped_slds)
                        
                        logger.info(f"Parsed {domains_found} domains, detected {drops_detected} drops")
                        
                    except FileNotFoundError:
                        logger.warning(f"Yesterday's zone file not found for {job.tld}, skipping drop detection")
                        
                except FileNotFoundError as e:
                    logger.warning(f"Today's zone file not found for {job.tld}: {e}")
            
            # Update log with success
            log.finished_at = datetime.utcnow()
            log.status = LogStatus.SUCCESS
            log.domains_found = domains_found
            log.drops_detected = drops_detected
            log.file_size_mb = file_size_mb
            log.execution_time_sec = int((log.finished_at - log.started_at).total_seconds())
            
            # Update job statistics
            job.last_status = JobStatus.SUCCESS
            job.last_error = None
            job.total_runs += 1
            job.success_count += 1
            job.next_run_at = scheduler_service.calculate_next_run(job.cron_hour, job.cron_minute)
            
            self.db.commit()
            logger.info(f"Job {job.id} completed successfully")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Job {job.id} failed: {error_msg}")
            
            # Update log with failure
            log.finished_at = datetime.utcnow()
            log.status = LogStatus.FAILED
            log.error_message = error_msg
            log.execution_time_sec = int((log.finished_at - log.started_at).total_seconds())
            
            # Update job statistics
            job.last_status = JobStatus.FAILED
            job.last_error = error_msg
            job.total_runs += 1
            job.next_run_at = scheduler_service.calculate_next_run(job.cron_hour, job.cron_minute)
            
            self.db.commit()
        
        self.db.refresh(log)
        return log
    
    def _register_job_with_scheduler(self, job: CronJob) -> None:
        """Register a job with the scheduler service."""
        scheduler_service.add_job(
            job_id=job.id,
            func=self._job_callback,
            hour=job.cron_hour,
            minute=job.cron_minute,
            args=(job.id,)
        )
    
    @staticmethod
    def _job_callback(job_id: int) -> None:
        """
        Callback function for scheduled job execution.
        Creates its own database session.
        """
        db = SessionLocal()
        try:
            service = CronJobService(db)
            service.run_job(job_id)
        finally:
            db.close()
    
    # ============== Logs ==============
    
    def get_job_logs(
        self,
        job_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[CronJobLog], int]:
        """Get logs for a specific job."""
        total = (
            self.db.query(func.count(CronJobLog.id))
            .filter(CronJobLog.job_id == job_id)
            .scalar()
        )
        
        logs = (
            self.db.query(CronJobLog)
            .filter(CronJobLog.job_id == job_id)
            .order_by(CronJobLog.started_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        return logs, total
    
    def get_all_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[LogStatus] = None
    ) -> Tuple[List[CronJobLog], int]:
        """Get all logs with optional status filter."""
        query = self.db.query(CronJobLog)
        
        if status:
            query = query.filter(CronJobLog.status == status)
        
        total = query.count()
        
        logs = (
            query
            .order_by(CronJobLog.started_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        return logs, total
    
    # ============== Scheduler Integration ==============
    
    def initialize_scheduler(self) -> None:
        """
        Initialize the scheduler with all enabled jobs.
        Should be called on application startup.
        """
        jobs = self.get_enabled_jobs()
        
        for job in jobs:
            self._register_job_with_scheduler(job)
        
        logger.info(f"Initialized scheduler with {len(jobs)} jobs")
    
    def get_scheduler_status(self) -> dict:
        """Get current scheduler status."""
        status = scheduler_service.get_status()
        status['enabled_count'] = self.get_enabled_count()
        status['running_count'] = self.get_running_count()
        return status

