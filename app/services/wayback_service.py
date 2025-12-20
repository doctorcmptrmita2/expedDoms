"""
Wayback Machine (Internet Archive) Service.
Fetches historical snapshots and archive data for domains.
"""
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any, List
import requests

logger = logging.getLogger(__name__)

# Wayback Machine API endpoints
WAYBACK_AVAILABILITY_API = "https://archive.org/wayback/available"
WAYBACK_CDX_API = "https://web.archive.org/cdx/search/cdx"
WAYBACK_SAVE_API = "https://web.archive.org/save"


class WaybackService:
    """Service for interacting with the Wayback Machine API."""
    
    def __init__(self, timeout: int = 15):
        """
        Initialize Wayback service.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ExpiredDomain.dev/1.0 (Domain Research Tool)"
        })
    
    def check_availability(self, domain: str) -> Dict[str, Any]:
        """
        Check if a domain has any archived snapshots.
        
        Args:
            domain: Domain to check (e.g., "example.com")
            
        Returns:
            Dict with availability info
        """
        try:
            url = f"{WAYBACK_AVAILABILITY_API}?url={domain}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("archived_snapshots", {}).get("closest"):
                snapshot = data["archived_snapshots"]["closest"]
                return {
                    "available": True,
                    "url": snapshot.get("url"),
                    "timestamp": snapshot.get("timestamp"),
                    "status": snapshot.get("status")
                }
            
            return {"available": False}
            
        except Exception as e:
            logger.error(f"Wayback availability check failed for {domain}: {e}")
            return {"available": False, "error": str(e)}
    
    def get_snapshot_count(self, domain: str) -> Dict[str, Any]:
        """
        Get total number of snapshots for a domain.
        
        Args:
            domain: Domain to check
            
        Returns:
            Dict with snapshot count and date range
        """
        try:
            # Use CDX API to get snapshot info
            params = {
                "url": domain,
                "output": "json",
                "fl": "timestamp",
                "collapse": "digest",  # Deduplicate similar snapshots
                "limit": 10000
            }
            
            response = self.session.get(
                WAYBACK_CDX_API,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # First row is headers
            if len(data) > 1:
                snapshots = data[1:]  # Skip header
                timestamps = [row[0] for row in snapshots]
                
                # Parse timestamps
                first_ts = timestamps[-1] if timestamps else None  # Oldest
                last_ts = timestamps[0] if timestamps else None    # Newest
                
                first_date = self._parse_timestamp(first_ts) if first_ts else None
                last_date = self._parse_timestamp(last_ts) if last_ts else None
                
                return {
                    "count": len(snapshots),
                    "first_snapshot": first_date,
                    "last_snapshot": last_date,
                    "archive_url": f"https://web.archive.org/web/*/{domain}"
                }
            
            return {
                "count": 0,
                "first_snapshot": None,
                "last_snapshot": None,
                "archive_url": None
            }
            
        except Exception as e:
            logger.error(f"Wayback snapshot count failed for {domain}: {e}")
            return {
                "count": 0,
                "error": str(e)
            }
    
    def get_snapshots_list(
        self,
        domain: str,
        limit: int = 100,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of snapshots for a domain.
        
        Args:
            domain: Domain to check
            limit: Maximum number of snapshots to return
            from_date: Start date (YYYYMMDD format)
            to_date: End date (YYYYMMDD format)
            
        Returns:
            List of snapshot dictionaries
        """
        try:
            params = {
                "url": domain,
                "output": "json",
                "fl": "timestamp,original,mimetype,statuscode,digest",
                "filter": "statuscode:200",
                "collapse": "timestamp:6",  # Group by month
                "limit": limit
            }
            
            if from_date:
                params["from"] = from_date
            if to_date:
                params["to"] = to_date
            
            response = self.session.get(
                WAYBACK_CDX_API,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if len(data) <= 1:
                return []
            
            # Parse results (skip header row)
            headers = data[0]
            snapshots = []
            
            for row in data[1:]:
                snapshot = dict(zip(headers, row))
                snapshot["date"] = self._parse_timestamp(snapshot.get("timestamp"))
                snapshot["archive_url"] = f"https://web.archive.org/web/{snapshot.get('timestamp')}/{snapshot.get('original')}"
                snapshots.append(snapshot)
            
            return snapshots
            
        except Exception as e:
            logger.error(f"Wayback snapshots list failed for {domain}: {e}")
            return []
    
    def get_earliest_snapshot(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Get the earliest snapshot for a domain.
        
        Args:
            domain: Domain to check
            
        Returns:
            Snapshot info or None
        """
        try:
            params = {
                "url": domain,
                "output": "json",
                "fl": "timestamp,original,statuscode",
                "filter": "statuscode:200",
                "limit": 1,
                "sort": "timestamp:asc"  # Oldest first
            }
            
            response = self.session.get(
                WAYBACK_CDX_API,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if len(data) > 1:
                headers = data[0]
                row = data[1]
                snapshot = dict(zip(headers, row))
                snapshot["date"] = self._parse_timestamp(snapshot.get("timestamp"))
                snapshot["archive_url"] = f"https://web.archive.org/web/{snapshot.get('timestamp')}/{snapshot.get('original')}"
                return snapshot
            
            return None
            
        except Exception as e:
            logger.error(f"Wayback earliest snapshot failed for {domain}: {e}")
            return None
    
    def _parse_timestamp(self, timestamp: str) -> Optional[date]:
        """Parse Wayback timestamp to date."""
        if not timestamp or len(timestamp) < 8:
            return None
        try:
            return datetime.strptime(timestamp[:8], "%Y%m%d").date()
        except ValueError:
            return None


def get_domain_wayback_info(domain: str) -> Dict[str, Any]:
    """
    Get comprehensive Wayback Machine info for a domain.
    
    Args:
        domain: Domain to check
        
    Returns:
        Dict with all Wayback data
    """
    service = WaybackService()
    
    # Get snapshot count and date range
    snapshot_info = service.get_snapshot_count(domain)
    
    # Get availability check
    availability = service.check_availability(domain)
    
    result = {
        "domain": domain,
        "wayback_snapshots": snapshot_info.get("count", 0),
        "first_snapshot": snapshot_info.get("first_snapshot"),
        "last_snapshot": snapshot_info.get("last_snapshot"),
        "archive_url": snapshot_info.get("archive_url"),
        "has_archive": availability.get("available", False),
        "latest_archive_url": availability.get("url")
    }
    
    # Calculate domain "web age" if we have first snapshot
    if result["first_snapshot"]:
        days_since_first = (date.today() - result["first_snapshot"]).days
        result["web_age_days"] = days_since_first
        result["web_age_years"] = round(days_since_first / 365.25, 1)
    
    return result






