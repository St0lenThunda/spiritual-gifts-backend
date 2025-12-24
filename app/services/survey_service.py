"""
Survey service module.

Contains business logic for survey operations, including:
- Survey creation
- Survey retrieval
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
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
        scores: Optional[Dict[str, float]] = None,
        org_id: Optional[UUID] = None
    ) -> Survey:
        """
        Create a new survey for a user.
        
        Args:
            db: Database session
            user: User submitting the survey
            answers: Dictionary of question_id -> answer_value
            scores: Optional calculated gift scores (calculated if not provided)
            org_id: Optional organization ID for multi-tenancy
            
        Returns:
            Created Survey object
        """
        if not scores:
            scores = SurveyService.calculate_scores(answers)

        # Use org_id from parameter or from user's org
        survey_org_id = org_id or user.org_id

        survey = Survey(
            user_id=user.id,
            neon_user_id=user.email,  # Keep for backward compatibility
            answers=answers,
            scores=scores,
            org_id=survey_org_id,
        )
        db.add(survey)
        db.commit()
        db.refresh(survey)
        return survey
    
    @staticmethod
    def get_user_surveys(
        db: Session,
        user: User,
        page: int = 1,
        limit: int = 20,
        org_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get paginated surveys for a user, ordered by creation date (newest first).
        Optionally filters by organization for multi-tenancy.
        
        Args:
            db: Database session
            user: User to get surveys for
            page: Page number (1-indexed)
            limit: Items per page
            org_id: Optional organization ID filter
            
        Returns:
            Dictionary with items, total, page, limit, pages
        """
        query = db.query(Survey).filter(Survey.user_id == user.id)
        
        # Apply org filter if provided
        if org_id:
            query = query.filter(Survey.org_id == org_id)
        
        # Calculate totals
        total = query.count()
        pages = (total + limit - 1) // limit
        
        # Apply pagination
        offset = (page - 1) * limit
        items = query.order_by(Survey.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages
        }

    @staticmethod
    def get_org_surveys(
        db: Session,
        org_id: UUID,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get all surveys for an organization (admin view).
        
        Args:
            db: Database session
            org_id: Organization ID
            page: Page number (1-indexed)
            limit: Items per page
            
        Returns:
            Dictionary with items, total, page, limit, pages
        """
        query = db.query(Survey).filter(Survey.org_id == org_id)
        
        # Calculate totals
        total = query.count()
        pages = (total + limit - 1) // limit
        
        # Apply pagination
        offset = (page - 1) * limit
        items = query.order_by(Survey.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages
        }
