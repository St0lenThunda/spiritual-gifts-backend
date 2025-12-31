# app/routers/denominations.py
"""API router for managing denominations and scripture sets.
Provides endpoints to list, retrieve, and create denominations.
Only admin users can create new denominations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..schemas import (
    DenominationCreate,
    DenominationResponse,
    ScriptureSetCreate,
    ScriptureSetResponse,
)
from uuid import UUID
from ..services.denomination_service import (
    list_denominations,
    get_denomination_by_slug,
    create_denomination,
    create_scripture_set,
    get_scripture_set,
    update_denomination,
    delete_denomination,
    list_scripture_sets,
    update_scripture_set,
    delete_scripture_set,
)
from ..neon_auth import get_current_user
from ..models import User

router = APIRouter(prefix="/denominations", tags=["Denominations"])

# ... (Existing GET/POST for denominations) ...

@router.get("/", response_model=List[DenominationResponse])
def get_denominations(db: Session = Depends(get_db)):
    """Return all available denominations."""
    return list_denominations(db)

@router.get("/{slug}", response_model=DenominationResponse)
def get_denomination(slug: str, db: Session = Depends(get_db)):
    """Retrieve a denomination by its slug."""
    denom = get_denomination_by_slug(db, slug)
    if not denom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Denomination not found")
    return denom

@router.post("/", response_model=DenominationResponse, status_code=status.HTTP_201_CREATED)
def create_new_denomination(
    payload: DenominationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new denomination (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create denominations")
    # Ensure slug is unique
    existing = get_denomination_by_slug(db, payload.slug)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Denomination slug already exists")
    return create_denomination(db, payload)

@router.put("/{slug}", response_model=DenominationResponse)
def update_existing_denomination(
    slug: str,
    payload: DenominationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a denomination (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can update denominations")
    denom = get_denomination_by_slug(db, slug)
    if not denom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Denomination not found")
    # If slug changes, check collision
    if payload.slug != slug:
        existing = get_denomination_by_slug(db, payload.slug)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="New slug already exists")
    
    return update_denomination(db, denom, payload)

@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_denomination(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a denomination (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete denominations")
    denom = get_denomination_by_slug(db, slug)
    if not denom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Denomination not found")
    delete_denomination(db, denom)

# --- Scripture Sets ---

@router.get("/scripture-sets/", response_model=List[ScriptureSetResponse])
def get_all_scripture_sets(db: Session = Depends(get_db)):
    """List all scripture sets."""
    return list_scripture_sets(db)

@router.get("/scripture-sets/{set_id}", response_model=ScriptureSetResponse)
def get_one_scripture_set(set_id: UUID, db: Session = Depends(get_db)):
    """Get a scripture set by ID."""
    ss = get_scripture_set(db, set_id)
    if not ss:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scripture set not found")
    return ss

@router.post("/scripture-sets/", response_model=ScriptureSetResponse, status_code=status.HTTP_201_CREATED)
def create_new_scripture_set(
    payload: ScriptureSetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new scripture set (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can create scripture sets")
    return create_scripture_set(db, payload)

@router.put("/scripture-sets/{set_id}", response_model=ScriptureSetResponse)
def update_existing_scripture_set(
    set_id: UUID,
    payload: ScriptureSetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a scripture set (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can update scripture sets")
    ss = get_scripture_set(db, set_id)
    if not ss:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scripture set not found")
    return update_scripture_set(db, ss, payload)

@router.delete("/scripture-sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_scripture_set(
    set_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a scripture set (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete scripture sets")
    ss = get_scripture_set(db, set_id)
    if not ss:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scripture set not found")
    delete_scripture_set(db, ss)
