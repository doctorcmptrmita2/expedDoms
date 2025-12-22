"""
Progress tracking service for long-running import operations.
Uses in-memory storage (can be replaced with Redis in production).
"""
from typing import Dict, Optional
from datetime import datetime
import uuid
import threading

# Thread-safe progress storage
_progress_store: Dict[str, Dict] = {}
_lock = threading.Lock()


class ProgressTracker:
    """Track progress of long-running operations."""
    
    def __init__(self, job_id: Optional[str] = None):
        """
        Initialize progress tracker.
        
        Args:
            job_id: Optional job ID, will generate if not provided
        """
        self.job_id = job_id or str(uuid.uuid4())
        self.start_time = datetime.now()
        
        with _lock:
            _progress_store[self.job_id] = {
                "status": "running",
                "progress": 0,
                "total": 0,
                "current": 0,
                "message": "Starting...",
                "start_time": self.start_time.isoformat(),
                "updated_at": self.start_time.isoformat(),
                "details": {}
            }
    
    def update(
        self, 
        current: int, 
        total: int, 
        message: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        """
        Update progress.
        
        Args:
            current: Current progress count
            total: Total items to process
            message: Optional status message
            details: Optional additional details
        """
        progress_pct = int((current / total * 100)) if total > 0 else 0
        
        with _lock:
            if self.job_id in _progress_store:
                _progress_store[self.job_id].update({
                    "progress": progress_pct,
                    "total": total,
                    "current": current,
                    "updated_at": datetime.now().isoformat(),
                    "message": message or f"Processing {current}/{total}...",
                    "details": details or _progress_store[self.job_id].get("details", {})
                })
    
    def complete(self, success: bool = True, message: Optional[str] = None, details: Optional[Dict] = None):
        """
        Mark job as complete.
        
        Args:
            success: Whether job completed successfully
            message: Optional completion message
            details: Optional final details
        """
        with _lock:
            if self.job_id in _progress_store:
                _progress_store[self.job_id].update({
                    "status": "completed" if success else "failed",
                    "updated_at": datetime.now().isoformat(),
                    "message": message or ("Completed" if success else "Failed"),
                    "details": details or _progress_store[self.job_id].get("details", {})
                })
    
    def get_status(self) -> Optional[Dict]:
        """Get current status."""
        with _lock:
            return _progress_store.get(self.job_id)
    
    @staticmethod
    def get_job_status(job_id: str) -> Optional[Dict]:
        """Get status for a specific job ID."""
        with _lock:
            return _progress_store.get(job_id)
    
    @staticmethod
    def cleanup_old_jobs(max_age_hours: int = 24):
        """Remove old completed jobs from memory."""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        with _lock:
            to_remove = []
            for job_id, job_data in _progress_store.items():
                if job_data.get("status") in ("completed", "failed"):
                    updated = datetime.fromisoformat(job_data.get("updated_at", datetime.now().isoformat()))
                    if updated < cutoff:
                        to_remove.append(job_id)
            
            for job_id in to_remove:
                del _progress_store[job_id]
    
    @staticmethod
    def list_jobs() -> Dict[str, Dict]:
        """List all active jobs."""
        with _lock:
            return _progress_store.copy()


