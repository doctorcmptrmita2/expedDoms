"""
Whois Service for domain registration information.
"""
import logging
import socket
from datetime import datetime, date
from typing import Optional, Dict, Any, List
import re

logger = logging.getLogger(__name__)

# Whois servers for common TLDs
WHOIS_SERVERS = {
    "com": "whois.verisign-grs.com",
    "net": "whois.verisign-grs.com",
    "org": "whois.pir.org",
    "info": "whois.afilias.net",
    "biz": "whois.biz",
    "io": "whois.nic.io",
    "co": "whois.nic.co",
    "dev": "whois.nic.google",
    "app": "whois.nic.google",
    "ai": "whois.nic.ai",
    "me": "whois.nic.me",
    "tv": "whois.nic.tv",
    "cc": "ccwhois.verisign-grs.com",
    "name": "whois.nic.name",
    "pro": "whois.afilias.net",
    "cloud": "whois.nic.cloud",
    "online": "whois.nic.online",
    "site": "whois.nic.site",
    "tech": "whois.nic.tech",
    "store": "whois.nic.store",
    "shop": "whois.nic.shop",
}

# Date patterns commonly found in whois data
DATE_PATTERNS = [
    r"(\d{4}-\d{2}-\d{2})",  # 2024-01-15
    r"(\d{2}-\w{3}-\d{4})",  # 15-Jan-2024
    r"(\d{2}/\d{2}/\d{4})",  # 01/15/2024
    r"(\d{4}/\d{2}/\d{2})",  # 2024/01/15
    r"(\d{2}\s+\w{3}\s+\d{4})",  # 15 Jan 2024
]


class WhoisService:
    """Service for querying Whois information."""
    
    def __init__(self, timeout: int = 10):
        """
        Initialize Whois service.
        
        Args:
            timeout: Socket timeout in seconds
        """
        self.timeout = timeout
    
    def query(self, domain: str) -> Optional[str]:
        """
        Query whois server for domain information.
        
        Args:
            domain: Domain to query (e.g., "example.com")
            
        Returns:
            Raw whois response or None
        """
        # Extract TLD
        parts = domain.lower().split(".")
        if len(parts) < 2:
            return None
        
        tld = parts[-1]
        whois_server = WHOIS_SERVERS.get(tld)
        
        if not whois_server:
            # Try generic whois server
            whois_server = f"whois.nic.{tld}"
        
        try:
            # Connect to whois server
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((whois_server, 43))
            
            # Send query
            sock.send(f"{domain}\r\n".encode())
            
            # Receive response
            response = b""
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                response += data
            
            sock.close()
            
            return response.decode("utf-8", errors="ignore")
            
        except socket.timeout:
            logger.warning(f"Whois timeout for {domain}")
            return None
        except socket.gaierror:
            logger.warning(f"Whois server not found for {domain}")
            return None
        except Exception as e:
            logger.error(f"Whois query failed for {domain}: {e}")
            return None
    
    def parse_whois(self, raw_whois: str) -> Dict[str, Any]:
        """
        Parse raw whois data into structured format.
        
        Args:
            raw_whois: Raw whois response
            
        Returns:
            Parsed whois data
        """
        result = {
            "registrar": None,
            "creation_date": None,
            "updated_date": None,
            "expiry_date": None,
            "name_servers": [],
            "status": [],
            "registrant": None
        }
        
        if not raw_whois:
            return result
        
        lines = raw_whois.split("\n")
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("%") or line.startswith("#"):
                continue
            
            line_lower = line.lower()
            
            # Registrar
            if "registrar:" in line_lower and not result["registrar"]:
                result["registrar"] = self._extract_value(line)
            
            # Creation date
            if any(x in line_lower for x in ["creation date:", "created:", "registered:"]):
                if not result["creation_date"]:
                    result["creation_date"] = self._parse_date(line)
            
            # Updated date
            if any(x in line_lower for x in ["updated date:", "last updated:", "modified:"]):
                if not result["updated_date"]:
                    result["updated_date"] = self._parse_date(line)
            
            # Expiry date
            if any(x in line_lower for x in ["expir", "registry expiry", "paid-till:"]):
                if not result["expiry_date"]:
                    result["expiry_date"] = self._parse_date(line)
            
            # Name servers
            if "name server:" in line_lower or "nserver:" in line_lower:
                ns = self._extract_value(line)
                if ns and ns not in result["name_servers"]:
                    result["name_servers"].append(ns.lower())
            
            # Status
            if "status:" in line_lower:
                status = self._extract_value(line)
                if status:
                    result["status"].append(status)
            
            # Registrant
            if "registrant" in line_lower and "name:" in line_lower:
                if not result["registrant"]:
                    result["registrant"] = self._extract_value(line)
        
        return result
    
    def _extract_value(self, line: str) -> Optional[str]:
        """Extract value after colon."""
        if ":" in line:
            return line.split(":", 1)[1].strip()
        return None
    
    def _parse_date(self, line: str) -> Optional[date]:
        """Parse date from whois line."""
        for pattern in DATE_PATTERNS:
            match = re.search(pattern, line)
            if match:
                date_str = match.group(1)
                return self._convert_to_date(date_str)
        return None
    
    def _convert_to_date(self, date_str: str) -> Optional[date]:
        """Convert various date formats to date object."""
        formats = [
            "%Y-%m-%d",
            "%d-%b-%Y",
            "%m/%d/%Y",
            "%Y/%m/%d",
            "%d %b %Y",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def get_domain_info(self, domain: str) -> Dict[str, Any]:
        """
        Get comprehensive whois info for a domain.
        
        Args:
            domain: Domain to query
            
        Returns:
            Parsed whois data with additional fields
        """
        raw_whois = self.query(domain)
        
        if not raw_whois:
            return {
                "domain": domain,
                "available": True,  # Likely available if no whois
                "error": "No whois data found"
            }
        
        parsed = self.parse_whois(raw_whois)
        
        result = {
            "domain": domain,
            "available": False,
            "registrar": parsed["registrar"],
            "creation_date": parsed["creation_date"],
            "updated_date": parsed["updated_date"],
            "expiry_date": parsed["expiry_date"],
            "name_servers": parsed["name_servers"],
            "status": parsed["status"],
            "registrant": parsed["registrant"],
            "raw_whois": raw_whois
        }
        
        # Calculate domain age
        if parsed["creation_date"]:
            age_days = (date.today() - parsed["creation_date"]).days
            result["domain_age_days"] = age_days
            result["domain_age_years"] = round(age_days / 365.25, 1)
        
        return result


def get_domain_whois(domain: str) -> Dict[str, Any]:
    """
    Get whois info for a domain.
    
    Args:
        domain: Domain to query
        
    Returns:
        Whois data dictionary
    """
    service = WhoisService()
    return service.get_domain_info(domain)






