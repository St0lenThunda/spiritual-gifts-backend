"""
API routers for the Spiritual Gifts Assessment application.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, Request, Header
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from fastapi_cache.decorator import cache
from fastapi_cache.coder import JsonCoder
from fastapi_csrf_protect import CsrfProtect
import json
from typing import Any

from ..neon_auth import (
    neon_send_magic_link, 
    neon_verify_magic_link, 
    get_current_user, 
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..database import get_db
from ..models import Survey, User
from .. import schemas
from ..services import AuthService, SurveyService, load_questions, load_gifts, load_scriptures
from ..limiter import limiter
from ..config import settings
from ..logging_setup import logger

router = APIRouter()

class SafeJsonCoder(JsonCoder):
    @classmethod
    def decode(cls, value: Any) -> Any:
        if isinstance(value, str):
            return json.loads(value)
        return super().decode(value)

# ============================================================================
# Security Routes
# ============================================================================

@router.get("/csrf-token")
async def get_csrf_token(csrf_protect: CsrfProtect = Depends()):
    """
    Endpoint to provide a CSRF token for SPAs.
    """
    from fastapi.responses import JSONResponse
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = JSONResponse(content={"detail": "CSRF cookie set", "csrf_token": csrf_token})
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response

# ============================================================================
# Authentication Routes
# ============================================================================

@router.post("/auth/send-link")
@limiter.limit("30/10minutes")
async def send_magic_link(
    request: Request, 
    login_data: schemas.LoginRequest,
    csrf_protect: CsrfProtect = Depends()
):
    """
    Send a magic link to the user's email for passwordless authentication.
    
    Args:
        request: FastAPI request object (required by slowapi)
        login_data: LoginRequest with email
        
    Returns:
        Success message
    """
    await csrf_protect.validate_csrf(request)
    await neon_send_magic_link(login_data.email)
    logger.info("magic_link_sent", user_email=login_data.email)
    return {"message": "Magic link sent successfully", "email": login_data.email}

@router.post("/auth/debug-csrf")
async def debug_csrf(
    request: Request,
    csrf_protect: CsrfProtect = Depends()
):
    """
    Debug endpoint to inspect CSRF state and request context.
    Does not raise on validation failure but returns the state.
    """
    is_valid = True
    error = None
    try:
        await csrf_protect.validate_csrf(request)
    except Exception as e:
        is_valid = False
        error = str(e)
    
    headers = {k: v for k, v in request.headers.items() if k.lower() in ["x-csrf-token", "origin", "referer", "cookie"]}
    cookies = {k: "present" for k in request.cookies.keys()}
    
    return {
        "csrf_valid": is_valid,
        "csrf_error": error,
        "headers": headers,
        "cookies": cookies,
        "env": settings.ENV,
        "client_ip": request.client.host if request.client else "unknown"
    }

@router.post("/auth/verify", response_model=schemas.Token)
async def verify_magic_link(
    request: schemas.TokenVerifyRequest, 
    response: Response,
    fastapi_request: Request,
    db: Session = Depends(get_db),
    csrf_protect: CsrfProtect = Depends()
):
    """
    Verify the magic link token and return a JWT access token.
    
    Args:
        request: TokenVerifyRequest with magic link token
        response: FastAPI response object
        db: Database session
        
    Returns:
        JWT access token
    """
    await csrf_protect.validate_csrf(fastapi_request)
    # Verify the magic link with Neon Auth
    neon_response = await neon_verify_magic_link(request.token)
    
    # Extract user info from Neon response
    user_data = neon_response.get("user")
    if not user_data:
        # Fallback to top-level email if user object is missing
        user_email = neon_response.get("email")
    else:
        user_email = user_data.get("email")
    
    if not user_email:
        logger.error("magic_link_verification_failed", reason="missing_email_in_response", response=neon_response)
        raise HTTPException(status_code=400, detail="Invalid token response from Neon Auth: Email missing")
    
    # Find or create user in our database (via service layer)
    user = AuthService.get_or_create_user(db, user_email)
    
    # Update last login
    AuthService.update_last_login(db, user)
    
    # Create JWT token (sub must be string for jose library)
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": user.role})
    
    # Set HttpOnly cookie
    is_dev = settings.ENV == "development"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False if is_dev else (fastapi_request.url.scheme == "https"),
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    logger.info("magic_link_verified", user_id=user.id, user_email=user.email)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/dev-login", response_model=schemas.Token)
async def dev_login_endpoint(
    request: schemas.LoginRequest, 
    response: Response,
    fastapi_request: Request,
    db: Session = Depends(get_db)
):
    """
    Development login endpoint - bypasses magic link email for testing.
    Simply provide an email and you'll get a JWT token.
    
    IMPORTANT: This endpoint is strictly disabled in production!
    
    Args:
        request: LoginRequest with email
        response: FastAPI response object
        fastapi_request: Request object
        db: Database session
        
    Returns:
        JWT access token
    """
    # CSRF validation skipped for dev tool convenience
    # await csrf_protect.validate_csrf(fastapi_request)
    if settings.ENV == "production":
        raise HTTPException(
            status_code=403, 
            detail="Dev login is strictly prohibited in production environments."
        )
    
    from ..dev_auth import dev_login
    result = await dev_login(request.email, "dev-password", db)
    
    # Set HttpOnly cookie
    is_dev = settings.ENV == "development"
    response.set_cookie(
        key="access_token",
        value=result["access_token"],
        httponly=True,
        secure=False if is_dev else (fastapi_request.url.scheme == "https"),
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )
    
    logger.info("dev_login_successful", user_email=request.email)
    return result

@router.get("/auth/me", response_model=schemas.UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's information.
    
    Args:
        current_user: Current authenticated user from JWT token
        
    Returns:
        User information
    """
    logger.info("fetch_user_info", user_id=current_user.id, user_email=current_user.email, user_role=current_user.role)
    return current_user

