"""
API routers for the Spiritual Gifts Assessment application.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from .neon_auth import neon_send_magic_link, neon_verify_magic_link, get_current_user, create_access_token
from .database import get_db
from .models import Survey, User
from . import schemas
from .services.getJSONData import load_questions, load_gifts, load_scriptures

router = APIRouter()

# ============================================================================
# Authentication Routes
# ============================================================================

@router.post("/auth/send-link")
async def send_magic_link(request: schemas.LoginRequest):
    """
    Send a magic link to the user's email for passwordless authentication.
    
    Args:
        request: LoginRequest with email
        
    Returns:
        Success message
    """
    try:
        await neon_send_magic_link(request.email)
        return {"message": "Magic link sent successfully", "email": request.email}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send magic link: {str(e)}")

@router.post("/auth/verify", response_model=schemas.Token)
async def verify_magic_link(request: schemas.TokenVerifyRequest, db: Session = Depends(get_db)):
    """
    Verify the magic link token and return a JWT access token.
    
    Args:
        request: TokenVerifyRequest with magic link token
        db: Database session
        
    Returns:
        JWT access token
    """
    try:
        # Verify the magic link with Neon Auth
        neon_response = await neon_verify_magic_link(request.token)
        
        # Extract user info from Neon response
        # Note: The actual structure depends on Neon Auth response format
        # Adjust these fields based on actual Neon Auth response
        user_email = neon_response.get("user", {}).get("email") or neon_response.get("email")
        
        if not user_email:
            raise HTTPException(status_code=400, detail="Invalid token response from Neon Auth")
        
        # Find or create user in our database
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            user = User(email=user_email, created_at=datetime.utcnow())
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Create JWT token (sub must be string for jose library)
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

@router.post("/auth/dev-login", response_model=schemas.Token)
async def dev_login_endpoint(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Development login endpoint - bypasses magic link email for testing.
    Simply provide an email and you'll get a JWT token.
    
    IMPORTANT: This endpoint should be disabled in production!
    
    Args:
        request: LoginRequest with email
        db: Database session
        
    Returns:
        JWT access token
    """
    try:
        from .dev_auth import dev_login
        result = await dev_login(request.email, "dev-password", db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dev login failed: {str(e)}")

@router.get("/auth/me", response_model=schemas.UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's information.
    
    Args:
        current_user: Current authenticated user from JWT token
        
    Returns:
        User information
    """
    return current_user

# ============================================================================
# Survey Routes (Protected)
# ============================================================================

@router.post("/survey/submit", response_model=schemas.SurveyResponse)
def submit_survey(
    survey_data: schemas.SurveyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    try:
        survey = Survey(
            user_id=current_user.id,
            neon_user_id=current_user.email,  # Keep for backward compatibility
            answers=survey_data.answers,
            scores=survey_data.scores or {},
        )
        db.add(survey)
        db.commit()
        db.refresh(survey)
        return survey
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error submitting survey: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/surveys", response_model=List[schemas.SurveyResponse])
def list_user_surveys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all surveys for the authenticated user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of user's surveys
    """
    try:
        surveys = db.query(Survey).filter(Survey.user_id == current_user.id).order_by(Survey.created_at.desc()).all()
        return surveys
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error fetching surveys: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Public Routes
# ============================================================================

@router.get("/questions")
def get_questions():
    """
    Get the assessment questions.
    
    Returns:
        Assessment questions
    """
    return load_questions()

@router.get("/gifts")
def get_gifts():
    """
    Get information about spiritual gifts.
    
    Returns:
        Spiritual gifts data
    """
    return load_gifts()

@router.get("/scriptures")
def get_scriptures():
    """
    Get scripture references.
    
    Returns:
        Scriptures data
    """
    return load_scriptures()
