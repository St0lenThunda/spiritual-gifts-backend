from datetime import datetime, timedelta
import pytest
from app.models import Survey, User
from app.services import SurveyService

def test_survey_pagination(db, test_user):
    """Test pagination logic for user surveys."""
    
    # Create 25 surveys for the user
    base_time = datetime.utcnow()
    for i in range(25):
        survey = Survey(
            user_id=test_user.id,
            neon_user_id=test_user.email,
            answers={1: 5},
            scores={"Leadership": 5},
            created_at=base_time - timedelta(days=i) # Newest first = smallest index
        )
        db.add(survey)
    db.commit()
    
    # Test Page 1 (Limit 10)
    # expected: items 1-10 (created most recently)
    result_p1 = SurveyService.get_user_surveys(db, test_user, page=1, limit=10)
    assert len(result_p1["items"]) == 10
    assert result_p1["total"] == 25
    assert result_p1["page"] == 1
    assert result_p1["pages"] == 3  # 10, 10, 5
    
    # Test Page 3 (Limit 10)
    # expected: items 21-25 (5 items)
    result_p3 = SurveyService.get_user_surveys(db, test_user, page=3, limit=10)
    assert len(result_p3["items"]) == 5
    assert result_p3["page"] == 3
    
    # Test Pagination Offset Logic
    # Item 0 (newest) should be in Page 1, but not Page 2
    # Item 10 (11th newest) should be first in Page 2
    result_p2 = SurveyService.get_user_surveys(db, test_user, page=2, limit=10)
    
    id_p1_last = result_p1["items"][-1].id
    id_p2_first = result_p2["items"][0].id
    
    assert id_p1_last != id_p2_first
