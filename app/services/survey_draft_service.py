from sqlalchemy.orm import Session
from ..models import SurveyDraft, User
from .. import schemas
from typing import Optional
from uuid import UUID

class SurveyDraftService:
    @staticmethod
    def get_draft(db: Session, user: User) -> Optional[SurveyDraft]:
        """Retrieve the current draft for a user."""
        return db.query(SurveyDraft).filter(SurveyDraft.user_id == user.id).first()

    @staticmethod
    def upsert_draft(
        db: Session, 
        user: User, 
        draft_data: schemas.SurveyDraftCreate,
        org_id: Optional[UUID] = None
    ) -> SurveyDraft:
        """Create or update a survey draft."""
        draft = SurveyDraftService.get_draft(db, user)
        
        if not draft:
            draft = SurveyDraft(
                user_id=user.id,
                org_id=org_id or user.org_id,
                answers=draft_data.answers,
                current_step=draft_data.current_step,
                assessment_version=draft_data.assessment_version
            )
            db.add(draft)
        else:
            draft.answers = draft_data.answers
            draft.current_step = draft_data.current_step
            draft.assessment_version = draft_data.assessment_version
            if org_id:
                draft.org_id = org_id

        db.commit()
        db.refresh(draft)
        return draft

    @staticmethod
    def delete_draft(db: Session, user: User) -> bool:
        """Delete a user's draft."""
        draft = SurveyDraftService.get_draft(db, user)
        if draft:
            db.delete(draft)
            db.commit()
            return True
        return False
