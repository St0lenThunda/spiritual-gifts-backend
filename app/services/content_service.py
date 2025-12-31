import json
from pathlib import Path
from sqlalchemy.orm import Session
from ..models import Denomination, ScriptureSet, Organization
from .getJSONData import load_questions, load_gifts, load_scriptures, LOCALES_DIR, DATA_DIR

class ContentService:
    @staticmethod
    def get_questions_for_context(db: Session, locale: str, org_slug: str = None):
        """
        Load questions for a given locale and organization context.
        TODO: Implement denomination-specific question overrides if needed.
        For now, just returns standard questions.
        """
        return load_questions(locale)

    @staticmethod
    def get_gifts_for_context(db: Session, locale: str, org_slug: str = None):
        """
        Load gifts for a given locale, optionally overridden by the organization's denomination.
        """
        # 1. Load base gifts
        gifts = load_gifts(locale)
        
        if not org_slug:
            return gifts

        # 2. Resolve Denomination
        org = db.query(Organization).filter(Organization.slug == org_slug).first()
        if not org or not org.denomination_id:
            return gifts
        
        # 3. Load Scripture Set provided by Denomination
        denom = db.query(Denomination).get(org.denomination_id)
        if not denom or not denom.scripture_set:
            return gifts

        scripture_overrides = denom.scripture_set.verses  # Expected format: {"GiftName": ["Ref1", "Ref2"]}
        if not scripture_overrides:
            return gifts

        # 4. Merge Overrides
        for gift_name, new_refs in scripture_overrides.items():
            # Check if gift exists in base set (handle case sensitivity?)
            # gifts keys are "Administration", etc.
            if gift_name in gifts:
                gifts[gift_name]["scriptures"] = new_refs
            
        return gifts
