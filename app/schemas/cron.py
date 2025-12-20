"""
Pydantic schemas for Cron Job API.
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class JobType(str, Enum):
    """Types of cron jobs."""
    DOWNLOAD_ONLY = "DOWNLOAD_ONLY"
    PARSE_ONLY = "PARSE_ONLY"
    FULL = "FULL"


class JobStatus(str, Enum):
    """Status of a cron job."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class LogStatus(str, Enum):
    """Status of a cron job log entry."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


# ============== CronJob Schemas ==============

class CronJobBase(BaseModel):
    """Base schema for CronJob."""
    name: str = Field(..., min_length=1, max_length=100, description="Job name")
    tld: str = Field(..., min_length=1, max_length=50, description="TLD to process")
    cron_hour: int = Field(default=2, ge=0, le=23, description="Hour to run (0-23)")
    cron_minute: int = Field(default=0, ge=0, le=59, description="Minute to run (0-59)")
    job_type: JobType = Field(default=JobType.FULL, description="Type of job")
    is_enabled: bool = Field(default=True, description="Whether job is enabled")
    priority: int = Field(default=5, ge=1, le=10, description="Priority (1-10, lower = higher)")
    timeout_minutes: int = Field(default=60, ge=1, le=480, description="Timeout in minutes")
    retry_count: int = Field(default=3, ge=0, le=10, description="Number of retries")


class CronJobCreate(CronJobBase):
    """Schema for creating a CronJob."""
    pass


class CronJobUpdate(BaseModel):
    """Schema for updating a CronJob."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    cron_hour: Optional[int] = Field(None, ge=0, le=23)
    cron_minute: Optional[int] = Field(None, ge=0, le=59)
    job_type: Optional[JobType] = None
    is_enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    timeout_minutes: Optional[int] = Field(None, ge=1, le=480)
    retry_count: Optional[int] = Field(None, ge=0, le=10)


class CronJobRead(CronJobBase):
    """Schema for reading a CronJob."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_status: JobStatus
    last_error: Optional[str] = None
    total_runs: int
    success_count: int
    created_at: datetime
    updated_at: datetime
    schedule_display: str
    success_rate: float


class CronJobListResponse(BaseModel):
    """Response schema for listing CronJobs."""
    items: List[CronJobRead]
    total: int
    enabled_count: int
    running_count: int


# ============== CronJobLog Schemas ==============

class CronJobLogBase(BaseModel):
    """Base schema for CronJobLog."""
    job_id: int
    status: LogStatus
    domains_found: int = 0
    drops_detected: int = 0
    file_size_mb: float = 0.0
    error_message: Optional[str] = None
    execution_time_sec: int = 0


class CronJobLogCreate(CronJobLogBase):
    """Schema for creating a CronJobLog."""
    started_at: datetime
    finished_at: Optional[datetime] = None


class CronJobLogRead(CronJobLogBase):
    """Schema for reading a CronJobLog."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    started_at: datetime
    finished_at: Optional[datetime] = None


class CronJobLogListResponse(BaseModel):
    """Response schema for listing CronJobLogs."""
    items: List[CronJobLogRead]
    total: int


# ============== Scheduler Schemas ==============

class SchedulerStatus(BaseModel):
    """Schema for scheduler status."""
    is_running: bool
    job_count: int
    active_jobs: int
    running_jobs: int
    next_job: Optional[str] = None
    next_run_at: Optional[datetime] = None


class BulkCreateRequest(BaseModel):
    """Schema for bulk creating cron jobs."""
    tlds: List[str] = Field(..., min_length=1, description="List of TLDs")
    start_hour: int = Field(default=0, ge=0, le=23, description="Starting hour")
    interval_minutes: int = Field(default=30, ge=5, le=120, description="Interval between jobs")
    job_type: JobType = Field(default=JobType.FULL, description="Type of job")


class BulkCreateResponse(BaseModel):
    """Response schema for bulk create."""
    created_count: int
    jobs: List[CronJobRead]


class ManualRunResponse(BaseModel):
    """Response schema for manual job run."""
    success: bool
    message: str
    job_id: int
    log_id: Optional[int] = None

