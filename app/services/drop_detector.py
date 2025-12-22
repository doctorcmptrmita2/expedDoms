"""
Drop detection logic: compare zone files and persist dropped domains.
"""
from datetime import date
from pathlib import Path
from typing import Set
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.tld import Tld
from app.models.drop import DroppedDomain
from app.services.zone_parser import extract_slds_from_zone, build_domain_name
from app.core.config import get_settings


def load_sld_set_for_day(tld: str, day: date) -> Set[str]:
    """
    Load set of SLDs from zone file for a specific day.
    
    Args:
        tld: Top-level domain
        day: Date to load zone file for
        
    Returns:
        Set of SLD strings
        
    Raises:
        FileNotFoundError: If zone file doesn't exist
    """
    settings = get_settings()
    date_str = day.strftime("%Y%m%d")
    zone_path = Path(settings.DATA_DIR) / "zones" / tld.lower() / f"{date_str}.zone"
    
    return extract_slds_from_zone(zone_path, tld)


def compute_dropped_slds(prev_set: Set[str], current_set: Set[str]) -> Set[str]:
    """
    Compute which SLDs were dropped (present yesterday, missing today).
    
    Args:
        prev_set: Set of SLDs from previous day
        current_set: Set of SLDs from current day
        
    Returns:
        Set of dropped SLDs
    """
    return prev_set - current_set


def _determine_charset_type(sld: str) -> str:
    """
    Determine charset type of an SLD.
    
    Args:
        sld: Second-level domain string
        
    Returns:
        "letters", "numbers", or "mixed"
    """
    if sld.isalpha():
        return "letters"
    elif sld.isdigit():
        return "numbers"
    else:
        return "mixed"


def persist_drops(db: Session, tld: Tld, drop_date: date, slds: Set[str]) -> int:
    """
    Persist dropped domains to database and trigger watchlist matching.
    
    Args:
        db: Database session
        tld: TLD model instance
        drop_date: Date when domains were dropped
        slds: Set of dropped SLDs
        
    Returns:
        Number of domains successfully persisted
    """
    persisted_count = 0
    persisted_domains = []  # Collect persisted domains for watchlist matching
    
    for sld in sorted(slds):
        domain = build_domain_name(sld, tld.name)
        
        # Compute metadata
        length = len(sld)
        label_count = 1  # Reserved for future use
        charset_type = _determine_charset_type(sld)
        
        # Create dropped domain record
        dropped_domain = DroppedDomain(
            domain=domain,
            tld_id=tld.id,
            drop_date=drop_date,
            length=length,
            label_count=label_count,
            charset_type=charset_type
        )
        
        try:
            db.add(dropped_domain)
            db.commit()
            db.refresh(dropped_domain)  # Refresh to get ID
            persisted_count += 1
            persisted_domains.append(dropped_domain)
        except IntegrityError:
            # Domain already exists for this date, skip
            db.rollback()
            continue
    
    # Update TLD metadata
    tld.last_import_date = drop_date
    tld.last_drop_count = persisted_count
    db.commit()
    
    # Trigger watchlist matching for persisted domains
    if persisted_domains:
        try:
            from app.services.watchlist_matcher import WatchlistMatcher
            matcher = WatchlistMatcher(db)
            match_result = matcher.match_dropped_domains(persisted_domains)
            if match_result["total_matches"] > 0:
                logger = __import__('logging').getLogger(__name__)
                logger.info(f"Watchlist matching: {match_result['total_matches']} matches found for {len(persisted_domains)} dropped domains")
        except Exception as e:
            # Log error but don't fail drop detection
            logger = __import__('logging').getLogger(__name__)
            logger.warning(f"Watchlist matching error: {e}")
    
    return persisted_count

