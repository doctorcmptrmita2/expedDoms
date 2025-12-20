"""
API endpoints for statistics and analytics.
"""
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.stats_service import StatsService, get_all_stats

router = APIRouter()


# ============== Schemas ==============

class DailyDropItem(BaseModel):
    date: str
    count: int


class TldDistributionItem(BaseModel):
    tld: str
    count: int
    percentage: float


class LengthDistributionItem(BaseModel):
    length: int
    count: int


class CharsetDistributionItem(BaseModel):
    charset: str
    label: str
    count: int
    percentage: float


class WeeklyTrendItem(BaseModel):
    year: int
    week: int
    week_start: Optional[str]
    count: int
    avg_per_day: float


class SummaryStats(BaseModel):
    total_domains: int
    unique_tlds: int
    average_length: float
    shortest_length: int
    first_date: Optional[str]
    last_date: Optional[str]
    filter_date: Optional[str]


class ShortDomainItem(BaseModel):
    id: int
    domain: str
    tld: str
    length: int
    charset: Optional[str]
    drop_date: str


# ============== Endpoints ==============

@router.get("/summary", response_model=SummaryStats)
def get_summary_statistics(
    date_filter: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for the dashboard.
    """
    filter_date = None
    if date_filter:
        try:
            filter_date = date.fromisoformat(date_filter)
        except ValueError:
            pass
    
    service = StatsService(db)
    stats = service.get_summary_stats(filter_date)
    
    return SummaryStats(**stats)


@router.get("/daily-drops", response_model=list[DailyDropItem])
def get_daily_drop_stats(
    days: int = Query(30, ge=7, le=365, description="Number of days"),
    tld: Optional[str] = Query(None, description="Filter by TLD"),
    db: Session = Depends(get_db)
):
    """
    Get daily drop counts for line chart.
    """
    service = StatsService(db)
    data = service.get_daily_drops(days, tld)
    
    return [DailyDropItem(**item) for item in data]


@router.get("/tld-distribution", response_model=list[TldDistributionItem])
def get_tld_distribution_stats(
    date_filter: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    limit: int = Query(15, ge=5, le=50, description="Number of TLDs"),
    db: Session = Depends(get_db)
):
    """
    Get TLD distribution for pie chart.
    """
    filter_date = None
    if date_filter:
        try:
            filter_date = date.fromisoformat(date_filter)
        except ValueError:
            pass
    
    service = StatsService(db)
    data = service.get_tld_distribution(filter_date, limit)
    
    return [TldDistributionItem(**item) for item in data]


@router.get("/length-distribution", response_model=list[LengthDistributionItem])
def get_length_distribution_stats(
    date_filter: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get domain length distribution for bar chart.
    """
    filter_date = None
    if date_filter:
        try:
            filter_date = date.fromisoformat(date_filter)
        except ValueError:
            pass
    
    service = StatsService(db)
    data = service.get_length_distribution(filter_date)
    
    return [LengthDistributionItem(**item) for item in data]


@router.get("/charset-distribution", response_model=list[CharsetDistributionItem])
def get_charset_distribution_stats(
    date_filter: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get charset type distribution for doughnut chart.
    """
    filter_date = None
    if date_filter:
        try:
            filter_date = date.fromisoformat(date_filter)
        except ValueError:
            pass
    
    service = StatsService(db)
    data = service.get_charset_distribution(filter_date)
    
    return [CharsetDistributionItem(**item) for item in data]


@router.get("/weekly-trends", response_model=list[WeeklyTrendItem])
def get_weekly_trend_stats(
    weeks: int = Query(12, ge=4, le=52, description="Number of weeks"),
    db: Session = Depends(get_db)
):
    """
    Get weekly drop trends for trend analysis.
    """
    service = StatsService(db)
    data = service.get_weekly_trends(weeks)
    
    return [WeeklyTrendItem(**item) for item in data]


@router.get("/top-short-domains", response_model=list[ShortDomainItem])
def get_top_short_domains(
    max_length: int = Query(4, ge=2, le=10, description="Maximum length"),
    date_filter: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=10, le=200, description="Number of results"),
    db: Session = Depends(get_db)
):
    """
    Get shortest (most valuable) dropped domains.
    """
    filter_date = None
    if date_filter:
        try:
            filter_date = date.fromisoformat(date_filter)
        except ValueError:
            pass
    
    service = StatsService(db)
    data = service.get_top_domains_by_length(max_length, filter_date, limit)
    
    return [ShortDomainItem(**item) for item in data]


@router.get("/all")
def get_all_statistics(
    date_filter: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get all statistics for dashboard in a single request.
    """
    filter_date = None
    if date_filter:
        try:
            filter_date = date.fromisoformat(date_filter)
        except ValueError:
            pass
    
    return get_all_stats(db, filter_date)






