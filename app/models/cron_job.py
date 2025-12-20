"""
Cron Job models for scheduled task management.
"""
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class JobType(str, PyEnum):
    """Types of cron jobs."""
    DOWNLOAD_ONLY = "DOWNLOAD_ONLY"
    PARSE_ONLY = "PARSE_ONLY"
    FULL = "FULL"


class JobStatus(str, PyEnum):
    """Status of a cron job."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class LogStatus(str, PyEnum):
    """Status of a cron job log entry."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class CronJob(Base):
    """Model representing a scheduled cron job for TLD zone processing."""
    
    __tablename__ = "cron_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    tld = Column(String(50), nullable=False, index=True)
    
    # Schedule configuration
    cron_hour = Column(Integer, nullable=False, default=2)  # 0-23
    cron_minute = Column(Integer, nullable=False, default=0)  # 0-59
    
    # Job configuration
    job_type = Column(Enum(JobType), nullable=False, default=JobType.FULL)
    is_enabled = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=5, nullable=False)  # 1-10, lower = higher priority
    timeout_minutes = Column(Integer, default=60, nullable=False)
    retry_count = Column(Integer, default=3, nullable=False)
    
    # Execution tracking
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    last_status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    last_error = Column(Text, nullable=True)
    
    # Statistics
    total_runs = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    logs = relationship("CronJobLog", back_populates="job", cascade="all, delete-orphan", lazy="dynamic")
    
    def __repr__(self) -> str:
        return f"<CronJob(id={self.id}, name={self.name}, tld={self.tld}, enabled={self.is_enabled})>"
    
    @property
    def schedule_display(self) -> str:
        """Return human-readable schedule."""
        return f"{self.cron_hour:02d}:{self.cron_minute:02d}"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_runs == 0:
            return 0.0
        return (self.success_count / self.total_runs) * 100


class CronJobLog(Base):
    """Model representing a log entry for a cron job execution."""
    
    __tablename__ = "cron_job_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("cron_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Execution times
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    
    # Results
    status = Column(Enum(LogStatus), nullable=False, default=LogStatus.SUCCESS)
    domains_found = Column(Integer, default=0, nullable=False)
    drops_detected = Column(Integer, default=0, nullable=False)
    file_size_mb = Column(Float, default=0.0, nullable=False)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Computed
    execution_time_sec = Column(Integer, default=0, nullable=False)
    
    # Relationships
    job = relationship("CronJob", back_populates="logs")
    
    def __repr__(self) -> str:
        return f"<CronJobLog(id={self.id}, job_id={self.job_id}, status={self.status})>"

