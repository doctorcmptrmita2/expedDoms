"""
Pydantic schemas for dropped domains.
"""
from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class DropRead(BaseModel):
    """Schema for reading a dropped domain."""
    id: int
    domain: str
    tld: str  # TLD name (from relationship)
    drop_date: date
    length: int
    charset_type: str
    
    class Config:
        from_attributes = True


class DropListResponse(BaseModel):
    """Schema for paginated drop list response."""
    total: int
    page: int
    page_size: int
    results: List[DropRead]

