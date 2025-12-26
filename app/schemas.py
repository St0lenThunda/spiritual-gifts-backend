from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, Dict, Annotated, Any
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
    assessment_version: str = Field("1.0", description="Version of the assessment questions used")

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
    discernment: Optional[Dict[str, Any]] = Field(None, description="Narrative indicators and context notes")
    assessment_version: str = Field(..., description="Version of the assessment questions used")
    created_at: datetime = Field(..., description="Timestamp when the survey was submitted")

    model_config = ConfigDict(from_attributes=True)


# Organization schemas (Multi-tenancy)
from uuid import UUID

class OrganizationCreate(BaseModel):
    """Schema for creating a new organization."""
    name: str = Field(..., min_length=2, max_length=255, description="Organization display name")
    slug: str = Field(
        ..., 
        min_length=3, 
        max_length=100, 
        pattern=r"^[a-z0-9-]+$",
        description="URL-friendly identifier (lowercase, numbers, hyphens)"
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("Slug cannot start or end with a hyphen")
        if "--" in v:
            raise ValueError("Slug cannot contain consecutive hyphens")
        reserved = ["www", "api", "app", "admin", "auth", "billing", "help", "support"]
        if v in reserved:
            raise ValueError(f"'{v}' is a reserved slug")
        return v.lower()


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    branding: Optional[Dict[str, Any]] = Field(None, description="Visual branding configuration")


class OrganizationResponse(BaseModel):
    """Schema for organization responses."""
    id: UUID = Field(..., description="Unique organization ID")
    name: str = Field(..., description="Organization display name")
    slug: str = Field(..., description="URL-friendly identifier")
    plan: str = Field(..., description="Subscription plan (free, individual, ministry, church)")
    branding: Optional[Dict[str, Any]] = Field({}, description="Visual branding configuration")
    is_active: bool = Field(..., description="Whether the organization is active")
    created_at: datetime = Field(..., description="When the organization was created")
    updated_at: datetime = Field(..., description="When the organization was last modified")

    model_config = ConfigDict(from_attributes=True)


class OrganizationMemberInvite(BaseModel):
    """Schema for inviting a member to an organization."""
    email: EmailStr = Field(..., description="Email address of the person to invite")
    role: str = Field("user", description="Role to assign (user or admin)")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ["user", "admin"]:
            raise ValueError("Role must be 'user' or 'admin'")
        return v
