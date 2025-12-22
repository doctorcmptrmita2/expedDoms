"""
API endpoints for dropped domains.
"""
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.core.database import get_db
from app.models.drop import DroppedDomain
from app.models.tld import Tld
from app.schemas.drop import DropRead, DropListResponse

router = APIRouter()


@router.get("/drops", response_model=DropListResponse)
def list_drops(
    date_filter: Optional[date] = Query(None, alias="date", description="Filter by drop date"),
    tld: Optional[str] = Query(None, description="Filter by TLD name"),
    search: Optional[str] = Query(None, description="Search in domain names"),
    min_length: Optional[int] = Query(None, ge=1, description="Minimum SLD length"),
    max_length: Optional[int] = Query(None, ge=1, description="Maximum SLD length"),
    charset_type: Optional[str] = Query(None, description="Filter by charset type (letters/numbers/mixed)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size"),
    db: Session = Depends(get_db)
) -> DropListResponse:
    """
    Get paginated list of dropped domains with filters.
    
    If no date is provided, defaults to the latest available date in the database.
    """
    # Build query
    query = db.query(DroppedDomain).join(Tld)
    
    # Date filter: if not provided, use latest date
    if date_filter is None:
        latest_date = db.query(func.max(DroppedDomain.drop_date)).scalar()
        if latest_date:
            date_filter = latest_date
        else:
            # No data in database
            return DropListResponse(total=0, page=1, page_size=page_size, results=[])
    
    query = query.filter(DroppedDomain.drop_date == date_filter)
    
    # TLD filter
    if tld:
        query = query.filter(Tld.name == tld.lower())
    
    # Search filter
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                DroppedDomain.domain.ilike(search_term)
            )
        )
    
    # Length filters
    if min_length is not None:
        query = query.filter(DroppedDomain.length >= min_length)
    if max_length is not None:
        query = query.filter(DroppedDomain.length <= max_length)
    
    # Charset filter
    if charset_type:
        query = query.filter(DroppedDomain.charset_type == charset_type.lower())
    
    # Get total count
    total = query.count()
    
    # Pagination
    offset = (page - 1) * page_size
    drops = query.order_by(DroppedDomain.domain).offset(offset).limit(page_size).all()
    
    # Convert to schema (include TLD name)
    results = [
        DropRead(
            id=drop.id,
            domain=drop.domain,
            tld=drop.tld.name,
            drop_date=drop.drop_date,
            length=drop.length,
            charset_type=drop.charset_type
        )
        for drop in drops
    ]
    
    return DropListResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=results
    )











