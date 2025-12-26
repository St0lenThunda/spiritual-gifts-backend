import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app
from app.services.survey_service import SurveyService
from app.models import User, Survey
from app.neon_auth import get_current_user

client = TestClient(app)

@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.org_id = uuid.uuid4()
    return user

def test_create_survey_default_version(mock_user):
    """Test creating survey uses default version."""
    mock_db = MagicMock()
    answers = {1: 5}
    
    survey = SurveyService.create_survey(
        db=mock_db,
        user=mock_user,
        answers=answers
    )
    
    # We can't easily check the default value since it's set by SQL/Model default usually,
    # but our service method sets it to "1.0" in the signature validation if we look at the code.
    # Actually, let's verify what arguments Survey constructor was called with if we mock it, 
    # but here we are testing the service logic which instantiates the model.
    # Since we are using a real Survey object (not mocked in the service code), we check the attribute.
    
    assert survey.assessment_version == "1.0"

def test_create_survey_custom_version(mock_user):
    """Test creating survey with custom version."""
    mock_db = MagicMock()
    answers = {1: 5}
    
    survey = SurveyService.create_survey(
        db=mock_db,
        user=mock_user,
        answers=answers,
        assessment_version="2.0"
    )
    
    assert survey.assessment_version == "2.0"
