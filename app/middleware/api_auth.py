"""
API Key authentication middleware.
"""
from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyHeader

from app.models.user import User
from app.services.api_key_service import ApiKeyService
from app.core.database import get_db
from sqlalchemy.orm import Session

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_user_from_api_key(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get user from API key header.
    
    Returns None if no API key provided or invalid.
    """
    if not api_key:
        return None
    
    service = ApiKeyService(db)
    user = service.authenticate(api_key)
    
    return user


async def require_api_key(
    api_key: Optional[str] = Depends(api_key_header),
    db: Session = Depends(get_db)
) -> User:
    """
    Require valid API key authentication.
    
    Raises 401 if API key is missing or invalid.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    service = ApiKeyService(db)
    user = service.authenticate(api_key)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    return user


