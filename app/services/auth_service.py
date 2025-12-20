"""
Authentication service for user management.
Handles password hashing, JWT tokens, and user authentication.
"""
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets
import jwt

from sqlalchemy.orm import Session

from app.models.user import User
from app.core.config import get_settings


# Simple password hashing using hashlib (no extra dependencies)
def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256 with salt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string (salt:hash format)
    """
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{password_hash}"


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password to verify
        hashed: Stored hash (salt:hash format)
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        salt, stored_hash = hashed.split(":")
        password_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return password_hash == stored_hash
    except (ValueError, AttributeError):
        return False


# JWT Configuration
SECRET_KEY = "expireddomain-secret-key-change-in-production-2025"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Get a user by email address.
    
    Args:
        db: Database session
        email: User's email address
        
    Returns:
        User instance or None
    """
    return db.query(User).filter(User.email == email.lower()).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Get a user by username.
    
    Args:
        db: Database session
        username: User's username
        
    Returns:
        User instance or None
    """
    return db.query(User).filter(User.username == username.lower()).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Get a user by ID.
    
    Args:
        db: Database session
        user_id: User's ID
        
    Returns:
        User instance or None
    """
    return db.query(User).filter(User.id == user_id).first()


def create_user(
    db: Session,
    email: str,
    username: str,
    password: str,
    full_name: Optional[str] = None
) -> User:
    """
    Create a new user account.
    
    Args:
        db: Database session
        email: User's email address
        username: User's username
        password: Plain text password
        full_name: Optional full name
        
    Returns:
        Created User instance
        
    Raises:
        ValueError: If email or username already exists
    """
    # Check if email exists
    if get_user_by_email(db, email):
        raise ValueError("Bu email adresi zaten kayıtlı")
    
    # Check if username exists
    if get_user_by_username(db, username):
        raise ValueError("Bu kullanıcı adı zaten alınmış")
    
    # Create user
    user = User(
        email=email.lower(),
        username=username.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        is_active=True,
        is_verified=False,
        is_premium=False,
        is_admin=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def authenticate_user(db: Session, email_or_username: str, password: str) -> Optional[User]:
    """
    Authenticate a user with email/username and password.
    
    Args:
        db: Database session
        email_or_username: User's email or username
        password: Plain text password
        
    Returns:
        User instance if authenticated, None otherwise
    """
    # Try to find user by email first
    user = get_user_by_email(db, email_or_username)
    
    # If not found, try username
    if not user:
        user = get_user_by_username(db, email_or_username)
    
    # Verify password
    if not user or not verify_password(password, user.password_hash):
        return None
    
    # Check if user is active
    if not user.is_active:
        return None
    
    # Update last login time
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    return user


def update_user_password(db: Session, user: User, new_password: str) -> bool:
    """
    Update a user's password.
    
    Args:
        db: Database session
        user: User instance
        new_password: New plain text password
        
    Returns:
        True if successful
    """
    user.password_hash = hash_password(new_password)
    db.commit()
    return True


def generate_password_reset_token(user: User) -> str:
    """
    Generate a password reset token.
    
    Args:
        user: User instance
        
    Returns:
        Password reset token
    """
    return create_access_token(
        data={"sub": user.email, "type": "password_reset"},
        expires_delta=timedelta(hours=1)
    )


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token and return the email.
    
    Args:
        token: Password reset token
        
    Returns:
        User's email if valid, None otherwise
    """
    payload = decode_access_token(token)
    
    if not payload:
        return None
    
    if payload.get("type") != "password_reset":
        return None
    
    return payload.get("sub")






