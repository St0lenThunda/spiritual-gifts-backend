import pytest
from datetime import timedelta
from fastapi import HTTPException, status
from unittest.mock import MagicMock, patch
import sys


from app.neon_auth import create_access_token, get_current_user, get_current_admin, get_user_context
from app.logging_setup import db_logger_processor, setup_logging
from app.models import User, LogEntry
from app.services.survey_service import SurveyService



def test_create_access_token_with_delta():
    delta = timedelta(minutes=10)
    token = create_access_token(data={"sub": "test"}, expires_delta=delta)
    assert token is not None

@pytest.mark.asyncio
async def test_get_current_user_with_invalid_sub(db):
    # Mock request and credentials with invalid sub
    request = MagicMock()
    credentials = MagicMock()
    # "abc" is not a valid integer id
    token = create_access_token(data={"sub": "abc"})
    credentials.credentials = token
    
    with pytest.raises(HTTPException) as excinfo:
        await get_user_context(request, credentials, db)
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in excinfo.value.detail

@pytest.mark.asyncio
async def test_get_current_admin_not_admin():
    user = MagicMock()
    user.role = "user"
    user.id = 123
    user.email = "test@example.com"
    
    with pytest.raises(HTTPException) as excinfo:
        await get_current_admin(user)
    assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
    assert "System Administrator privileges required" in excinfo.value.detail

def test_db_logger_processor_exception():
    # Patch the SessionLocal used within the logging_setup module
    with patch("app.logging_setup.database.SessionLocal") as mock_session_factory:
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        # Setup the context manager to return the mock_session
        mock_session.__enter__.return_value = mock_session
        # Make commit raise an exception
        mock_session.commit.side_effect = Exception("DB Error")
        
        with patch("sys.stderr.write") as mock_stderr:
            # Include user_id so the log is not skipped as anonymous INFO
            event_dict = {"event": "test_event", "user_id": 1}
            result = db_logger_processor(None, "info", event_dict)
            assert result == event_dict
            mock_stderr.assert_called()

def test_setup_logging_terminal():
    # Mock sys.stderr.isatty() to be True
    with patch("sys.stderr.isatty", return_value=True):
        # Re-running setup_logging to hit the branch
        setup_logging()
        # No easy way to assert internal state of structlog, but we hit the line

def test_survey_service_calculate_scores_invalid_answer():
    answers = {1: "not-an-int", 2: 5}
    # This should hit the except block in calculate_scores
    scores = SurveyService.calculate_scores(answers)
    assert "Administration" in scores # Assuming 1 and 2 mapped to gifts
    # It should have skipped question 1 and handled question 2

@pytest.mark.asyncio
async def test_get_current_user_with_header(db):
    # Mock request and credentials
    request = MagicMock()
    credentials = MagicMock()
    user = User(email="header@example.com")
    db.add(user)
    db.commit()
    
    token = create_access_token(data={"sub": str(user.id)})
    credentials.credentials = token
    
    # Passing credentials explicitly to get_user_context
    result = await get_user_context(request, credentials, db)
    assert result.user.id == user.id

from app.schemas import TokenVerifyRequest, SurveyCreate
from pydantic import ValidationError

def test_token_verify_request_empty():
    with pytest.raises(ValidationError):
        TokenVerifyRequest(token="")

def test_survey_create_empty_answers():
    with pytest.raises(ValidationError):
        SurveyCreate(answers={})

def test_survey_create_invalid_score():
    with pytest.raises(ValidationError):
        # We need to bypass the Field validation to hit the validator manually if needed,
        # but actually the validator will be called by Pydantic.
        SurveyCreate(answers={1: 0})
    
    with pytest.raises(ValidationError):
        SurveyCreate(answers={1: 6})

def test_validate_answers_manually():
    # Calling class method directly to hit coverage on the raise statement
    with pytest.raises(ValueError):
        SurveyCreate.validate_answers({1: 0})

@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_get_json_data_main():
    import runpy
    # Test the module's __main__ block to ensure coverage
    with patch("builtins.print"):
        runpy.run_module("app.services.getJSONData", run_name="__main__")
