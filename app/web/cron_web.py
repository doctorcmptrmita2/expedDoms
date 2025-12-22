"""
Web routes for Cron Jobs management page.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.cron_job_service import CronJobService

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin/cron", response_class=HTMLResponse)
def cron_jobs_page(request: Request, db: Session = Depends(get_db)):
    """
    Cron Jobs management page.
    """
    service = CronJobService(db)
    
    # Get jobs and stats
    jobs, total = service.get_all(limit=200)
    scheduler_status = service.get_scheduler_status()
    
    # Calculate stats
    enabled_count = service.get_enabled_count()
    running_count = service.get_running_count()
    
    # Calculate success rate
    total_runs = sum(job.total_runs for job in jobs)
    success_runs = sum(job.success_count for job in jobs)
    success_rate = (success_runs / total_runs * 100) if total_runs > 0 else 0
    
    # Get TLDs for dropdown (from existing TLD table)
    from app.models.tld import Tld
    tlds = db.query(Tld).filter(Tld.is_active == True).order_by(Tld.name).all()
    
    return templates.TemplateResponse("admin/cron_jobs.html", {
        "request": request,
        "jobs": jobs,
        "total_jobs": total,
        "enabled_count": enabled_count,
        "running_count": running_count,
        "success_rate": success_rate,
        "scheduler_status": scheduler_status,
        "tlds": tlds
    })







