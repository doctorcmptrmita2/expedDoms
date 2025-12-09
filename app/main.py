"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1 import tlds, drops, czds, process
from app.web import routes, admin

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Daily dropped domains explorer using ICANN CZDS zone files",
    version="1.0.0"
)

# CORS middleware (minimal for now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routers
app.include_router(tlds.router, prefix="/api/v1", tags=["TLDs"])
app.include_router(drops.router, prefix="/api/v1", tags=["Drops"])
app.include_router(czds.router, prefix="/api/v1", tags=["CZDS"])
app.include_router(process.router, prefix="/api/v1", tags=["Process"])

# Include web routes
app.include_router(routes.router, tags=["Web"])
app.include_router(admin.router, tags=["Admin"])


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

