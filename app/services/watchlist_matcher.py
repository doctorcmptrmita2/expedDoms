"""
Watchlist matching service for dropped domains.
"""
import re
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.user import UserWatchlist, User
from app.models.drop import DroppedDomain
from app.models.notification import Notification, NotificationChannel, NotificationStatus
from app.services.notification_service import NotificationService
from app.core.config import get_settings

import logging
logger = logging.getLogger(__name__)


class WatchlistMatcher:
    """Service for matching dropped domains against user watchlists."""
    
    def __init__(self, db: Session):
        """
        Initialize watchlist matcher.
        
        Args:
            db: Database session
        """
        self.db = db
        settings = get_settings()
        self.notification_service = NotificationService(
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            smtp_user=settings.SMTP_USER,
            smtp_password=settings.SMTP_PASSWORD,
            smtp_from=settings.SMTP_FROM
        )
    
    def match_dropped_domains(self, dropped_domains: List[DroppedDomain]) -> Dict[str, Any]:
        """
        Match dropped domains against all active watchlists.
        
        Args:
            dropped_domains: List of DroppedDomain objects
            
        Returns:
            Dictionary with match statistics
        """
        # Get all active watchlists
        watchlists = self.db.query(UserWatchlist).filter(
            UserWatchlist.is_active == True
        ).all()
        
        matches = []
        total_matched = 0
        
        for watchlist in watchlists:
            for domain in dropped_domains:
                if self._matches_watchlist(domain, watchlist):
                    matches.append({
                        "watchlist_id": watchlist.id,
                        "watchlist_name": watchlist.name,
                        "user_id": watchlist.user_id,
                        "domain_id": domain.id,
                        "domain": domain.domain,
                        "tld": domain.tld.name if domain.tld else "",
                        "drop_date": domain.drop_date.isoformat() if domain.drop_date else None,
                        "quality_score": domain.quality_score
                    })
                    total_matched += 1
        
        # Create notifications for matches
        if matches:
            self._create_notifications(matches)
        
        return {
            "total_domains": len(dropped_domains),
            "total_watchlists": len(watchlists),
            "total_matches": total_matched,
            "matches": matches
        }
    
    def _matches_watchlist(self, domain: DroppedDomain, watchlist: UserWatchlist) -> bool:
        """
        Check if a domain matches watchlist criteria.
        
        Args:
            domain: DroppedDomain object
            watchlist: UserWatchlist object
            
        Returns:
            True if domain matches watchlist
        """
        # Extract domain name (without TLD)
        domain_name = domain.domain.split('.')[0] if '.' in domain.domain else domain.domain
        
        # Check domain pattern (regex)
        if watchlist.domain_pattern:
            try:
                pattern = watchlist.domain_pattern.replace('*', '.*')  # Simple wildcard support
                if not re.search(pattern, domain_name, re.IGNORECASE):
                    return False
            except re.error:
                # Invalid regex, skip pattern check
                pass
        
        # Check TLD filter
        if watchlist.tld_filter:
            tlds = [t.strip().lower() for t in watchlist.tld_filter.split(',')]
            domain_tld = domain.tld.name.lower() if domain.tld else ""
            if domain_tld not in tlds:
                return False
        
        # Check length filter
        if watchlist.min_length and domain.length < watchlist.min_length:
            return False
        if watchlist.max_length and domain.length > watchlist.max_length:
            return False
        
        # Check charset filter
        if watchlist.charset_filter:
            if watchlist.charset_filter == "letters" and not domain_name.isalpha():
                return False
            elif watchlist.charset_filter == "numbers" and not domain_name.isdigit():
                return False
            elif watchlist.charset_filter == "mixed" and not (domain_name.isalnum() and not domain_name.isalpha() and not domain_name.isdigit()):
                return False
        
        # Check quality score filter
        if watchlist.min_quality_score and domain.quality_score:
            if domain.quality_score < watchlist.min_quality_score:
                return False
        
        return True
    
    def _create_notifications(self, matches: List[Dict[str, Any]]):
        """
        Create and send notifications for watchlist matches.
        
        Args:
            matches: List of match dictionaries
        """
        # Group matches by user and watchlist
        user_watchlist_matches = {}
        for match in matches:
            key = (match["user_id"], match["watchlist_id"])
            if key not in user_watchlist_matches:
                user_watchlist_matches[key] = {
                    "user_id": match["user_id"],
                    "watchlist_id": match["watchlist_id"],
                    "watchlist_name": match["watchlist_name"],
                    "domains": []
                }
            user_watchlist_matches[key]["domains"].append(match)
        
        # Process each user-watchlist combination
        for (user_id, watchlist_id), match_data in user_watchlist_matches.items():
            try:
                # Get user and watchlist
                user = self.db.query(User).filter(User.id == user_id).first()
                watchlist = self.db.query(UserWatchlist).filter(UserWatchlist.id == watchlist_id).first()
                
                if not user or not watchlist:
                    continue
                
                domain_count = len(match_data["domains"])
                watchlist_name = match_data["watchlist_name"]
                
                # Prepare domain list for notification
                domain_list = []
                for match in match_data["domains"][:20]:  # Limit to 20 domains
                    domain_list.append({
                        "domain": match["domain"],
                        "tld": match["tld"],
                        "score": match.get("quality_score", 0)
                    })
                
                # Format message
                plain_text, html_text = self._format_watchlist_alert(domain_list, watchlist_name, domain_count)
                
                # Send notifications based on watchlist settings
                if watchlist.notify_email:
                    subject = f"🔔 Watchlist Alert: {watchlist_name} - {domain_count} Domain(s) Found"
                    self.notification_service.notify_user(
                        self.db,
                        user,
                        plain_text,
                        subject=subject,
                        data={"matches": match_data["domains"], "watchlist_id": watchlist_id},
                        channels=[NotificationChannel.EMAIL]
                    )
                    logger.info(f"Email notification sent to user {user_id} for watchlist {watchlist_name}")
                
                # Update watchlist last_notified_at
                from datetime import datetime
                watchlist.last_notified_at = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Error creating notification for user {user_id}, watchlist {watchlist_id}: {e}")
                continue
        
        self.db.commit()
    
    def _format_watchlist_alert(
        self,
        domains: List[Dict[str, Any]],
        watchlist_name: str,
        total_count: int
    ) -> tuple[str, str]:
        """
        Format watchlist alert message.
        
        Args:
            domains: List of domain dictionaries
            watchlist_name: Name of the watchlist
            total_count: Total number of matched domains
            
        Returns:
            Tuple of (plain_text, html_text)
        """
        plain_lines = [
            f"🔔 Watchlist Alert: {watchlist_name}",
            f"",
            f"Found {total_count} matching dropped domain(s):",
            f""
        ]
        
        html_lines = [
            f"<h2>🔔 Watchlist Alert: {watchlist_name}</h2>",
            f"<p>Found <strong>{total_count}</strong> matching dropped domain(s):</p>",
            f"<ul>"
        ]
        
        for d in domains:
            domain_str = f"{d['domain']}.{d['tld']}"
            score = d.get('score', 0)
            plain_lines.append(f"• {domain_str} (Score: {score})")
            html_lines.append(f"<li><strong>{domain_str}</strong> - Quality Score: {score}</li>")
        
        if total_count > len(domains):
            remaining = total_count - len(domains)
            plain_lines.append(f"... and {remaining} more domain(s)")
            html_lines.append(f"<li>... and {remaining} more domain(s)</li>")
        
        html_lines.append("</ul>")
        
        # Add footer
        settings = get_settings()
        app_url = settings.APP_URL
        plain_lines.append("")
        plain_lines.append(f"Visit {app_url}/watchlists to see all matches and manage your watchlists.")
        
        html_lines.append(f"<p><a href='{app_url}/watchlists'>View all matches and manage watchlists</a></p>")
        
        return "\n".join(plain_lines), "\n".join(html_lines)

