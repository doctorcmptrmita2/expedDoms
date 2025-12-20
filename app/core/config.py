"""
Application configuration using Pydantic Settings.
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    APP_NAME: str = "ExpiredDomain.dev"
    ENV: str = "local"
    
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:@localhost:3306/expireddomain"
    
    # CZDS API (optional - can work with local files)
    CZDS_USERNAME: str | None = None
    CZDS_PASSWORD: str | None = None
    CZDS_AUTH_URL: str = "https://account-api.icann.org/api/authenticate"
    CZDS_BASE_URL: str = "https://czds-api.icann.org"
    CZDS_DOWNLOAD_BASE_URL: str = "https://czds-download-api.icann.org"
    
    # Tracked TLDs (comma-separated)
    TRACKED_TLDS: str = "zip,works,dev,app,style,org,pro,trade,travel"
    
    # Data directory for zone files
    DATA_DIR: str = "./data"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def tracked_tlds_list(self) -> List[str]:
        """Parse TRACKED_TLDS into a list."""
        return [tld.strip().lower() for tld in self.TRACKED_TLDS.split(",") if tld.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

