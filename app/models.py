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
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # New denomination relationship (Model C support)
    denomination_id = Column(UUID(as_uuid=True), ForeignKey("denominations.id"), nullable=True, index=True)
    denomination = relationship("Denomination", back_populates="organizations")

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
    
    # User preferences
    global_preferences = Column(JSON, default={}, nullable=True)  # Synced across orgs
    org_preferences = Column(JSON, default={}, nullable=True)     # Per-org overrides
    
    # Multi-tenancy
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    membership_status = Column(String(50), default="active", nullable=False)  # pending, active
    
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
    discernment = Column(JSON, nullable=True)
    assessment_version = Column(String(20), default="1.0", nullable=False)
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
class AuditLog(Base):
    """Minimal audit log for tracking actions.
    Stores who performed an action, on which organization, the action type,
    the target resource, and a timestamp.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(255), nullable=False)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    actor = relationship("User", backref="audit_logs")
    organization = relationship("Organization", backref="audit_logs")

# New models for multi‑denominational support

class Denomination(Base):
    """Denomination model representing a theological tradition or configuration bundle."""
    __tablename__ = "denominations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    logo_url = Column(String(255), nullable=True)
    default_currency = Column(String(10), nullable=True)
    scripture_set_id = Column(UUID(as_uuid=True), ForeignKey("scripture_sets.id"), nullable=True)
    
    # Governance (ADR-022)
    active_gift_keys = Column(JSON, default=[], nullable=True)      # List of enabled gift keys
    pastoral_overlays = Column(JSON, default={}, nullable=True)     # Map of gift_key -> { note, warning, etc }

    # Relationships
    scripture_set = relationship("ScriptureSet", back_populates="denominations")
    organizations = relationship("Organization", back_populates="denomination")

class ScriptureSet(Base):
    """Set of scripture references used for a particular denomination/profile."""
    __tablename__ = "scripture_sets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    verses = Column(JSON, default={}, nullable=True)  # e.g., {"grace": "Eph 2:8", ...}

    # Relationships
    denominations = relationship("Denomination", back_populates="scripture_set")
