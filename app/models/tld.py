"""
TLD model for tracking top-level domains.
"""
from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime
from sqlalchemy.orm import relationship

from app.core.database import Base


class Tld(Base):
    """Model representing a tracked TLD."""
    
    __tablename__ = "tlds"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_import_date = Column(Date, nullable=True)
    last_drop_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    dropped_domains = relationship("DroppedDomain", back_populates="tld", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Tld(name={self.name}, is_active={self.is_active})>"











