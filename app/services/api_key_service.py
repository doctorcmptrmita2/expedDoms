"""
API Key service for managing and authenticating API keys.
"""
import secrets
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.subscription import ApiKey
from app.models.user import User
from app.services.subscription_service import SubscriptionService, get_subscription_service

logger = logging.getLogger(__name__)


class ApiKeyService:
    """Service for managing API keys."""
    
    def __init__(self, db: Session):
        self.db = db
    
    @staticmethod
    def generate_key() -> str:
        """Generate a secure API key."""
        return f"ed_{secrets.token_urlsafe(32)}"
    
    def create_api_key(
        self,
        user: User,
        name: str
    ) -> ApiKey:
        """
        Create a new API key for user.
        
        Args:
            user: User to create key for
            name: Key name/identifier
            
        Returns:
            Created ApiKey instance (with _plain_key attribute for one-time display)
        """
        # Check if user has API access (Pro+ plans)
        subscription_service = get_subscription_service(self.db)
        plan = subscription_service.get_user_plan(user)
        
        if not subscription_service.can_access_feature(user, "api_access"):
            raise ValueError("API access requires Pro or Business plan")
        
        # Generate key
        key = self.generate_key()
        
        # Hash the key for storage (using simple hash for now)
        import hashlib
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        # Create API key record
        api_key = ApiKey(
            user_id=user.id,
            key_hash=key_hash,
            name=name,
            is_active=True
        )
        
        # Store plain key temporarily (will be returned to user, then discarded)
        api_key._plain_key = key  # Temporary storage
        
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        
        logger.info(f"API key created for user {user.id}: {name}")
        
        return api_key
    
    def get_api_key(self, key: str) -> Optional[ApiKey]:
        """
        Get API key by key string.
        
        Args:
            key: API key string
            
        Returns:
            ApiKey instance or None
        """
        # Hash the provided key
        import hashlib
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        return self.db.query(ApiKey).filter(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active == True
        ).first()
    
    def get_user_api_keys(self, user: User) -> list[ApiKey]:
        """
        Get all API keys for a user.
        
        Args:
            user: User to get keys for
            
        Returns:
            List of ApiKey instances
        """
        return self.db.query(ApiKey).filter(
            ApiKey.user_id == user.id
        ).order_by(ApiKey.created_at.desc()).all()
    
    def revoke_api_key(self, user: User, key_id: int) -> bool:
        """
        Revoke (deactivate) an API key.
        
        Args:
            user: User who owns the key
            key_id: API key ID
            
        Returns:
            True if revoked successfully
        """
        api_key = self.db.query(ApiKey).filter(
            ApiKey.id == key_id,
            ApiKey.user_id == user.id
        ).first()
        
        if not api_key:
            return False
        
        api_key.is_active = False
        self.db.commit()
        
        logger.info(f"API key {key_id} revoked for user {user.id}")
        
        return True
    
    def authenticate(self, key: str) -> Optional[User]:
        """
        Authenticate using API key.
        
        Args:
            key: API key string
            
        Returns:
            User instance if valid, None otherwise
        """
        api_key = self.get_api_key(key)
        
        if not api_key:
            return None
        
        # Check if user is active
        user = api_key.user
        if not user or not user.is_active:
            return None
        
        # Update last used timestamp
        api_key.last_used_at = datetime.utcnow()
        api_key.requests_count += 1
        api_key.requests_count_monthly += 1
        self.db.commit()
        
        return user


