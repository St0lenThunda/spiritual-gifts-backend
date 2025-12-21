import pytest
from sqlalchemy.orm import Session
from datetime import datetime
from app.models import User, Survey
from app.services.auth_service import AuthService
from app.services.survey_service import SurveyService
from app.services.getJSONData import load_questions, load_gifts, load_scriptures

def test_auth_service_get_or_create_user(db: Session):
    """Test creating a new user and retrieving an existing one."""
    email = "test_service@example.com"
    
    # Create new
    user = AuthService.get_or_create_user(db, email)
    assert user.id is not None
    assert user.email == email
    
    # Retrieve existing
    user_repeat = AuthService.get_or_create_user(db, email)
    assert user_repeat.id == user.id
    
    # Verify count
    assert db.query(User).count() == 1

def test_auth_service_update_last_login(db: Session):
    """Test updating the last login timestamp."""
    user = AuthService.get_or_create_user(db, "login@example.com")
    assert user.last_login is None
    
    AuthService.update_last_login(db, user)
    assert user.last_login is not None
    assert isinstance(user.last_login, datetime)

def test_survey_service_calculate_scores():
    """Test spiritual gift score calculation logic."""
    # Mock answers (1-5 range)
    # Question 6 is Leadership (GIFT_MAPPINGS)
    # Question 1 is Administration
    answers = {
        6: 5, # Leadership
        16: 4, # Leadership
        27: 3, # Leadership
        43: 2, # Leadership
        65: 1, # Leadership -> Total 15
        "1": 5, # Administration (string key)
        17: 5, # Administration
        31: 5, # Administration
        47: 5, # Administration
        59: 5, # Administration -> Total 25
    }
    
    scores = SurveyService.calculate_scores(answers)
    
    assert scores["Leadership"] == 15
    assert scores["Administration"] == 25
    assert scores["Teaching"] == 0 # Default for mission answers
    assert len(scores) == 16 # Total gifts

def test_survey_service_create_survey(db: Session):
    """Test persisting a survey to the database."""
    user = AuthService.get_or_create_user(db, "survey_user@example.com")
    answers = {1: 5, 2: 4}
    
    # Create with auto-calculation
    survey = SurveyService.create_survey(db, user, answers)
    
    assert survey.id is not None
    assert survey.user_id == user.id
    # SQLAlchemy JSON column converts keys to strings
    assert survey.answers == {str(k): v for k, v in answers.items()}
    assert "Administration" in survey.scores
    
    # Verify DB persistence
    db_survey = db.query(Survey).filter(Survey.id == survey.id).first()
    assert db_survey is not None
    assert db_survey.scores["Administration"] == 5

def test_survey_service_get_user_surveys(db: Session):
    """Test retrieving survey history for a user."""
    user = AuthService.get_or_create_user(db, "history@example.com")
    
    # Create multiple surveys
    SurveyService.create_survey(db, user, {1: 3})
    SurveyService.create_survey(db, user, {1: 5})
    
    surveys = SurveyService.get_user_surveys(db, user)
    assert len(surveys) == 2
    # Check ordering (newest first)
    assert surveys[0].scores["Administration"] == 5
    assert surveys[1].scores["Administration"] == 3

def test_get_json_data():
    """Test loading static JSON data."""
    data = load_questions()
    assert isinstance(data, dict)
    assert "assessment" in data
    questions = data["assessment"]["questions"]
    assert isinstance(questions, list)
    assert len(questions) > 0
    assert "text" in questions[0]
    
    gifts = load_gifts()
    assert isinstance(gifts, dict)
    assert len(gifts) > 0
    # Check for a specific gift to verify structure
    assert "Administration" in gifts
    assert "name" in gifts["Administration"]
    
    scriptures = load_scriptures()
    assert isinstance(scriptures, dict)
    assert len(scriptures) > 0
