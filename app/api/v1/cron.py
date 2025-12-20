"""
Cron Jobs API endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.cron_job_service import CronJobService
from app.services.scheduler_service import scheduler_service
from app.models.cron_job import JobStatus, LogStatus
from app.schemas.cron import (
    CronJobCreate,
    CronJobUpdate,
    CronJobRead,
    CronJobListResponse,
    CronJobLogRead,
    CronJobLogListResponse,
    SchedulerStatus,
    BulkCreateRequest,
    BulkCreateResponse,
    ManualRunResponse
)

router = APIRouter(prefix="/cron", tags=["Cron Jobs"])


# ============== Scheduler Endpoints ==============

@router.get("/scheduler/status", response_model=SchedulerStatus)
def get_scheduler_status(db: Session = Depends(get_db)):
    """Get current scheduler status."""
    service = CronJobService(db)
    status_data = service.get_scheduler_status()
    return SchedulerStatus(**status_data)


@router.post("/scheduler/start")
def start_scheduler():
    """Start the scheduler."""
    success = scheduler_service.start()
    if success:
        return {"message": "Scheduler started successfully", "is_running": True}
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to start scheduler"
    )


@router.post("/scheduler/stop")
def stop_scheduler():
    """Stop the scheduler."""
    success = scheduler_service.stop()
    if success:
        return {"message": "Scheduler stopped successfully", "is_running": False}
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to stop scheduler"
    )


# ============== Job CRUD Endpoints ==============

@router.get("/jobs", response_model=CronJobListResponse)
def list_jobs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all cron jobs."""
    service = CronJobService(db)
    jobs, total = service.get_all(skip=skip, limit=limit)
    
    return CronJobListResponse(
        items=[CronJobRead.model_validate(job) for job in jobs],
        total=total,
        enabled_count=service.get_enabled_count(),
        running_count=service.get_running_count()
    )


@router.post("/jobs", response_model=CronJobRead, status_code=status.HTTP_201_CREATED)
def create_job(data: CronJobCreate, db: Session = Depends(get_db)):
    """Create a new cron job."""
    service = CronJobService(db)
    
    try:
        job = service.create(data)
        return CronJobRead.model_validate(job)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/jobs/{job_id}", response_model=CronJobRead)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get a cron job by ID."""
    service = CronJobService(db)
    job = service.get_by_id(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return CronJobRead.model_validate(job)


@router.put("/jobs/{job_id}", response_model=CronJobRead)
def update_job(job_id: int, data: CronJobUpdate, db: Session = Depends(get_db)):
    """Update a cron job."""
    service = CronJobService(db)
    job = service.update(job_id, data)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return CronJobRead.model_validate(job)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """Delete a cron job."""
    service = CronJobService(db)
    success = service.delete(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )


@router.post("/jobs/{job_id}/toggle", response_model=CronJobRead)
def toggle_job(job_id: int, db: Session = Depends(get_db)):
    """Toggle job enabled/disabled status."""
    service = CronJobService(db)
    job = service.toggle_enabled(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return CronJobRead.model_validate(job)


@router.post("/jobs/{job_id}/run", response_model=ManualRunResponse)
def run_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually run a cron job."""
    service = CronJobService(db)
    job = service.get_by_id(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    if job.last_status == JobStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job {job_id} is already running"
        )
    
    # Run in background
    background_tasks.add_task(CronJobService._job_callback, job_id)
    
    return ManualRunResponse(
        success=True,
        message=f"Job {job_id} started",
        job_id=job_id
    )


# ============== Bulk Operations ==============

@router.post("/bulk-create", response_model=BulkCreateResponse)
def bulk_create_jobs(data: BulkCreateRequest, db: Session = Depends(get_db)):
    """Bulk create cron jobs for multiple TLDs."""
    service = CronJobService(db)
    
    jobs = service.bulk_create(
        tlds=data.tlds,
        start_hour=data.start_hour,
        interval_minutes=data.interval_minutes,
        job_type=data.job_type
    )
    
    return BulkCreateResponse(
        created_count=len(jobs),
        jobs=[CronJobRead.model_validate(job) for job in jobs]
    )


# ============== Job Logs ==============

@router.get("/jobs/{job_id}/logs", response_model=CronJobLogListResponse)
def get_job_logs(
    job_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get logs for a specific job."""
    service = CronJobService(db)
    
    # Verify job exists
    job = service.get_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    logs, total = service.get_job_logs(job_id, skip=skip, limit=limit)
    
    return CronJobLogListResponse(
        items=[CronJobLogRead.model_validate(log) for log in logs],
        total=total
    )


@router.get("/logs", response_model=CronJobLogListResponse)
def get_all_logs(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all job logs with optional status filter."""
    service = CronJobService(db)
    
    log_status = None
    if status_filter:
        try:
            log_status = LogStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    logs, total = service.get_all_logs(skip=skip, limit=limit, status=log_status)
    
    return CronJobLogListResponse(
        items=[CronJobLogRead.model_validate(log) for log in logs],
        total=total
    )





