from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, Annotated, Union
from uuid import UUID
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
    org_id: Optional[UUID] = Field(None, description="Organization ID affiliation")
    membership_status: str = Field("active", description="Status within the organization (pending or active)")
    global_preferences: Dict[str, Any] = Field(default_factory=dict, description="User's global preferences")
    created_at: datetime = Field(..., description="Timestamp of user account creation")
    last_login: Optional[datetime] = Field(None, description="Timestamp of the most recent successful login")

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    """Schema for updating a user (admins only)."""
    role: Optional[str] = Field(None, description="User's role (user or admin)")
    org_id: Optional[UUID] = Field(None, description="Organization ID affiliation")
    membership_status: Optional[str] = Field(None, description="Status within the organization (pending or active)")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["user", "admin"]:
            raise ValueError("Role must be 'user' or 'admin'")
        return v

    @field_validator("membership_status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["pending", "active"]:
            raise ValueError("Status must be 'pending' or 'active'")
        return v

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
        json_schema_extra={"examples": [{"1": 5, "2": 4, "3": 1, "4": 2}]}
    )
    notes: Optional[str] = Field(None, description="Optional personal notes or reflections about the assessment")
    scores: Optional[Dict[str, float]] = Field(
        None, 
        description="Optional pre-calculated scores (Prioritizes backend calculation if omitted)"
    )
    assessment_version: str = Field("1.0", description="Version of the assessment questions used")

    @field_validator("answers", mode="before")
    @classmethod
    def validate_answers(cls, v):
        if not v:
            raise ValueError("Answers cannot be empty")
        
        # Handle both dict and already-validated input
        if not isinstance(v, dict):
            raise ValueError("Answers must be a dictionary")
        
        # Convert string keys to integers and validate
        converted = {}
        for key, value in v.items():
            try:
                int_key = int(key)
            except (ValueError, TypeError):
                raise ValueError(f"Question key '{key}' must be a valid integer")
            
            # Ensure value is an integer
            try:
                int_value = int(value)
            except (ValueError, TypeError):
                raise ValueError(f"Answer value for question {int_key} must be an integer")
            
            if not (1 <= int_value <= 5):
                raise ValueError(f"Score for question {int_key} must be between 1 and 5")
            
            converted[int_key] = int_value
        
        return converted

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
    denomination_id: Optional[UUID] = Field(None, description="Denomination configuration ID for the organization")


class OrganizationThemeCreate(BaseModel):
    """Schema for creating a new organization theme."""
    name: str = Field(..., description="Name of the theme")
    config: Dict[str, Any] = Field(..., description="JSON configuration for the theme")

class OrganizationThemeUpdate(BaseModel):
    """Schema for updating an organization theme."""
    name: Optional[str] = Field(None, description="Name of the theme")
    config: Optional[Dict[str, Any]] = Field(None, description="JSON configuration for the theme")

# New schemas for multi‑denominational support
class ScriptureVerses(BaseModel):
    KJV: Optional[str] = None
    NIV: Optional[str] = None
    ESV: Optional[str] = None

class ScriptureObject(BaseModel):
    reference: str
    verses: Optional[ScriptureVerses] = None

class ScriptureSetBase(BaseModel):
    name: str = Field(..., description="Human readable name for the scripture set")
    verses: Dict[str, List[Union[ScriptureObject, str]]] = Field(
        default_factory=dict, 
        description="Mapping of gift -> scripture references. Can be simple strings or enriched objects."
    )

class ScriptureSetCreate(ScriptureSetBase):
    pass

class ScriptureSetResponse(ScriptureSetBase):
    id: UUID = Field(..., description="Unique ID for the scripture set")
    model_config = ConfigDict(from_attributes=True)

