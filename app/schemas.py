from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
from datetime import datetime

# Authentication schemas
class LoginRequest(BaseModel):
    """Request schema for sending magic link."""
    email: EmailStr

class Token(BaseModel):
    """JWT token response schema."""
    access_token: str
    token_type: str = "bearer"

class TokenVerifyRequest(BaseModel):
    """Request schema for verifying magic link token."""
    token: str

class UserResponse(BaseModel):
    """User response schema."""
    id: int
    email: str
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

# Survey schemas
class SurveyCreate(BaseModel):
    """Schema for creating a new survey (authenticated users only)."""
    answers: Dict[int, int]
    notes: Optional[str] = None
    scores: Optional[Dict[str, float]] = None

class SurveyResponse(BaseModel):
    """Schema for survey responses."""
    id: int
    user_id: Optional[int] = None
    neon_user_id: str
    answers: Dict[int, int]
    scores: Dict[str, float]
    created_at: datetime

    class Config:
        from_attributes = True
