"""
Pydantic schemas for TLD.
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class TldBase(BaseModel):
    """Base schema for TLD."""
    name: str
    display_name: Optional[str] = None
    is_active: bool = True


class TldCreate(TldBase):
    """Schema for creating a TLD."""
    pass


class TldRead(TldBase):
    """Schema for reading TLD data."""
    id: int
    last_import_date: Optional[date] = None
    last_drop_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True









