"""
API endpoints for API key management.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.subscription import ApiKey
from app.services.api_key_service import ApiKeyService
from app.web.auth_web import get_current_user_from_cookie
from fastapi import Request

router = APIRouter()


# ============== Schemas ==============

class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key: str  # Only shown once on creation
    is_active: bool
    requests_count: int
    created_at: str
    last_used_at: str | None
    
    class Config:
        from_attributes = True


class ApiKeyListResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    requests_count: int
    requests_count_monthly: int
    created_at: str
    last_used_at: str | None
    
    class Config:
        from_attributes = True


# ============== Endpoints ==============

@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    request: Request,
    api_key_data: ApiKeyCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new API key.
    Requires Pro or Business plan.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = ApiKeyService(db)
        api_key = service.create_api_key(
            user=user,
            name=api_key_data.name
        )
        
        # Get plain key from temporary storage
        plain_key = getattr(api_key, '_plain_key', None)
        if not plain_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API key could not be retrieved"
            )
        
        return ApiKeyResponse(
            id=api_key.id,
            name=api_key.name,
            key=plain_key,  # Show key only on creation
            is_active=api_key.is_active,
            requests_count=api_key.requests_count,
            created_at=api_key.created_at.isoformat(),
            last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.get("/api-keys", response_model=List[ApiKeyListResponse])
def list_api_keys(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    List user's API keys (keys are not shown for security).
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    service = ApiKeyService(db)
    api_keys = service.get_user_api_keys(user)
    
    return [
        ApiKeyListResponse(
            id=key.id,
            name=key.name,
            is_active=key.is_active,
            requests_count=key.requests_count,
            requests_count_monthly=key.requests_count_monthly,
            created_at=key.created_at.isoformat(),
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None
        )
        for key in api_keys
    ]


@router.delete("/api-keys/{key_id}")
def revoke_api_key(
    request: Request,
    key_id: int,
    db: Session = Depends(get_db)
):
    """
    Revoke (deactivate) an API key.
    """
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    service = ApiKeyService(db)
    success = service.revoke_api_key(user, key_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {"message": "API key revoked successfully"}


