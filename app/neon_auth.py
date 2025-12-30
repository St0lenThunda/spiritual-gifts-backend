"""
Authentication utilities using Neon Auth for magic links and JWT for session management.
"""
import httpx
import structlog
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from .config import settings
from .database import get_db
from .models import User, Organization
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

class UserContext(BaseModel):
    """Rich context object for authenticated requests."""
    user: User
    organization: Optional[Organization]
    role: str
    permissions: List[str] = []
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

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

async def get_user_context(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> UserContext:
    """
    Get the full context for the current authenticated user requests.
    Resolves User, Organization, and effective Role.
    """
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")
        
    if not token:
        logger.warning("unauthorized_access", reason="missing_token", path=request.url.path, cookies=list(request.cookies.keys()))
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
    
    # Eagerly load organization
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

    # Resolve Organization
    org = user.organization  # Relies on SQLAlchemy relationship
    
    # Enforce Read-Only for Demo Org
    if org and org.is_demo:
        if request.method not in ["GET", "HEAD", "OPTIONS"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This is a demo organization. Write actions are disabled."
            )
    
    # Determine effective role (expand Logic here later)
    role = user.role

    return UserContext(
        user=user,
        organization=org,
        role=role,
        permissions=[] 
    )

async def get_current_user(
    context: UserContext = Depends(get_user_context)
) -> User:
    """
    Legacy dependency wrapper: Returns the User object from the context.
    Use this for backward compatibility with existing routes.
    """
    return context.user

async def require_org(context: UserContext = Depends(get_user_context)) -> Organization:
    """
    Dependency that enforces the user belongs to an active Organization.
    Returns the Organization object.
    """
    if not context.organization:
        logger.warning("access_denied", reason="no_organization", user_id=context.user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization membership required"
        )
    
    if not context.organization.is_active:
        logger.warning("access_denied", reason="org_inactive", org_id=str(context.organization.id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive"
        )
    
    if context.user.membership_status != "active":
        logger.warning("access_denied", reason="membership_pending", user_id=context.user.id, org_id=str(context.organization.id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization membership is pending approval"
        )
        
    return context.organization

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
    allowed_emails = ["tonym415@gmail.com"]
    allowed_org_slugs = ["neon-evangelion"]
    
    # Check 1: Must be an admin role
    if current_user.role != "admin":
        logger.warning("unauthorized_admin_access", user_id=current_user.id, user_email=current_user.email, reason="role_not_admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
        
    # Check 2: Must be a Super Admin (specific email or specific org)
    is_super_admin = current_user.email in allowed_emails
    if not is_super_admin and current_user.organization:
         if current_user.organization.slug in allowed_org_slugs:
             is_super_admin = True
             
    if not is_super_admin:
        logger.warning("unauthorized_super_admin_access", user_id=current_user.id, user_email=current_user.email, org_id=current_user.org_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System Administrator privileges required"
        )
        
    return current_user

async def get_org_admin(
    context: UserContext = Depends(get_user_context)
) -> User:
    """
    Dependency that verifies if the current user is an organization admin.
    This allows org admins to access admin features scoped to their organization.
    
    Returns:
        User object if the user is an org admin or super admin
        
    Raises:
        HTTPException: If the user is not an admin
    """
    user = context.user
    
    # Super admins always have access
    allowed_emails = ["tonym415@gmail.com"]
    allowed_org_slugs = ["neon-evangelion"]
    
    is_super_admin = user.email in allowed_emails
    if not is_super_admin and user.organization:
        if user.organization.slug in allowed_org_slugs:
            is_super_admin = True
    
    if is_super_admin:
        return user
    
    # Check if user is an org admin
    if user.role != "admin":
        logger.warning("unauthorized_admin_access", user_id=user.id, user_email=user.email, reason="role_not_admin")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    
    # Org admin must belong to an organization
    if not context.organization:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization membership required for admin access"
        )
    
    return user

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
