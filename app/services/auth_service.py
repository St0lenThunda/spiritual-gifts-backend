"""
Authentication service module.

Contains business logic for user authentication, including:
- User lookup and creation
- Last login tracking
"""
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import User


class AuthService:
    """Service class for authentication-related business logic."""
    
    @staticmethod
    def get_or_create_user(db: Session, email: str) -> User:
        """
        Find an existing user by email or create a new one.
        
        Args:
            db: Database session
            email: User's email address
            
        Returns:
            User object (existing or newly created)
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, created_at=datetime.utcnow())
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    
    @staticmethod
    def update_last_login(db: Session, user: User) -> None:
        """
        Update the user's last login timestamp.
        
        Args:
            db: Database session
            user: User object to update
        """
        user.last_login = datetime.utcnow()
        db.commit()
