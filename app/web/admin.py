"""
Admin panel routes for CZDS management.
"""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import status

from app.services.czds_client import CZDSClient
from app.core.config import get_settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request):
    """
    CZDS Admin Panel - Main page.
    """
    settings = get_settings()
    
    # Check if credentials are configured
    has_credentials = bool(settings.CZDS_USERNAME and settings.CZDS_PASSWORD)
    
    token_info = None
    zones = []
    zones_error = None
    
    # Try to authenticate and list zones if credentials are available
    if has_credentials:
        try:
            client = CZDSClient()
            # Try to authenticate
            try:
                auth_result = client.authenticate()
                token_info = client.get_token_info()
                
                # Try to list zones
                try:
                    zones = client.list_zones()
                except Exception as e:
                    zones_error = f"Failed to list zones: {str(e)}"
            except ValueError as e:
                # Invalid credentials
                zones_error = f"Authentication failed: {str(e)}"
            except Exception as e:
                zones_error = f"Authentication error: {str(e)}"
        except Exception as e:
            zones_error = f"Error: {str(e)}"
    
    try:
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "has_credentials": has_credentials,
            "token_info": token_info or {},
            "zones": zones[:50] if zones else [],  # Limit to 50 for display
            "zones_count": len(zones) if zones else 0,
            "zones_error": zones_error
        })
    except Exception as e:
        # Return error page if template rendering fails
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(f"Template error: {str(e)}", status_code=500)


@router.post("/admin/authenticate", response_class=HTMLResponse)
def authenticate_admin(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """
    Authenticate with CZDS API.
    """
    client = CZDSClient(username=username, password=password)
    
    try:
        result = client.authenticate()
        # Store credentials in session or return success
        return templates.TemplateResponse("admin_auth_success.html", {
            "request": request,
            "success": True,
            "token_info": result
        })
    except Exception as e:
        return templates.TemplateResponse("admin_auth_error.html", {
            "request": request,
            "error": str(e)
        })

