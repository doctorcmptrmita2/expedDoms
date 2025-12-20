"""
Zone file parser for extracting second-level domains.
"""
from pathlib import Path
from typing import Set


def extract_slds_from_zone(zone_path: Path, tld: str) -> Set[str]:
    """
    Parse a zone file and extract unique second-level domains (SLDs).
    
    Args:
        zone_path: Path to the zone file
        tld: Top-level domain (e.g., "zip")
        
    Returns:
        Set of SLD strings (e.g., {"example", "test", "cool-name"})
        
    Raises:
        FileNotFoundError: If zone file doesn't exist
    """
    if not zone_path.exists():
        raise FileNotFoundError(f"Zone file not found: {zone_path}")
    
    slds: Set[str] = set()
    tld_lower = tld.lower()
    tld_with_dot = f".{tld_lower}"
    
    with open(zone_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            # Skip empty lines and comments
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            
            # Parse zone file record
            # Format is typically: FQDN [TTL] [IN] TYPE RDATA
            # We only care about the FQDN (first field)
            parts = line.split()
            if not parts:
                continue
            
            fqdn = parts[0]
            
            # Normalize: remove trailing dot
            if fqdn.endswith("."):
                fqdn = fqdn[:-1]
            
            # Ensure it ends with our TLD
            if not fqdn.lower().endswith(tld_with_dot) and not fqdn.lower().endswith(tld_lower):
                continue
            
            # Extract SLD: the label immediately before the TLD
            # Example: "www.example.zip" -> "example"
            # Example: "example.zip" -> "example"
            domain_parts = fqdn.lower().split(".")
            
            # Find TLD position
            if domain_parts[-1] == tld_lower:
                # Take the label before TLD as SLD
                if len(domain_parts) >= 2:
                    sld = domain_parts[-2]
                    # Filter out empty strings and add to set
                    if sld:
                        slds.add(sld)
    
    return slds


def build_domain_name(sld: str, tld: str) -> str:
    """
    Build full domain name from SLD and TLD.
    
    Args:
        sld: Second-level domain (e.g., "example")
        tld: Top-level domain (e.g., "zip")
        
    Returns:
        Full domain name (e.g., "example.zip")
    """
    return f"{sld}.{tld.lower()}"









