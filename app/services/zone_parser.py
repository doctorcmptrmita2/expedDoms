"""
Zone file parser for extracting second-level domains.
Enhanced with chunk-based processing for large files.
"""
from pathlib import Path
from typing import Set, Generator, Optional
import time


def extract_slds_from_zone_chunked(
    zone_path: Path, 
    tld: str, 
    chunk_size: int = 10000,
    pause_every: int = 50000,
    pause_seconds: float = 0.1
) -> Generator[Set[str], None, None]:
    """
    Parse a zone file in chunks and yield SLD sets.
    This is memory-efficient for large zone files.
    
    Args:
        zone_path: Path to the zone file
        tld: Top-level domain (e.g., "zip")
        chunk_size: Number of lines to process before yielding
        pause_every: Pause every N lines to prevent blocking
        pause_seconds: Seconds to pause
        
    Yields:
        Set of SLD strings for each chunk
        
    Raises:
        FileNotFoundError: If zone file doesn't exist
    """
    if not zone_path.exists():
        raise FileNotFoundError(f"Zone file not found: {zone_path}")
    
    slds: Set[str] = set()
    tld_lower = tld.lower()
    tld_with_dot = f".{tld_lower}"
    line_count = 0
    
    with open(zone_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line_count += 1
            
            # Pause periodically to prevent blocking
            if line_count % pause_every == 0:
                time.sleep(pause_seconds)
            
            # Skip empty lines and comments
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            
            # Parse zone file record
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
            
            # Extract SLD
            domain_parts = fqdn.lower().split(".")
            
            if domain_parts[-1] == tld_lower:
                if len(domain_parts) >= 2:
                    sld = domain_parts[-2]
                    if sld:
                        slds.add(sld)
            
            # Yield chunk when size reached
            if len(slds) >= chunk_size:
                yield slds
                slds = set()
    
    # Yield remaining SLDs
    if slds:
        yield slds


def extract_slds_from_zone(zone_path: Path, tld: str) -> Set[str]:
    """
    Parse a zone file and extract unique second-level domains (SLDs).
    For large files, consider using extract_slds_from_zone_chunked instead.
    
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










