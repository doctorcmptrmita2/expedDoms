"""
Web routes for statistics dashboard.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/stats", response_class=HTMLResponse)
def stats_dashboard(request: Request):
    """
    Render the statistics dashboard page.
    """
    return templates.TemplateResponse(
        "stats/dashboard.html",
        {"request": request}
    )


@router.get("/analytics", response_class=HTMLResponse)
def analytics_redirect(request: Request):
    """
    Redirect alias for stats dashboard.
    """
    return templates.TemplateResponse(
        "stats/dashboard.html",
        {"request": request}
    )






