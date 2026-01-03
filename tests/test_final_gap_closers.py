import pytest
import uuid
from sqlalchemy.orm import Session
from app.schemas import OrganizationMemberInvite
from app.services.survey_service import SurveyService
from app.models import Survey, User

def test_organization_member_invite_invalid_role():
    """Cover app/schemas.py:132"""
    with pytest.raises(ValueError) as exc:
        OrganizationMemberInvite(email="test@example.com", role="superadmin")
    assert "Role must be 'user', 'admin', or 'super_admin'" in str(exc.value)

def test_survey_service_get_user_surveys_with_org_id(db):
    """Cover app/services/survey_service.py:129"""
    user_id = 999
    org_id = uuid.uuid4()
    
    # Create test surveys
    s1 = Survey(user_id=user_id, org_id=org_id, scores={"test": 1}, answers={})
    s2 = Survey(user_id=user_id, org_id=uuid.uuid4(), scores={"test": 2}, answers={})
    db.add_all([s1, s2])
    db.commit()
    
    user = User(id=user_id)
    
    # Fetch with org_id
    res = SurveyService.get_user_surveys(db, user, org_id=org_id)
    assert res["total"] == 1
    assert res["items"][0].org_id == org_id

def test_survey_service_get_org_surveys(db):
    """Cover app/services/survey_service.py:166-176"""
    org_id = uuid.uuid4()
    
    # Create surveys for this org
    surveys = [
        Survey(user_id=1, org_id=org_id, scores={"v": i}, answers={})
        for i in range(5)
    ]
    # Create survey for another org
    other = Survey(user_id=1, org_id=uuid.uuid4(), scores={"v": 100}, answers={})
    
    db.add_all(surveys)
    db.add(other)
    db.commit()
    
    # Fetch org surveys
    res = SurveyService.get_org_surveys(db, org_id)
    assert res["total"] == 5
    assert len(res["items"]) == 5
    
    # Test pagination
    res_paginated = SurveyService.get_org_surveys(db, org_id, page=1, limit=2)
    assert res_paginated["total"] == 5
    assert len(res_paginated["items"]) == 2
    assert res_paginated["pages"] == 3
