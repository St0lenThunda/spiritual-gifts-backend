from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, Dict, Annotated
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

    model_config = ConfigDict(from_attributes=True)

# Survey schemas
class SurveyCreate(BaseModel):
    """Schema for creating a new survey (authenticated users only)."""
    answers: Dict[int, Annotated[int, Field(ge=1, le=5)]]
    notes: Optional[str] = None
    scores: Optional[Dict[str, float]] = None

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, v: Dict[int, int]) -> Dict[int, int]:
        if not v:
            raise ValueError("Answers cannot be empty")
        for key, value in v.items():
            if not (1 <= value <= 5):
                raise ValueError(f"Score for question {key} must be between 1 and 5")
        return v

class SurveyResponse(BaseModel):
    """Schema for survey responses."""
    id: int
    user_id: Optional[int] = None
    neon_user_id: str
    answers: Dict[int, int]
    scores: Dict[str, float]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
