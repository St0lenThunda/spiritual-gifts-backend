from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class User(Base):
    """User model for authenticated users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationship to surveys
    surveys = relationship("Survey", back_populates="user")

class Survey(Base):
    """Survey model for storing assessment results."""
    __tablename__ = "surveys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable for legacy data
    neon_user_id = Column(String, index=True)  # Keep for backward compatibility
    answers = Column(JSON)
    scores = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to user
    user = relationship("User", back_populates="surveys")

class LogEntry(Base):
    """Model for storing application logs and errors in the database."""
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String, index=True)
    event = Column(String, index=True)
    
    # Contextual info
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_email = Column(String, index=True, nullable=True)
    path = Column(String, index=True)
    method = Column(String)
    status_code = Column(Integer, nullable=True)
    request_id = Column(String, index=True, nullable=True)
    
    # Detailed data
    context = Column(JSON, nullable=True)
    exception = Column(String, nullable=True)
    
    # Relationship to user
    user = relationship("User")
