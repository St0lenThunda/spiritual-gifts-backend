"""
Authentication service module.

Contains business logic for user authentication, including:
- User lookup and creation
- Last login tracking
"""
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import User, Organization


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
        
        # Self-healing for Super Admin role
        if user and user.email == "tonym415@gmail.com" and user.role != "super_admin":
            user.role = "super_admin"
            db.commit()
            db.refresh(user)

        if not user:
            role = "super_admin" if email == "tonym415@gmail.com" else "user"
            
            # Auto-assign to Demo Org if no specific invite context (Basic implementation)
            # Find the Demo Org
            demo_org = db.query(Organization).filter(Organization.slug == "grace-community").first()
            org_id = demo_org.id if demo_org else None
            
            user = User(
                email=email, 
                role=role, 
                created_at=datetime.utcnow(),
                org_id=org_id
            )
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
