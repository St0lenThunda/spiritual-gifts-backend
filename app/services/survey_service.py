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
    
    GIFT_MAPPINGS = {
        "Leadership": [6, 16, 27, 43, 65],
        "Administration": [1, 17, 31, 47, 59],
        "Teaching": [2, 18, 33, 61, 73],
        "Knowledge": [9, 24, 39, 68, 79],
        "Wisdom": [3, 19, 48, 62, 74],
        "Prophecy": [10, 25, 40, 54, 69],
        "Discernment": [11, 26, 41, 55, 70],
        "Exhortation": [20, 34, 49, 63, 75],
        "Shepherding": [4, 21, 35, 50, 76],
        "Faith": [12, 28, 42, 56, 80],
        "Evangelism": [5, 36, 51, 64, 77],
        "Apostleship": [13, 29, 44, 57, 71],
        "Service/Helps": [14, 30, 46, 58, 72],
        "Mercy": [7, 22, 37, 52, 66],
        "Giving": [8, 23, 38, 53, 67],
        "Hospitality": [15, 32, 45, 60, 78]
    }

    @staticmethod
    def calculate_scores(answers: Dict[Any, Any]) -> Dict[str, int]:
        """
        Calculates the total score for each spiritual gift based on the provided answers.
        
        Args:
            answers: Dictionary of question_id -> answer_value
            
        Returns:
            Dictionary mapping Gift Name to Total Score
        """
        scores = {}
        for gift, question_ids in SurveyService.GIFT_MAPPINGS.items():
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
