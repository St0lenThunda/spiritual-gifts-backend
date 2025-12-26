from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from .database import Base
from datetime import datetime
import uuid


class Organization(Base):
    """Organization model for multi-tenancy."""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan = Column(String(50), default="free", nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)
    branding = Column(JSON, default={}, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="organization")
    surveys = relationship("Survey", back_populates="organization")


class User(Base):
    """User model for authenticated users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, default="user", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Multi-tenancy
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    surveys = relationship("Survey", back_populates="user")


class Survey(Base):
    """Survey model for storing assessment results."""
    __tablename__ = "surveys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    neon_user_id = Column(String, index=True)  # Keep for backward compatibility
    answers = Column(JSON)
    scores = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Multi-tenancy
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="surveys")
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
    
    # Multi-tenancy
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    
    # Detailed data
    context = Column(JSON, nullable=True)
    exception = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User")
    organization = relationship("Organization")
