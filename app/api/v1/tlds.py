"""
API endpoints for TLD management.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tld import Tld
from app.schemas.tld import TldRead

router = APIRouter()


@router.get("/tlds", response_model=List[TldRead])
def list_tlds(
    db: Session = Depends(get_db)
) -> List[TldRead]:
    """
    Get list of all tracked TLDs.
    """
    tlds = db.query(Tld).order_by(Tld.name).all()
    return tlds











