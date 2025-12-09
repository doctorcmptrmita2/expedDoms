"""
Dropped domain model.
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Integer, SmallInteger, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class DroppedDomain(Base):
    """Model representing a dropped domain."""
    
    __tablename__ = "dropped_domains"
    
    id = Column(BigInteger, primary_key=True, index=True)
    domain = Column(String(191), nullable=False, index=True)  # Reduced for MySQL index compatibility
    tld_id = Column(Integer, ForeignKey("tlds.id"), nullable=False, index=True)
    drop_date = Column(Date, nullable=False, index=True)
    length = Column(Integer, nullable=False)  # Length of SLD part
    label_count = Column(Integer, default=1, nullable=False)
    charset_type = Column(String(20), nullable=False)  # "letters", "numbers", "mixed"
    quality_score = Column(Integer, nullable=True)  # Reserved for future use
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    tld = relationship("Tld", back_populates="dropped_domains")
    
    # Unique constraint: same domain cannot be dropped twice on the same date
    __table_args__ = (
        Index("idx_domain_drop_date", "domain", "drop_date", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<DroppedDomain(domain={self.domain}, drop_date={self.drop_date})>"

