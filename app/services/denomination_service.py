# app/services/denomination_service.py
"""Service layer for handling denominations and scripture sets.
Provides functions used by API routers to retrieve and manage theological profiles.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..models import Denomination, ScriptureSet
from ..schemas import DenominationCreate, DenominationResponse, ScriptureSetCreate, ScriptureSetResponse


def get_denomination_by_slug(db: Session, slug: str) -> Optional[Denomination]:
    """Return a Denomination model matching the given slug, or None if not found."""
    return db.query(Denomination).filter(Denomination.slug == slug).first()


def list_denominations(db: Session) -> List[Denomination]:
    """Return all denominations ordered by display_name."""
    return db.query(Denomination).order_by(Denomination.display_name).all()


def create_denomination(db: Session, payload: DenominationCreate) -> Denomination:
    """Create a new Denomination record from a Pydantic payload."""
    denom = Denomination(
        slug=payload.slug,
        display_name=payload.display_name,
        logo_url=payload.logo_url,
        default_currency=payload.default_currency,
        scripture_set_id=payload.scripture_set_id,
    )
    db.add(denom)
    db.flush()  # assign id
    db.refresh(denom)
    return denom


def get_scripture_set(db: Session, set_id: UUID) -> Optional[ScriptureSet]:
    return db.query(ScriptureSet).filter(ScriptureSet.id == set_id).first()


def create_scripture_set(db: Session, payload: ScriptureSetCreate) -> ScriptureSet:
    ss = ScriptureSet(name=payload.name, verses=payload.verses)
    db.add(ss)
    db.flush()
    db.refresh(ss)
    return ss

# Helper to convert model to response schema (FastAPI can use .from_orm)
# No extra mapping needed because Pydantic ConfigDict(from_attributes=True) is set.

def update_denomination(db: Session, db_denom: Denomination, payload: DenominationCreate) -> Denomination:
    """Update an existing denomination."""
    # Note: Using DenominationCreate schema for update is okay for now, or you can separate UpdateSchema
    if payload.slug:
        db_denom.slug = payload.slug
    if payload.display_name:
        db_denom.display_name = payload.display_name
    db_denom.logo_url = payload.logo_url
    db_denom.default_currency = payload.default_currency
    db_denom.scripture_set_id = payload.scripture_set_id
    
    db.commit()
    db.refresh(db_denom)
    return db_denom

def delete_denomination(db: Session, db_denom: Denomination):
    """Delete a denomination."""
    db.delete(db_denom)
    db.commit()

def list_scripture_sets(db: Session) -> List[ScriptureSet]:
    """Return all scripture sets."""
    return db.query(ScriptureSet).order_by(ScriptureSet.name).all()

def update_scripture_set(db: Session, db_ss: ScriptureSet, payload: ScriptureSetCreate) -> ScriptureSet:
    """Update an existing scripture set."""
    db_ss.name = payload.name
    db_ss.verses = payload.verses
    db.commit()
    db.refresh(db_ss)
    return db_ss

def delete_scripture_set(db: Session, db_ss: ScriptureSet):
    """Delete a scripture set."""
    db.delete(db_ss)
    db.commit()
