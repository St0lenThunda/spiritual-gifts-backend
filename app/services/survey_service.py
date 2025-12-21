"""
Survey service module.

Contains business logic for survey operations, including:
- Survey creation
- Survey retrieval
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..models import Survey, User


from ..services.getJSONData import load_questions


class SurveyService:
    """Service class for survey-related business logic."""
    
    _gift_mappings: Optional[Dict[str, List[int]]] = None

    @classmethod
    def get_gift_mappings(cls) -> Dict[str, List[int]]:
        """
        Builds the gift mappings from the questions.json data.
        Caches the result in a class variable for efficiency.
        """
        if cls._gift_mappings is None:
            data = load_questions()
            mappings = {}
            for q in data["assessment"]["questions"]:
                gift = q["gift"]
                if gift not in mappings:
                    mappings[gift] = []
                mappings[gift].append(q["id"])
            cls._gift_mappings = mappings
        return cls._gift_mappings

    @staticmethod
    def calculate_scores(answers: Dict[Any, Any]) -> Dict[str, int]:
        """
        Calculates the total score for each spiritual gift based on the provided answers.
        
        Args:
            answers: Dictionary of question_id -> answer_value
            
        Returns:
            Dictionary mapping Gift Name to Total Score
        """
        mappings = SurveyService.get_gift_mappings()
        scores = {}
        for gift, question_ids in mappings.items():
            total = 0
            for q_id in question_ids:
                # Handle potential string keys and missing answers
                val = answers.get(q_id) or answers.get(str(q_id)) or 0
                try:
                    total += int(val)
                except (ValueError, TypeError):
                    continue
            scores[gift] = total
        return scores

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
            scores: Optional calculated gift scores (calculated if not provided)
            
        Returns:
            Created Survey object
        """
        if not scores:
            scores = SurveyService.calculate_scores(answers)

        survey = Survey(
            user_id=user.id,
            neon_user_id=user.email,  # Keep for backward compatibility
            answers=answers,
            scores=scores,
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
