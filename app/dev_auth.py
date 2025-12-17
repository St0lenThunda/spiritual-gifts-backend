"""
Development authentication utilities for testing without Neon Auth email service.
This provides a simple email/password authentication for development purposes.
"""
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from .models import User
from .neon_auth import create_access_token

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)

async def dev_login(email: str, password: str, db: Session) -> dict:
    """
    Development login - authenticate with email/password.
    
    Args:
        email: User's email
        password: User's password
        db: Database session
        
    Returns:
        JWT access token
    """
    # For development, accept any password for now
    # In production, you'd verify against stored password hash
    
    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Create new user
        user = User(email=email, created_at=datetime.utcnow())
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create JWT token (sub must be string for jose library)
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}
