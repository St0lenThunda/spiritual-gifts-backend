"""
Survey service module.

Contains business logic for survey operations, including:
- Survey creation
- Survey retrieval
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import or_
from sqlalchemy.orm import Session
from ..models import Survey, User


from datetime import datetime, timedelta, UTC
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
    def generate_discernment(scores: Dict[str, float], active_gift_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generates a discernment explanation object based on scores.
        Narrative indicators instead of raw math.
        Respects active_gift_keys if provided.
        """
        high = []
        moderate = []
        
        # Filter out 'overall' and sort gifts by score descending
        valid_scores = {k: v for k, v in scores.items() if k.lower() != 'overall'}
        
        # Apply whitelist if provided (Constraint Layer)
        if active_gift_keys:
            active_set = set(active_gift_keys)
            valid_scores = {k: v for k, v in valid_scores.items() if k in active_set}

        sorted_gifts = sorted(valid_scores.items(), key=lambda x: x[1], reverse=True)
        
        for gift, score in sorted_gifts:
            if score >= 32:
                high.append(gift)
            elif score >= 24:
                moderate.append(gift)
        
        # Fallback: if none are >= 24, take top 3 as moderate (from active set)
        if not high and not moderate and sorted_gifts:
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

        # Resolve Denomination Context for Discernment Whitelisting
        active_gift_keys = None
        survey_org_id = org_id or user.org_id
        if survey_org_id:
            from ..models import Organization, Denomination
            org_context = db.get(Organization, survey_org_id)
            if org_context and org_context.denomination_id:
                denom = db.get(Denomination, org_context.denomination_id)
                if denom:
                    active_gift_keys = denom.active_gift_keys

        discernment = SurveyService.generate_discernment(scores, active_gift_keys)

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
        
        # Clean up any existing draft
        from .survey_draft_service import SurveyDraftService
        SurveyDraftService.delete_draft(db, user)

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
        # Get all members of the organization
        members = db.query(User).filter(User.org_id == org_id).all()
        member_ids = [m.id for m in members]

        if not member_ids:
             # Fallback if no members found (unlikely if org exists, but safe)
             surveys = db.query(Survey).filter(Survey.org_id == org_id).all()
        else:
            # Fetch surveys for these members OR explicitly linked to the org
            # This ensures we capture pre-join assessments for current members
            surveys = db.query(Survey).filter(
                or_(
                    Survey.org_id == org_id,
                    Survey.user_id.in_(member_ids)
                )
            ).all()
        
        # Count in-progress drafts
        from ..models import SurveyDraft
        draft_count = db.query(SurveyDraft).filter(SurveyDraft.org_id == org_id).count()

        total_assessments = len(surveys)
        if total_assessments == 0:
            return {
                "total_assessments": 0,
                "gift_averages": {},
                "top_gifts_distribution": {},
                "gift_demographics": {},
                "in_progress_drafts": draft_count
            }
            
        # Initialize accumulators
        gift_totals = {}
        top_gifts_counts = {}
        gift_demographics = {} # New accumulator for demographics
        
        # Resolve Denomination for filtering (ADR-022)
        active_gift_keys = None
        from ..models import Organization, Denomination
        org = db.get(Organization, org_id)
        if org and org.denomination_id:
            denom = db.get(Denomination, org.denomination_id)
            if denom:
                active_gift_keys = denom.active_gift_keys
        
        active_set = set(active_gift_keys) if active_gift_keys else None

        for survey in surveys:
            scores = survey.scores or {}
            
            # Filter and Accumulate totals for averages
            for gift, score in scores.items():
                if gift.lower() == 'overall':
                    continue
                if active_set and gift not in active_set:
                    continue
                gift_totals[gift] = gift_totals.get(gift, 0) + score
                
            # Determine top gift for this survey (respecting active set)
            if scores:
                valid_scores = {k: v for k, v in scores.items() if k.lower() != 'overall'}
                if active_set:
                    valid_scores = {k: v for k, v in valid_scores.items() if k in active_set}
                
                if valid_scores:
                    top_gift = max(valid_scores.items(), key=lambda x: x[1])[0]
                    top_gifts_counts[top_gift] = top_gifts_counts.get(top_gift, 0) + 1
                    
                    # Track anonymized demographics (Role & Tenure)
                    if top_gift not in gift_demographics:
                        gift_demographics[top_gift] = {
                            "roles": {},
                            "tenure": {}
                        }
                    
                    # Get user context
                    user = survey.user
                    if user:
                        role_key = user.role
                        gift_demographics[top_gift]["roles"][role_key] = gift_demographics[top_gift]["roles"].get(role_key, 0) + 1
                        
                        if user.created_at:
                            now_naive = datetime.now(UTC).replace(tzinfo=None)
                            tenure_years = (now_naive - user.created_at).days / 365.25
                            
                            if tenure_years < 1:
                                band = "<1_year"
                            elif 1 <= tenure_years < 3:
                                band = "1-3_years"
                            else:
                                band = "3+_years"
                                
                            gift_demographics[top_gift]["tenure"][band] = gift_demographics[top_gift]["tenure"].get(band, 0) + 1
        
        # Calculate averages (only for active gifts)
        gift_averages = {
            gift: round(total / total_assessments, 1)
            for gift, total in gift_totals.items()
        }
        
        # If active_set is present, ensure all active gifts are in the result even with 0
        if active_set:
            for gift in active_set:
                if gift not in gift_averages:
                    gift_averages[gift] = 0.0
        
        # Sort distribution by count desc
        sorted_distribution = dict(sorted(
            top_gifts_counts.items(), 
            key=lambda item: item[1], 
            reverse=True
        ))
        
        # Calculate active members (unique users who have taken an assessment)
        active_members_count = len(set(s.user_id for s in surveys))
        
        # Initialize last 12 months with 0
        today = datetime.now(UTC)
        trends = {}
        
        for i in range(12):
            target_month_idx = today.month - i - 1
            year_offset = 0
            while target_month_idx < 0:
                target_month_idx += 12
                year_offset -= 1
            
            target_year = today.year + year_offset
            target_month = target_month_idx + 1
            
            key = f"{target_year}-{target_month:02d}"
            trends[key] = 0
            
        for survey in surveys:
            month_key = survey.created_at.strftime("%Y-%m")
            if month_key in trends:
                trends[month_key] += 1
            
        trends_list = [
            {"date": k, "count": v} 
            for k, v in sorted(trends.items())
        ]
        
        MIN_ANONYMITY_THRESHOLD = 5
        insufficient_data = total_assessments < MIN_ANONYMITY_THRESHOLD
        
        if insufficient_data:
            gift_demographics = {} 

        return {
            "total_assessments": total_assessments,
            "active_members_count": active_members_count,
            "assessments_trend": trends_list,
            "gift_averages": gift_averages,
            "top_gifts_distribution": sorted_distribution,
            "gift_demographics": gift_demographics,
            "insufficient_data": insufficient_data,
            "in_progress_drafts": draft_count
        }
