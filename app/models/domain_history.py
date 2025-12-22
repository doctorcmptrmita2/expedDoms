"""
Domain History model for storing Wayback Machine and Whois data.
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class DomainHistory(Base):
    """Stores historical information about domains."""
    
    __tablename__ = "domain_histories"
    
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(255), nullable=False, index=True, unique=True)
    
    # Wayback Machine data
    wayback_snapshots = Column(Integer, default=0, nullable=False)
    wayback_first_snapshot = Column(Date, nullable=True)
    wayback_last_snapshot = Column(Date, nullable=True)
    archive_url = Column(String(500), nullable=True)
    
    # Whois data
    first_registered = Column(Date, nullable=True)
    last_updated = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    registrar = Column(String(255), nullable=True)
    
    # Previous owners (JSON list)
    previous_owners = Column(JSON, nullable=True)
    
    # Domain age (calculated)
    domain_age_days = Column(Integer, nullable=True)
    
    # Raw whois data
    whois_raw = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<DomainHistory(domain={self.domain}, snapshots={self.wayback_snapshots})>"
    
    @property
    def domain_age_years(self) -> float | None:
        """Calculate domain age in years."""
        if self.domain_age_days:
            return round(self.domain_age_days / 365.25, 1)
        return None








