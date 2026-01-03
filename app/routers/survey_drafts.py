from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..database import get_db
from ..neon_auth import get_current_user
from ..models import User
from .. import schemas
from ..services.survey_draft_service import SurveyDraftService
from ..logging_setup import logger
from fastapi_csrf_protect import CsrfProtect

router = APIRouter(prefix="/survey/draft", tags=["Survey Drafts"])

@router.get("", response_model=schemas.SurveyDraftResponse)
async def get_draft(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve the current assessment draft for the user."""
    draft = SurveyDraftService.get_draft(db, current_user)
    if not draft:
        raise HTTPException(status_code=404, detail="No draft found")
    return draft

@router.post("", response_model=schemas.SurveyDraftResponse)
async def upsert_draft(
    draft_data: schemas.SurveyDraftCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    csrf_protect: CsrfProtect = Depends()
):
    """Create or update an assessment draft."""
    await csrf_protect.validate_csrf(request)
    draft = SurveyDraftService.upsert_draft(db, current_user, draft_data)
    logger.info("survey_draft_saved", user_id=current_user.id)
    return draft

@router.delete("")
async def delete_draft(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    csrf_protect: CsrfProtect = Depends()
):
    """Manually delete an assessment draft."""
    await csrf_protect.validate_csrf(request)
    success = SurveyDraftService.delete_draft(db, current_user)
    if not success:
        raise HTTPException(status_code=404, detail="No draft found to delete")
    logger.info("survey_draft_deleted", user_id=current_user.id)
    return {"message": "Draft deleted successfully"}