@router.post("/auth/logout")
async def logout(
    request: Request, 
    response: Response,
    current_user: User = Depends(get_current_user),
    csrf_protect: CsrfProtect = Depends()
):
    """
    Logout the current user by clearing the access token cookie.
    
    Args:
        request: FastAPI request object
        response: FastAPI response object
        
    Returns:
        Success message
    """
    await csrf_protect.validate_csrf(request)
    is_dev = settings.ENV == "development"
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=False if is_dev else (request.url.scheme == "https"),
        samesite="lax",
    )
    logger.info("user_logged_out")
    return {"message": "Successfully logged out"}

# ============================================================================
# Survey Routes (Protected)
# ============================================================================

@router.post("/survey/submit", response_model=schemas.SurveyResponse)
async def submit_survey(
    survey_data: schemas.SurveyCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    csrf_protect: CsrfProtect = Depends()
):
    """
    Submit a new survey for the authenticated user.
    
    Args:
        survey_data: Survey data with answers and scores
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created survey object
    """
    await csrf_protect.validate_csrf(request)
    survey = SurveyService.create_survey(
        db=db,
        user=current_user,
        answers=survey_data.answers,
        scores=survey_data.scores,
        assessment_version=survey_data.assessment_version
    )
    logger.info("survey_submitted", survey_id=survey.id)
    return survey

@router.get("/user/surveys")
def list_user_surveys(
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List surveys for the authenticated user (paginated).
    
    Args:
        page: Page number (default: 1)
        limit: Items per page (default: 20)
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Paginated survey response
    """
    return SurveyService.get_user_surveys(db, current_user, page, limit)

# ============================================================================
# Public Routes
# ============================================================================

from ..services.content_service import ContentService

# ... imports ...

@router.get("/questions")
@cache(expire=3600, coder=SafeJsonCoder)
async def get_questions(
    accept_language: str = Header("en"),
    locale: str = None,
    org_slug: str = None,
    db: Session = Depends(get_db)
):
    """
    Get the assessment questions.
    """
    # Prefer query param for caching variance, fallback to header
    final_locale = locale or (accept_language[:2].lower() if accept_language else "en")
    return ContentService.get_questions_for_context(db, final_locale, org_slug)

@router.get("/gifts")
@cache(expire=3600, coder=SafeJsonCoder)
async def get_gifts(
    accept_language: str = Header("en"),
    locale: str = None,
    org_slug: str = None,
    db: Session = Depends(get_db)
):
    """
    Get information about spiritual gifts.
    """
    # Prefer query param for caching variance, fallback to header
    final_locale = locale or (accept_language[:2].lower() if accept_language else "en")
    return ContentService.get_gifts_for_context(db, final_locale, org_slug)

@router.get("/scriptures")
@cache(expire=3600, coder=SafeJsonCoder)
async def get_scriptures():
    """
    Get scripture references.
    
    Returns:
        Scriptures data
    """
    return load_scriptures()
