from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, Dict, Annotated
from datetime import datetime

# Authentication schemas
class LoginRequest(BaseModel):
    """Request schema for sending magic link."""
    email: EmailStr = Field(
        ..., 
        description="User's email address for magic link delivery",
        json_schema_extra={"examples": ["user@example.com"]}
    )

class Token(BaseModel):
    """JWT token response schema."""
    access_token: str = Field(..., description="JWT access token for authenticated requests")
    token_type: str = Field("bearer", description="Token type, fixed as 'bearer'")

class TokenVerifyRequest(BaseModel):
    """Request schema for verifying magic link token."""
    token: str = Field(
        ..., 
        min_length=1,
        description="Magic link token received via email",
        json_schema_extra={"examples": ["v1_magic_link_token_abc123"]}
    )

class UserResponse(BaseModel):
    """User response schema."""
    id: int = Field(..., description="Unique internal user ID")
    email: str = Field(..., description="User's verified email address")
    role: str = Field("user", description="User's role (user or admin)")
    created_at: datetime = Field(..., description="Timestamp of user account creation")
    last_login: Optional[datetime] = Field(None, description="Timestamp of the most recent successful login")

    model_config = ConfigDict(from_attributes=True)

# Survey schemas
class SurveyCreate(BaseModel):
    """Schema for creating a new survey (authenticated users only)."""
    answers: Dict[int, Annotated[int, Field(
        ge=1, 
        le=5, 
        description="Map of question ID (1-80) to score (1-5)",
    )]] = Field(
        ..., 
        description="Dictionary of 1-indexed assessment questions and their user-selected scores",
        json_schema_extra={"examples": [{1: 5, 2: 4, 3: 1, 4: 2}]}
    )
    notes: Optional[str] = Field(None, description="Optional personal notes or reflections about the assessment")
    scores: Optional[Dict[str, float]] = Field(
        None, 
        description="Optional pre-calculated scores (Prioritizes backend calculation if omitted)"
    )

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
    id: int = Field(..., description="Unique survey ID")
    user_id: Optional[int] = Field(None, description="Internal user ID associated with the survey")
    neon_user_id: str = Field(..., description="User's email identifier")
    answers: Dict[int, int] = Field(..., description="The raw 1-indexed answers provided by the user")
    scores: Dict[str, float] = Field(..., description="Calculated totals for each spiritual gift category")
    created_at: datetime = Field(..., description="Timestamp when the survey was submitted")

    model_config = ConfigDict(from_attributes=True)
