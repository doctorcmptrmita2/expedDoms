"""
Import logging service for tracking parse operations.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json

# Setup file logger
LOG_DIR = Path("./data/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("import_logger")

# File handler for persistent logs
file_handler = logging.FileHandler(LOG_DIR / "import.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(file_handler)


class ImportLogger:
    """Logger for import operations with progress tracking."""
    
    def __init__(self, tld: str, operation: str = "parse"):
        self.tld = tld
        self.operation = operation
        self.start_time = datetime.now()
        self.progress = 0
        self.total = 0
        self.errors = []
        self.warnings = []
        self.stats = {}
        
    def start(self, total: int = 0):
        """Start the operation."""
        self.total = total
        self.progress = 0
        logger.info(f"[{self.tld}] Starting {self.operation} - Total items: {total}")
        
    def update_progress(self, current: int, message: str = ""):
        """Update progress."""
        self.progress = current
        if self.total > 0:
            percent = (current / self.total) * 100
            if message:
                logger.debug(f"[{self.tld}] {percent:.1f}% - {message}")
                
    def log_error(self, message: str, exception: Optional[Exception] = None):
        """Log an error."""
        error_msg = f"[{self.tld}] ERROR: {message}"
        if exception:
            error_msg += f" - {str(exception)}"
        logger.error(error_msg)
        self.errors.append({
            "time": datetime.now().isoformat(),
            "message": message,
            "exception": str(exception) if exception else None
        })
        
    def log_warning(self, message: str):
        """Log a warning."""
        logger.warning(f"[{self.tld}] WARNING: {message}")
        self.warnings.append({
            "time": datetime.now().isoformat(),
            "message": message
        })
        
    def log_info(self, message: str):
        """Log info message."""
        logger.info(f"[{self.tld}] {message}")
        
    def set_stat(self, key: str, value: Any):
        """Set a statistic."""
        self.stats[key] = value
        
    def complete(self, success: bool = True):
        """Complete the operation and return summary."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        summary = {
            "tld": self.tld,
            "operation": self.operation,
            "success": success,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "progress": self.progress,
            "total": self.total,
            "errors": self.errors,
            "warnings": self.warnings,
            "stats": self.stats
        }
        
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"[{self.tld}] {self.operation} {status} - Duration: {duration:.1f}s - Errors: {len(self.errors)}")
        
        # Save detailed log to file
        log_file = LOG_DIR / f"{self.tld}_{self.operation}_{end_time.strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save log file: {e}")
            
        return summary


def get_recent_logs(tld: Optional[str] = None, limit: int = 20) -> list:
    """Get recent import logs."""
    logs = []
    try:
        log_files = sorted(LOG_DIR.glob("*.json"), reverse=True)[:limit]
        for log_file in log_files:
            if tld and not log_file.name.startswith(tld):
                continue
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs.append(json.load(f))
            except:
                pass
    except:
        pass
    return logs








