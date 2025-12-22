"""
Export service for CSV and Excel exports.
"""
import io
import logging
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd

from sqlalchemy.orm import Session

from app.models.user import User, UserFavorite, UserWatchlist
from app.models.drop import DroppedDomain
from app.services.subscription_service import SubscriptionService, get_subscription_service

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting data to CSV/Excel."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def export_favorites_to_csv(self, user: User) -> bytes:
        """
        Export user's favorites to CSV.
        
        Args:
            user: User to export favorites for
            
        Returns:
            CSV file as bytes
        """
        favorites = self.db.query(UserFavorite).filter(
            UserFavorite.user_id == user.id
        ).order_by(UserFavorite.created_at.desc()).all()
        
        # Build data
        data = []
        for fav in favorites:
            domain = self.db.query(DroppedDomain).filter(
                DroppedDomain.id == fav.domain_id
            ).first()
            
            if domain:
                data.append({
                    "Domain": domain.domain,
                    "TLD": domain.tld.name if domain.tld else "",
                    "Drop Date": domain.drop_date.isoformat() if domain.drop_date else "",
                    "Length": domain.length,
                    "Charset Type": domain.charset_type or "",
                    "Quality Score": domain.quality_score if domain.quality_score else "",
                    "Notes": fav.notes or "",
                    "Added At": fav.created_at.isoformat()
                })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Convert to CSV
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')  # UTF-8 with BOM for Excel
        output.seek(0)
        
        return output.read()
    
    def export_favorites_to_excel(self, user: User) -> bytes:
        """
        Export user's favorites to Excel.
        Requires Pro or Business plan.
        
        Args:
            user: User to export favorites for
            
        Returns:
            Excel file as bytes
        """
        # Check plan
        subscription_service = get_subscription_service(self.db)
        if not subscription_service.can_access_feature(user, "export_excel"):
            raise ValueError("Excel export requires Pro or Business plan")
        
        favorites = self.db.query(UserFavorite).filter(
            UserFavorite.user_id == user.id
        ).order_by(UserFavorite.created_at.desc()).all()
        
        # Build data
        data = []
        for fav in favorites:
            domain = self.db.query(DroppedDomain).filter(
                DroppedDomain.id == fav.domain_id
            ).first()
            
            if domain:
                data.append({
                    "Domain": domain.domain,
                    "TLD": domain.tld.name if domain.tld else "",
                    "Drop Date": domain.drop_date.isoformat() if domain.drop_date else "",
                    "Length": domain.length,
                    "Charset Type": domain.charset_type or "",
                    "Quality Score": domain.quality_score if domain.quality_score else "",
                    "Notes": fav.notes or "",
                    "Added At": fav.created_at.isoformat()
                })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Convert to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Favorites')
        
        output.seek(0)
        return output.read()
    
    def export_watchlist_matches_to_csv(self, user: User, watchlist_id: int) -> bytes:
        """
        Export watchlist matches to CSV.
        
        Args:
            user: User who owns the watchlist
            watchlist_id: Watchlist ID
            
        Returns:
            CSV file as bytes
        """
        # Verify watchlist ownership
        watchlist = self.db.query(UserWatchlist).filter(
            UserWatchlist.id == watchlist_id,
            UserWatchlist.user_id == user.id
        ).first()
        
        if not watchlist:
            raise ValueError("Watchlist not found")
        
        # Get matches from domain history (if available)
        # For now, return empty CSV with headers
        data = []
        
        # Create DataFrame
        df = pd.DataFrame(data, columns=[
            "Domain", "TLD", "Drop Date", "Length", "Charset Type", 
            "Quality Score", "Matched At"
        ])
        
        # Convert to CSV
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)
        
        return output.read()
    
    def export_watchlist_matches_to_excel(self, user: User, watchlist_id: int) -> bytes:
        """
        Export watchlist matches to Excel.
        Requires Pro or Business plan.
        
        Args:
            user: User who owns the watchlist
            watchlist_id: Watchlist ID
            
        Returns:
            Excel file as bytes
        """
        # Check plan
        subscription_service = get_subscription_service(self.db)
        if not subscription_service.can_access_feature(user, "export_enabled"):
            raise ValueError("Excel export requires Pro or Business plan")
        
        # Verify watchlist ownership
        watchlist = self.db.query(UserWatchlist).filter(
            UserWatchlist.id == watchlist_id,
            UserWatchlist.user_id == user.id
        ).first()
        
        if not watchlist:
            raise ValueError("Watchlist not found")
        
        # Get matches from domain history (if available)
        # For now, return empty Excel with headers
        data = []
        
        # Create DataFrame
        df = pd.DataFrame(data, columns=[
            "Domain", "TLD", "Drop Date", "Length", "Charset Type", 
            "Quality Score", "Matched At"
        ])
        
        # Convert to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Matches')
        
        output.seek(0)
        return output.read()


