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
    
    # Email settings (for verification and password reset)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "noreply@expireddomain.dev"
    APP_URL: str = "http://localhost:8001"
    
    # Stripe settings (for payments)
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "expireddomain-secret-key-change-in-production-2025"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
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

