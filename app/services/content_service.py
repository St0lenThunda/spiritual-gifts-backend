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
        Filters questions based on the denomination's active_gift_keys if available.
        """
        questions_data = load_questions(locale)
        
        if not org_slug:
            return questions_data

        # Resolve Denomination for whitelisting
        org = db.query(Organization).filter(Organization.slug == org_slug).first()
        if not org or not org.denomination_id:
            return questions_data
        
        denom = db.get(Denomination, org.denomination_id)
        if not denom or not denom.active_gift_keys:
            return questions_data

        # Filter questions based on active_gift_keys
        active_keys = set(denom.active_gift_keys)
        filtered_questions = [
            q for q in questions_data["assessment"]["questions"] 
            if q.get("gift") in active_keys
        ]
        
        questions_data["assessment"]["questions"] = filtered_questions
        return questions_data

    @staticmethod
    def get_gifts_for_context(db: Session, locale: str, org_slug: str = None):
        """
        Load gifts for a given locale, optionally overridden by the organization's denomination.
        Filters gifts based on active_gift_keys and applies pastoral_overlays.
        """
        # 1. Load base gifts
        gifts = load_gifts(locale)
        
        if not org_slug:
            return gifts

        # 2. Resolve Denomination
        org = db.query(Organization).filter(Organization.slug == org_slug).first()
        if not org or not org.denomination_id:
            return gifts
        
        denom = db.get(Denomination, org.denomination_id)
        if not denom:
            return gifts

        # 3. Apply active_gift_keys Whitelist (Structural Layer)
        if denom.active_gift_keys:
            active_keys = set(denom.active_gift_keys)
            gifts = {k: v for k, v in gifts.items() if k in active_keys}
        
        # 4. Integrate Scripture Set overrides
        if denom.scripture_set:
            scripture_overrides = denom.scripture_set.verses
            if scripture_overrides:
                for gift_name, new_refs in scripture_overrides.items():
                    if gift_name in gifts:
                        gifts[gift_name]["scriptures"] = new_refs

        # 5. Apply Pastoral Overlays (Interpretive Layer)
        if denom.pastoral_overlays:
            for gift_name, overlay in denom.pastoral_overlays.items():
                if gift_name in gifts:
                    # Merge overlay data into gift (notes, cautions, etc.)
                    # We preserve existing keys but prioritize overlay values
                    gifts[gift_name]["pastoral_context"] = overlay

        return gifts
