"""
Database models.
"""
from app.core.database import Base
from app.models.tld import Tld
from app.models.drop import DroppedDomain

__all__ = ["Base", "Tld", "DroppedDomain"]

