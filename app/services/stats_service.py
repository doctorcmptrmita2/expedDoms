"""
Statistics Service for domain analytics.
Provides aggregated stats for dashboard charts.
"""
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import func, and_, case
from sqlalchemy.orm import Session

from app.models.drop import DroppedDomain
from app.models.tld import Tld


class StatsService:
    """Service for generating domain statistics."""
    
    def __init__(self, db: Session):
        """
        Initialize stats service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_daily_drops(
        self,
        days: int = 30,
        tld_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily drop counts for the last N days.
        
        Args:
            days: Number of days to look back
            tld_filter: Optional TLD to filter by
            
        Returns:
            List of {date, count} dicts
        """
        start_date = date.today() - timedelta(days=days)
        
        query = self.db.query(
            DroppedDomain.drop_date,
            func.count(DroppedDomain.id).label("count")
        ).filter(DroppedDomain.drop_date >= start_date)
        
        if tld_filter:
            tld = self.db.query(Tld).filter(Tld.name == tld_filter.lower()).first()
            if tld:
                query = query.filter(DroppedDomain.tld_id == tld.id)
        
        query = query.group_by(DroppedDomain.drop_date).order_by(DroppedDomain.drop_date)
        
        results = query.all()
        
        return [
            {"date": r.drop_date.isoformat(), "count": r.count}
            for r in results
        ]
    
    def get_tld_distribution(
        self,
        date_filter: Optional[date] = None,
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Get domain count distribution by TLD.
        
        Args:
            date_filter: Optional date to filter by
            limit: Number of top TLDs to return
            
        Returns:
            List of {tld, count, percentage} dicts
        """
        query = self.db.query(
            Tld.name,
            func.count(DroppedDomain.id).label("count")
        ).join(DroppedDomain)
        
        if date_filter:
            query = query.filter(DroppedDomain.drop_date == date_filter)
        
        query = query.group_by(Tld.name).order_by(func.count(DroppedDomain.id).desc())
        
        results = query.limit(limit).all()
        
        # Calculate total for percentages
        total = sum(r.count for r in results)
        
        return [
            {
                "tld": r.name,
                "count": r.count,
                "percentage": round(r.count / total * 100, 1) if total > 0 else 0
            }
            for r in results
        ]
    
    def get_length_distribution(
        self,
        date_filter: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get domain length distribution.
        
        Args:
            date_filter: Optional date to filter by
            
        Returns:
            List of {length, count} dicts
        """
        query = self.db.query(
            DroppedDomain.length,
            func.count(DroppedDomain.id).label("count")
        )
        
        if date_filter:
            query = query.filter(DroppedDomain.drop_date == date_filter)
        
        query = query.filter(DroppedDomain.length.isnot(None))
        query = query.group_by(DroppedDomain.length).order_by(DroppedDomain.length)
        
        results = query.all()
        
        return [
            {"length": r.length, "count": r.count}
            for r in results
        ]
    
    def get_charset_distribution(
        self,
        date_filter: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get charset type distribution.
        
        Args:
            date_filter: Optional date to filter by
            
        Returns:
            List of {charset, count, percentage} dicts
        """
        query = self.db.query(
            DroppedDomain.charset_type,
            func.count(DroppedDomain.id).label("count")
        )
        
        if date_filter:
            query = query.filter(DroppedDomain.drop_date == date_filter)
        
        query = query.filter(DroppedDomain.charset_type.isnot(None))
        query = query.group_by(DroppedDomain.charset_type)
        
        results = query.all()
        
        total = sum(r.count for r in results)
        
        # Map charset types to friendly names
        charset_names = {
            "letters": "Sadece Harf",
            "numeric": "Sadece Rakam",
            "alphanumeric": "Harf + Rakam",
            "hyphen": "Tire İçeren",
            "other": "Diğer"
        }
        
        return [
            {
                "charset": r.charset_type,
                "label": charset_names.get(r.charset_type, r.charset_type),
                "count": r.count,
                "percentage": round(r.count / total * 100, 1) if total > 0 else 0
            }
            for r in results
        ]
    
    def get_weekly_trends(self, weeks: int = 12) -> List[Dict[str, Any]]:
        """
        Get weekly drop trends.
        
        Args:
            weeks: Number of weeks to look back
            
        Returns:
            List of {week, year, count, avg_per_day} dicts
        """
        start_date = date.today() - timedelta(weeks=weeks)
        
        # Group by ISO week
        query = self.db.query(
            func.year(DroppedDomain.drop_date).label("year"),
            func.week(DroppedDomain.drop_date).label("week"),
            func.count(DroppedDomain.id).label("count"),
            func.min(DroppedDomain.drop_date).label("week_start")
        ).filter(
            DroppedDomain.drop_date >= start_date
        ).group_by(
            func.year(DroppedDomain.drop_date),
            func.week(DroppedDomain.drop_date)
        ).order_by(
            func.year(DroppedDomain.drop_date),
            func.week(DroppedDomain.drop_date)
        )
        
        results = query.all()
        
        return [
            {
                "year": r.year,
                "week": r.week,
                "week_start": r.week_start.isoformat() if r.week_start else None,
                "count": r.count,
                "avg_per_day": round(r.count / 7, 0)
            }
            for r in results
        ]
    
    def get_summary_stats(
        self,
        date_filter: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get summary statistics.
        
        Args:
            date_filter: Optional date to filter by
            
        Returns:
            Summary stats dict
        """
        query = self.db.query(DroppedDomain)
        
        if date_filter:
            query = query.filter(DroppedDomain.drop_date == date_filter)
        
        total_count = query.count()
        
        # Get unique TLD count
        tld_count_query = self.db.query(func.count(func.distinct(DroppedDomain.tld_id)))
        if date_filter:
            tld_count_query = tld_count_query.filter(DroppedDomain.drop_date == date_filter)
        unique_tlds = tld_count_query.scalar() or 0
        
        # Get average length
        avg_length_query = self.db.query(func.avg(DroppedDomain.length))
        if date_filter:
            avg_length_query = avg_length_query.filter(DroppedDomain.drop_date == date_filter)
        avg_length = avg_length_query.scalar() or 0
        
        # Get shortest domain
        shortest_query = self.db.query(func.min(DroppedDomain.length))
        if date_filter:
            shortest_query = shortest_query.filter(DroppedDomain.drop_date == date_filter)
        shortest = shortest_query.scalar() or 0
        
        # Get date range
        date_range_query = self.db.query(
            func.min(DroppedDomain.drop_date).label("first"),
            func.max(DroppedDomain.drop_date).label("last")
        )
        date_range = date_range_query.first()
        
        return {
            "total_domains": total_count,
            "unique_tlds": unique_tlds,
            "average_length": round(avg_length, 1),
            "shortest_length": shortest,
            "first_date": date_range.first.isoformat() if date_range.first else None,
            "last_date": date_range.last.isoformat() if date_range.last else None,
            "filter_date": date_filter.isoformat() if date_filter else None
        }
    
    def get_top_domains_by_length(
        self,
        max_length: int = 4,
        date_filter: Optional[date] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get shortest domains (most valuable).
        
        Args:
            max_length: Maximum length to include
            date_filter: Optional date filter
            limit: Number of results
            
        Returns:
            List of domain dicts
        """
        query = self.db.query(DroppedDomain).join(Tld).filter(
            DroppedDomain.length <= max_length
        )
        
        if date_filter:
            query = query.filter(DroppedDomain.drop_date == date_filter)
        
        query = query.order_by(DroppedDomain.length, DroppedDomain.domain).limit(limit)
        
        results = query.all()
        
        return [
            {
                "id": d.id,
                "domain": d.domain,
                "tld": d.tld.name if d.tld else "",
                "length": d.length,
                "charset": d.charset_type,
                "drop_date": d.drop_date.isoformat()
            }
            for d in results
        ]


def get_all_stats(db: Session, date_filter: Optional[date] = None) -> Dict[str, Any]:
    """
    Get all statistics for dashboard.
    
    Args:
        db: Database session
        date_filter: Optional date filter
        
    Returns:
        Complete stats dict for dashboard
    """
    service = StatsService(db)
    
    return {
        "summary": service.get_summary_stats(date_filter),
        "daily_drops": service.get_daily_drops(days=30),
        "tld_distribution": service.get_tld_distribution(date_filter),
        "length_distribution": service.get_length_distribution(date_filter),
        "charset_distribution": service.get_charset_distribution(date_filter),
        "weekly_trends": service.get_weekly_trends(weeks=12),
        "top_short_domains": service.get_top_domains_by_length(4, date_filter, 50)
    }








