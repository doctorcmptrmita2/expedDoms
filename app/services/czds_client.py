"""
CZDS API client for downloading zone files.
Implements ICANN CZDS REST API v1.0.9 specification.
Supports both API-based downloads and local file mode.
"""
import gzip
import json
import time
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict
import requests
try:
    import jwt
except ImportError:
    # Fallback if PyJWT not installed
    jwt = None

from app.core.config import get_settings


class CZDSClient:
    """
    Client for ICANN CZDS REST API.
    
    Implements authentication, zone listing, and zone file downloading
    according to ICANN CZDS REST API v1.0.9 specification.
    """
    
    def __init__(
        self,
        auth_url: Optional[str] = None,
        base_url: Optional[str] = None,
        download_base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        data_dir: Optional[str] = None
    ):
        """
        Initialize CZDS client.
        
        Args:
            auth_url: CZDS authentication URL
            base_url: CZDS API base URL
            download_base_url: CZDS download API base URL
            username: CZDS username (email)
            password: CZDS password
            data_dir: Local directory for storing zone files
        """
        settings = get_settings()
        self.auth_url = auth_url or settings.CZDS_AUTH_URL
        self.base_url = base_url or settings.CZDS_BASE_URL
        self.download_base_url = download_base_url or settings.CZDS_DOWNLOAD_BASE_URL
        self.username = username or settings.CZDS_USERNAME
        self.password = password or settings.CZDS_PASSWORD
        self.data_dir = Path(data_dir or settings.DATA_DIR)
        
        # Token cache
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_user_agent(self) -> str:
        """Get User-Agent header as required by CZDS API."""
        return "ExpiredDomain.dev/1.0.0 (CZDS API Client)"
    
    def authenticate(self, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, any]:
        """
        Authenticate with CZDS API and obtain access token.
        
        Args:
            username: CZDS username (email). If not provided, uses instance username.
            password: CZDS password. If not provided, uses instance password.
            
        Returns:
            Dict with 'accessToken' and 'expiresAt' keys
            
        Raises:
            requests.RequestException: If authentication fails
            ValueError: If credentials are missing
        """
        username = username or self.username
        password = password or self.password
        
        if not username or not password:
            raise ValueError("CZDS username and password are required for authentication")
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self._get_user_agent()
        }
        
        payload = {
            "username": username,
            "password": password
        }
        
        try:
            response = requests.post(
                self.auth_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("accessToken")
                
                if not access_token:
                    raise ValueError("No access token in response")
                
                # Decode JWT to get expiration time
                try:
                    if jwt:
                        # Decode without verification to get claims
                        decoded = jwt.decode(access_token, options={"verify_signature": False})
                        exp_timestamp = decoded.get("exp", 0)
                        expires_at = datetime.fromtimestamp(exp_timestamp)
                    else:
                        # If PyJWT not available, assume 24 hours from now
                        expires_at = datetime.now().replace(microsecond=0) + timedelta(hours=24)
                except Exception:
                    # If decoding fails, assume 24 hours from now
                    expires_at = datetime.now().replace(microsecond=0) + timedelta(hours=24)
                
                self._access_token = access_token
                self._token_expires_at = expires_at
                
                return {
                    "accessToken": access_token,
                    "expiresAt": expires_at.isoformat(),
                    "expiresIn": int((expires_at - datetime.now()).total_seconds())
                }
            elif response.status_code == 401:
                raise ValueError("Invalid CZDS credentials")
            elif response.status_code == 429:
                raise ValueError("Rate limit exceeded. Please wait before retrying.")
            else:
                response.raise_for_status()
                
        except requests.RequestException as e:
            raise requests.RequestException(f"Authentication failed: {e}")
    
    def _ensure_valid_token(self) -> str:
        """
        Ensure we have a valid access token, refreshing if necessary.
        
        Returns:
            Valid access token
        """
        # Check if token exists and is still valid (with 5 minute buffer)
        if self._access_token and self._token_expires_at:
            buffer_time = datetime.now() + timedelta(minutes=5)
            if self._token_expires_at > buffer_time:
                return self._access_token
        
        # Token expired or doesn't exist, authenticate
        if not self.username or not self.password:
            raise ValueError("CZDS credentials not configured. Please authenticate first.")
        
        self.authenticate()
        return self._access_token
    
    def list_zones(self) -> List[str]:
        """
        List all authorized zone file download links.
        
        Returns:
            List of zone file download URLs
            
        Raises:
            requests.RequestException: If API call fails
        """
        token = self._ensure_valid_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": self._get_user_agent()
        }
        
        url = f"{self.base_url}/czds/downloads/links"
        
        try:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            zones = response.json()
            if not isinstance(zones, list):
                raise ValueError("Invalid response format from CZDS API")
            
            return zones
            
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to list zones: {e}")
    
    def get_zone_info(self, zone_url: str) -> Dict[str, any]:
        """
        Get zone file information (size, last modified, etc.) without downloading.
        
        Args:
            zone_url: Zone file download URL
            
        Returns:
            Dict with zone file information
        """
        token = self._ensure_valid_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": self._get_user_agent()
        }
        
        try:
            response = requests.head(zone_url, headers=headers, timeout=60)
            response.raise_for_status()
            
            info = {
                "url": zone_url,
                "size": int(response.headers.get("Content-Length", 0)),
                "lastModified": response.headers.get("Last-Modified"),
                "contentType": response.headers.get("Content-Type"),
                "filename": None
            }
            
            # Extract filename from Content-Disposition header
            content_disposition = response.headers.get("Content-Disposition", "")
            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[1].strip('"')
                info["filename"] = filename
            
            return info
            
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to get zone info: {e}")
    
    def download_zone(self, zone_url: str, target_path: Optional[Path] = None, tld: Optional[str] = None, target_date: Optional[date] = None) -> Path:
        """
        Download a zone file from CZDS API.
        
        Args:
            zone_url: Zone file download URL (from list_zones())
            target_path: Optional target file path. If not provided, auto-generates.
            tld: Optional TLD name for auto-generating path
            target_date: Optional date for auto-generating path
            
        Returns:
            Path to downloaded zone file
            
        Raises:
            requests.RequestException: If download fails
        """
        token = self._ensure_valid_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": self._get_user_agent()
        }
        
        # Auto-generate target path if not provided
        if target_path is None:
            if tld and target_date:
                tld_dir = self.data_dir / "zones" / tld.lower()
                tld_dir.mkdir(parents=True, exist_ok=True)
                date_str = target_date.strftime("%Y%m%d")
                target_path = tld_dir / f"{date_str}.zone"
            else:
                # Extract TLD from URL
                zone_name = zone_url.split("/")[-1].replace(".zone", "")
                tld_dir = self.data_dir / "zones" / zone_name
                tld_dir.mkdir(parents=True, exist_ok=True)
                date_str = datetime.now().strftime("%Y%m%d")
                target_path = tld_dir / f"{date_str}.zone"
        
        # Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Retry configuration
        max_retries = 3
        timeout_seconds = 1800  # 30 minutes for large files
        retry_delay = 5  # seconds between retries
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Use streaming for large files
                response = requests.get(
                    zone_url, 
                    headers=headers, 
                    stream=True, 
                    timeout=(30, timeout_seconds)  # (connect timeout, read timeout)
                )
                response.raise_for_status()
                
                # Download in chunks and write to temp file first
                temp_path = target_path.with_suffix('.tmp')
                total_size = 0
                
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                        if chunk:
                            f.write(chunk)
                            total_size += len(chunk)
                
                # Try to decompress if it's gzip
                try:
                    with open(temp_path, "rb") as f:
                        compressed_content = f.read()
                    decompressed = gzip.decompress(compressed_content)
                    with open(target_path, "wb") as f:
                        f.write(decompressed)
                    temp_path.unlink()  # Remove temp file
                except Exception:
                    # If not gzip or decompression fails, rename temp to target
                    if temp_path.exists():
                        if target_path.exists():
                            target_path.unlink()
                        temp_path.rename(target_path)
                
                return target_path
                
            except (requests.exceptions.ConnectionError, 
                    requests.exceptions.Timeout,
                    requests.exceptions.ChunkedEncodingError,
                    ConnectionResetError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    # Get fresh token for retry
                    token = self._ensure_valid_token()
                    headers["Authorization"] = f"Bearer {token}"
                    continue
                    
            except requests.RequestException as e:
                last_error = e
                break
                
            except Exception as e:
                last_error = e
                break
        
        # All retries failed
        raise requests.RequestException(f"Failed to download zone file after {max_retries} attempts: {last_error}")
    
    def download_zone_by_tld(self, tld: str, target_date: date) -> Path:
        """
        Download zone file for a specific TLD and date.
        First lists available zones, then downloads matching zone.
        
        Args:
            tld: Top-level domain (e.g., "zip")
            target_date: Date for which to download the zone file
            
        Returns:
            Path to downloaded zone file
        """
        # List available zones
        zones = self.list_zones()
        
        # Find matching zone URL
        zone_name = tld.lower()
        matching_zones = [z for z in zones if f"/{zone_name}.zone" in z.lower()]
        
        if not matching_zones:
            raise ValueError(f"No authorized zone file found for TLD: {tld}")
        
        # Use first matching zone
        zone_url = matching_zones[0]
        
        return self.download_zone(zone_url, tld=tld, target_date=target_date)
    
    def get_token_info(self) -> Optional[Dict[str, any]]:
        """
        Get information about current access token.
        
        Returns:
            Dict with token information or None if no token
        """
        if not self._access_token:
            return None
        
        try:
            if jwt and self._access_token:
                decoded = jwt.decode(self._access_token, options={"verify_signature": False})
                return {
                    "token": self._access_token[:50] + "...",
                    "expiresAt": self._token_expires_at.isoformat() if self._token_expires_at else None,
                    "isValid": self._token_expires_at > datetime.now() if self._token_expires_at else False,
                    "claims": decoded
                }
            else:
                return {
                    "token": self._access_token[:50] + "..." if self._access_token else None,
                    "expiresAt": self._token_expires_at.isoformat() if self._token_expires_at else None,
                    "isValid": self._token_expires_at > datetime.now() if self._token_expires_at else False
                }
        except Exception:
            return {
                "token": self._access_token[:50] + "..." if self._access_token else None,
                "expiresAt": self._token_expires_at.isoformat() if self._token_expires_at else None,
                "isValid": False
            }
