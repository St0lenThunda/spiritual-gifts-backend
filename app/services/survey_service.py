"""
Survey service module.

Contains business logic for survey operations, including:
- Survey creation
- Survey retrieval
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..models import Survey, User


class SurveyService:
    """Service class for survey-related business logic."""
    
    @staticmethod
    def create_survey(
        db: Session,
        user: User,
        answers: Dict[int, int],
        scores: Optional[Dict[str, float]] = None
    ) -> Survey:
        """
        Create a new survey for a user.
        
        Args:
            db: Database session
            user: User submitting the survey
            answers: Dictionary of question_id -> answer_value
            scores: Optional calculated gift scores
            
        Returns:
            Created Survey object
        """
        survey = Survey(
            user_id=user.id,
            neon_user_id=user.email,  # Keep for backward compatibility
            answers=answers,
            scores=scores or {},
        )
        db.add(survey)
        db.commit()
        db.refresh(survey)
        return survey
    
    @staticmethod
    def get_user_surveys(db: Session, user: User) -> List[Survey]:
        """
        Get all surveys for a user, ordered by creation date (newest first).
        
        Args:
            db: Database session
            user: User to get surveys for
            
        Returns:
            List of Survey objects
        """
        return (
            db.query(Survey)
            .filter(Survey.user_id == user.id)
            .order_by(Survey.created_at.desc())
            .all()
        )
