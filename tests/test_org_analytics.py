from datetime import datetime, timedelta
from app.services.survey_service import SurveyService
from app.models import Survey, User
from unittest.mock import MagicMock

def test_get_org_analytics_active_members():
    # Setup
    mock_db = MagicMock()
    org_id = "test-org-id"
    
    # 3 Surveys from 2 distinct users
    surveys = [
        Survey(user_id=1, org_id=org_id, scores={"A": 10}, created_at=datetime.utcnow()),
        Survey(user_id=1, org_id=org_id, scores={"B": 5}, created_at=datetime.utcnow()),
        Survey(user_id=2, org_id=org_id, scores={"C": 15}, created_at=datetime.utcnow())
    ]
    
    mock_db.query.return_value.filter.return_value.all.return_value = surveys
    
    # Execute
    analytics = SurveyService.get_org_analytics(mock_db, org_id)
    
    # Verify
    assert analytics["total_assessments"] == 3
    assert analytics["active_members_count"] == 2 # Distinct users

def test_get_org_analytics_trends():
    # Setup
    mock_db = MagicMock()
    org_id = "test-org-id"
    
    current_month = datetime.utcnow()
    last_month = current_month - timedelta(days=32)
    
    # Surveys in different months
    surveys = [
        Survey(user_id=1, org_id=org_id, scores={}, created_at=current_month),
        Survey(user_id=2, org_id=org_id, scores={}, created_at=current_month),
        Survey(user_id=3, org_id=org_id, scores={}, created_at=last_month)
    ]
    
    mock_db.query.return_value.filter.return_value.all.return_value = surveys
    
    # Execute
    analytics = SurveyService.get_org_analytics(mock_db, org_id)
    
    # Verify Trends Structure
    trends = analytics["assessments_trend"]
    assert isinstance(trends, list)
    assert len(trends) == 12 # Last 12 months
    
    # Verify Counts
    curr_key = current_month.strftime("%Y-%m")
    last_key = last_month.strftime("%Y-%m")
    
    curr_trend = next(t for t in trends if t["date"] == curr_key)
    last_trend = next(t for t in trends if t["date"] == last_key)
    
    assert curr_trend["count"] == 2
    assert last_trend["count"] == 1
