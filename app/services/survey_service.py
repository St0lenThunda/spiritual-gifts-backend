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
    def generate_discernment(scores: Dict[str, float]) -> Dict[str, Any]:
        """
        Generates a discernment explanation object based on scores.
        Narrative indicators instead of raw math.
        
        Thresholds (assuming 8 questions per gift, max 40 per gift):
        - High: >= 32 (80%)
        - Moderate: >= 24 (60%)
        """
        high = []
        moderate = []
        
        # Filter out 'overall' and sort gifts by score descending
        valid_scores = {k: v for k, v in scores.items() if k.lower() != 'overall'}
        sorted_gifts = sorted(valid_scores.items(), key=lambda x: x[1], reverse=True)
        
        for gift, score in sorted_gifts:
            if score >= 32:
                high.append(gift)
            elif score >= 24:
                moderate.append(gift)
        
        # Fallback: if none are >= 24, take top 3 as moderate
        if not high and not moderate:
            moderate = [item[0] for item in sorted_gifts[:3]]

        context_notes = "These results indicate patterns of spiritual interest and effectiveness. " \
                        "They are most helpful when discussed with ministry leaders who can help confirm " \
                        "these gifts through shared experience and observation."

        return {
            "high_indicators": high,
            "moderate_indicators": moderate,
            "context_notes": context_notes
        }

    @staticmethod
    def create_survey(
        db: Session,
        user: User,
        answers: Dict[int, int],
        scores: Optional[Dict[str, float]] = None,
        org_id: Optional[UUID] = None,
        assessment_version: str = "1.0"
    ) -> Survey:
        """
        Create a new survey for a user.
        
        Args:
            db: Database session
            user: User submitting the survey
            answers: Dictionary of question_id -> answer_value
            scores: Optional calculated gift scores (calculated if not provided)
            org_id: Optional organization ID for multi-tenancy
            assessment_version: Version of the assessment questions
            
        Returns:
            Created Survey object
        """
        if not scores:
            scores = SurveyService.calculate_scores(answers)

        discernment = SurveyService.generate_discernment(scores)

        # Use org_id from parameter or from user's org
        survey_org_id = org_id or user.org_id

        survey = Survey(
            user_id=user.id,
            neon_user_id=user.email,  # Keep for backward compatibility
            answers=answers,
            scores=scores,
            discernment=discernment,
            org_id=survey_org_id,
            assessment_version=assessment_version
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

    @staticmethod
    def get_org_analytics(
        db: Session,
        org_id: UUID
    ) -> Dict[str, Any]:
        """
        Calculates aggregated analytics for an organization.
        
        Args:
            db: Database session
            org_id: Organization ID
            
        Returns:
            Dictionary containing analytics data:
            - total_assessments: int
            - gift_averages: Dict[str, float]
            - top_gifts_distribution: Dict[str, int]
        """
        surveys = db.query(Survey).filter(Survey.org_id == org_id).all()
        
        total_assessments = len(surveys)
        if total_assessments == 0:
            return {
                "total_assessments": 0,
                "gift_averages": {},
                "top_gifts_distribution": {}
            }
            
        # Initialize accumulators
        gift_totals = {}
        top_gifts_counts = {}
        
        for survey in surveys:
            scores = survey.scores or {}
            
            # Accumulate totals for averages
            for gift, score in scores.items():
                if gift.lower() == 'overall':
                    continue
                gift_totals[gift] = gift_totals.get(gift, 0) + score
                
            # Determine top gift for this survey
            if scores:
                # Filter out 'overall' before finding max
                valid_scores = {k: v for k, v in scores.items() if k.lower() != 'overall'}
                if valid_scores:
                    top_gift = max(valid_scores.items(), key=lambda x: x[1])[0]
                    top_gifts_counts[top_gift] = top_gifts_counts.get(top_gift, 0) + 1
        
        # Calculate averages
        gift_averages = {
            gift: round(total / total_assessments, 1)
            for gift, total in gift_totals.items()
        }
        
        # Sort distribution by count desc
        sorted_distribution = dict(sorted(
            top_gifts_counts.items(), 
            key=lambda item: item[1], 
            reverse=True
        ))
        
        # Calculate active members (unique users who have taken an assessment)
        active_members_count = len(set(s.user_id for s in surveys))
        
        # Calculate trends (group by month for the last 12 months)
        from datetime import datetime, timedelta
        
        # Initialize last 12 months with 0
        today = datetime.utcnow()
        trends = {}
        
        # Generate last 12 months keys accurately
        for i in range(12):
            # Calculate target year and month
            # effective_month is 1-based index (e.g. jan=1). 
            # If today.month is 5 (May), i=0 -> 5. i=4 -> 1 (Jan). i=5 -> 0 (needs wrap to Dec prev year)
            
            target_month_idx = today.month - i - 1 # 0-indexed (0=Jan, 11=Dec)
            
            # Handle negative wrapping
            year_offset = 0
            while target_month_idx < 0:
                target_month_idx += 12
                year_offset -= 1
            
            target_year = today.year + year_offset
            target_month = target_month_idx + 1 # Convert back to 1-based
            
            key = f"{target_year}-{target_month:02d}"
            trends[key] = 0
            
        for survey in surveys:
            month_key = survey.created_at.strftime("%Y-%m")
            if month_key in trends:
                trends[month_key] += 1
            
        # Convert trends to list of dicts for frontend
        trends_list = [
            {"date": k, "count": v} 
            for k, v in sorted(trends.items())
        ]
        
        return {
            "total_assessments": total_assessments,
            "active_members_count": active_members_count,
            "assessments_trend": trends_list,
            "gift_averages": gift_averages,
            "top_gifts_distribution": sorted_distribution
        }
