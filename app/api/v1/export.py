"""
API endpoints for data export (CSV/Excel).
"""
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.export_service import ExportService
from app.web.auth_web import get_current_user_from_cookie
from fastapi import Request

router = APIRouter()


@router.get("/export/favorites/csv")
def export_favorites_csv(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Export user's favorites to CSV.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = ExportService(db)
        csv_data = service.export_favorites_to_csv(user)
        
        filename = f"favorites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            io.BytesIO(csv_data),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@router.get("/export/favorites/excel")
def export_favorites_excel(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Export user's favorites to Excel.
    Requires Pro or Business plan.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = ExportService(db)
        excel_data = service.export_favorites_to_excel(user)
        
        filename = f"favorites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@router.get("/export/watchlist/{watchlist_id}/csv")
def export_watchlist_matches_csv(
    request: Request,
    watchlist_id: int,
    db: Session = Depends(get_db)
):
    """
    Export watchlist matches to CSV.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = ExportService(db)
        csv_data = service.export_watchlist_matches_to_csv(user, watchlist_id)
        
        filename = f"watchlist_{watchlist_id}_matches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            io.BytesIO(csv_data),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


@router.get("/export/watchlist/{watchlist_id}/excel")
def export_watchlist_matches_excel(
    request: Request,
    watchlist_id: int,
    db: Session = Depends(get_db)
):
    """
    Export watchlist matches to Excel.
    Requires Pro or Business plan.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = ExportService(db)
        excel_data = service.export_watchlist_matches_to_excel(user, watchlist_id)
        
        filename = f"watchlist_{watchlist_id}_matches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if "plan" in str(e).lower() else status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


