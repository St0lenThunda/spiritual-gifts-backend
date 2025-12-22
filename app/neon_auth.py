"""
Authentication utilities using Neon Auth for magic links and JWT for session management.
"""
import httpx
import structlog
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .config import settings
from .database import get_db
from .models import User
from .logging_setup import user_id_ctx, user_email_ctx, logger

# Neon Auth configuration
NEON_AUTH_URL = "https://auth.neon.tech"
NEON_PROJECT_ID = settings.NEON_PROJECT_ID
NEON_API_KEY = settings.NEON_API_KEY

# JWT configuration
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_EXPIRATION_MINUTES

# HTTP Bearer token scheme (don't auto-error so we can check cookies)
security = HTTPBearer(auto_error=False)

class NeonUser(BaseModel):
    """Neon user model."""
    id: str
    email: str

# ============================================================================
# JWT Token Utilities
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional expiration time delta
        
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

def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        logger.warning("unauthorized_access", reason="invalid_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ============================================================================
# Authentication Dependencies
# ============================================================================

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token (header or cookie).
    
    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials from request header
        db: Database session
        
    Returns:
        User object for the authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")
        
    if not token:
        logger.warning("unauthorized_access", reason="missing_token", path=request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token)
    
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logger.warning("unauthorized_access", reason="user_not_found", user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Set context for logging
    structlog.contextvars.bind_contextvars(user_id=user.id, user_email=user.email)
    user_id_ctx.set(user.id)
    user_email_ctx.set(user.email)
    
    return user

async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency that verifies if the current user is an administrator.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User object if the user is an admin
        
    Raises:
        HTTPException: If the user is not an admin
    """
    if current_user.role != "admin":
        logger.warning("unauthorized_admin_access", user_id=current_user.id, user_email=current_user.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    return current_user

# ============================================================================
# Neon Auth Magic Link Functions
# ============================================================================

async def neon_signup(email: str):
    """
    Sign up a new user with Neon Auth.
    
    Args:
        email: User's email address
        
    Returns:
        Neon Auth response
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{NEON_AUTH_URL}/auth/v1/signup",
            json={"email": email},
            headers={"apikey": NEON_API_KEY},
        )
        r.raise_for_status()
        return r.json()

async def neon_send_magic_link(email: str):
    """
    Send a magic link to the user's email via Neon Auth.
    
    Args:
        email: User's email address
        
    Returns:
        Neon Auth response
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{NEON_AUTH_URL}/auth/v1/otp",
            json={"email": email, "create_user": True},
            headers={"apikey": NEON_API_KEY},
        )
        r.raise_for_status()
        return r.json()

async def neon_verify_magic_link(token: str):
    """
    Verify a magic link token with Neon Auth.
    
    Args:
        token: Magic link token from email
        
    Returns:
        Neon Auth response with user info
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{NEON_AUTH_URL}/auth/v1/token",
            data={"grant_type": "magiclink", "token": token},
            headers={"apikey": NEON_API_KEY, "Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        return r.json()