class DenominationBase(BaseModel):
    slug: str = Field(..., description="URL‑friendly identifier for the denomination")
    display_name: str = Field(..., description="Human readable name for the denomination")
    logo_url: Optional[str] = Field(None, description="Optional logo image URL")
    default_currency: Optional[str] = Field(None, description="Default currency code for pricing, if applicable")
    scripture_set_id: Optional[UUID] = Field(None, description="Reference to a ScriptureSet for this denomination")

class DenominationCreate(DenominationBase):
    pass

class DenominationResponse(DenominationBase):
    id: UUID = Field(..., description="Unique denomination ID")
    scripture_set: Optional[ScriptureSetResponse] = Field(None, description="Embedded scripture set details")
    model_config = ConfigDict(from_attributes=True)

class OrganizationThemeResponse(BaseModel):
    """Schema for organization theme responses."""
    id: UUID = Field(..., description="Unique theme ID")
    org_id: UUID = Field(..., description="Organization ID this theme belongs to")
    name: str = Field(..., description="Name of the theme")
    config: Dict[str, Any] = Field(..., description="JSON configuration for the theme")
    is_active: bool = Field(..., description="Whether this theme is currently active for the organization")
    created_at: datetime = Field(..., description="When the theme was created")
    updated_at: datetime = Field(..., description="When the theme was last modified")

    model_config = ConfigDict(from_attributes=True)


class OrganizationResponse(BaseModel):
    """Schema for organization responses."""
    id: UUID = Field(..., description="Unique organization ID")
    name: str = Field(..., description="Organization display name")
    slug: str = Field(..., description="URL-friendly identifier")
    plan: str = Field(..., description="Subscription plan (free, individual, ministry, church)")
    entitlements: Optional[Dict[str, Any]] = Field(None, description="Feature limits and entitlements for the current plan")
    branding: Optional[Dict[str, Any]] = Field({}, description="Visual branding configuration")
    theme_id: Optional[UUID] = Field(None, description="ID of the active theme for the organization")
    is_active: bool = Field(..., description="Whether the organization is active")
    is_demo: bool = Field(False, description="Whether this is a demo organization (read-only mode)")
    created_at: datetime = Field(..., description="When the organization was created")
    updated_at: datetime = Field(..., description="When the organization was last modified")
    # Denomination fields (Model C support)
    denomination_id: Optional[UUID] = Field(None, description="Denomination configuration ID for the organization")
    denomination: Optional[DenominationResponse] = Field(None, description="Denomination profile details (display_name, logo, etc.)")
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


class OrganizationMemberUpdate(BaseModel):
    """Schema for updating an existing organization member."""
    role: Optional[str] = Field(None, description="Role to assign (user or admin)")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["user", "admin"]:
            raise ValueError("Role must be 'user' or 'admin'")
        return v


class OrganizationBulkAction(BaseModel):
    """Schema for bulk actions on organization members."""
    user_ids: List[int] = Field(..., description="List of internal user IDs to perform action on")

# User Preference schemas
class PreferenceUpdate(BaseModel):
    """Schema for updating user preferences."""
    theme: Optional[str] = Field(None, description="Theme preference ID")
    theme_sync: Optional[bool] = Field(None, description="Whether to subscribe to organization theme updates")
    locale: Optional[str] = Field(None, description="Preferred language code (en, es, fr, ru)")
    sync_across_orgs: Optional[bool] = Field(None, description="Whether to sync preferences across organizations")
    notifications: Optional[Dict[str, bool]] = Field(None, description="Notification preferences")
    ui: Optional[Dict[str, Any]] = Field(None, description="UI preferences")


class UserPreferences(BaseModel):
    """Schema for user preferences response."""
    theme: Optional[str] = None
    theme_sync: bool = True
    locale: str = "en"
    sync_across_orgs: bool = True
    notifications: Dict[str, bool] = {"email": True, "toast": True}
    ui: Dict[str, Any] = {}


class ThemeAnalytics(BaseModel):
    """Schema for theme analytics response."""
    total_users: int
    theme_distribution: List[Dict[str, Any]]
    org_has_custom_theme: bool
