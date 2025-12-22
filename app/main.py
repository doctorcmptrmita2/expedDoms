"""
FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

# Get settings (may fail if .env is missing, but that's OK for health check)
try:
    settings = get_settings()
    app_title = settings.APP_NAME
except Exception:
    app_title = "ExpiredDomain.dev"

from app.api.v1 import tlds, drops, czds, process, import_api, auth, users, quality, notifications, history, stats, cron, subscriptions, favorites, watchlists, api_keys, export
from app.web import routes, admin, domains, debug, auth_web, stats_web, cron_web, admin_dashboard, subscription_web, favorites_web, watchlist_web, deleted_domains, droptoday

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info("Starting application...")
    
    # Initialize and start the scheduler
    try:
        from app.services.scheduler_service import scheduler_service
        from app.services.cron_job_service import CronJobService
        from app.core.database import SessionLocal
        
        # Start scheduler
        scheduler_service.start()
        logger.info("Scheduler started")
        
        # Load existing cron jobs into scheduler
        db = SessionLocal()
        try:
            service = CronJobService(db)
            service.initialize_scheduler()
            logger.info("Cron jobs loaded into scheduler")
        finally:
            db.close()
            
    except Exception as e:
        logger.warning(f"Could not initialize scheduler: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    try:
        from app.services.scheduler_service import scheduler_service
        scheduler_service.stop(wait=False)
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.warning(f"Error stopping scheduler: {e}")

# Create FastAPI app
app = FastAPI(
    title=app_title,
    description="Daily dropped domains explorer using ICANN CZDS zone files",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (minimal for now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (with error handling)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    # Log error but don't fail startup if static directory doesn't exist
    import logging
    logging.warning(f"Could not mount static files: {e}")

# Include API routers
app.include_router(tlds.router, prefix="/api/v1", tags=["TLDs"])
app.include_router(drops.router, prefix="/api/v1", tags=["Drops"])
app.include_router(czds.router, prefix="/api/v1", tags=["CZDS"])
app.include_router(process.router, prefix="/api/v1", tags=["Process"])
app.include_router(import_api.router, prefix="/api/v1", tags=["Import"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(quality.router, prefix="/api/v1/quality", tags=["Quality Score"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(history.router, prefix="/api/v1/history", tags=["Domain History"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["Statistics"])
app.include_router(cron.router, prefix="/api/v1", tags=["Cron Jobs"])
app.include_router(subscriptions.router, prefix="/api/v1", tags=["Subscriptions"])
app.include_router(favorites.router, prefix="/api/v1", tags=["Favorites"])
app.include_router(watchlists.router, prefix="/api/v1", tags=["Watchlists"])
app.include_router(api_keys.router, prefix="/api/v1", tags=["API Keys"])
app.include_router(export.router, prefix="/api/v1", tags=["Export"])

# Stripe webhook (no prefix, direct path)
from app.api.v1 import stripe_webhook
app.include_router(stripe_webhook.router, tags=["Stripe"])

# Include web routes
app.include_router(routes.router, tags=["Web"])
app.include_router(admin.router, tags=["Admin"])
app.include_router(admin_dashboard.router, tags=["Admin Dashboard"])
app.include_router(domains.router, tags=["Domains"])
app.include_router(debug.router, tags=["Debug"])
app.include_router(auth_web.router, tags=["Auth Web"])
app.include_router(stats_web.router, tags=["Stats Web"])
app.include_router(cron_web.router, tags=["Cron Web"])
app.include_router(subscription_web.router, tags=["Subscription Web"])
app.include_router(favorites_web.router, tags=["Favorites Web"])
app.include_router(watchlist_web.router, tags=["Watchlist Web"])
app.include_router(deleted_domains.router, tags=["Deleted Domains"])
app.include_router(droptoday.router, tags=["Drop Today"])


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

