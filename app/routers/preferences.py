"""
Preferences API router for user preference management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from ..database import get_db
from ..models import User
from ..neon_auth import get_current_user
from .. import schemas
from ..services.entitlements import get_plan_features, FEATURE_THEME_ANALYTICS, FEATURE_AVAILABLE_THEMES
from ..logging_setup import logger

router = APIRouter()


@router.get("/user/preferences", response_model=schemas.UserPreferences)
async def get_user_preferences(
    org_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get user preferences, optionally scoped to an organization.
    Returns merged global + org-specific preferences.
    """
    global_prefs = current_user.global_preferences or {}
    
    if org_id and current_user.org_preferences:
        org_prefs = current_user.org_preferences.get(org_id, {})
        # Merge: org_prefs override global_prefs
        merged = {**global_prefs, **org_prefs}
        return merged
    
    return global_prefs


@router.patch("/user/preferences", response_model=schemas.UserPreferences)
async def update_user_preferences(
    preferences: schemas.PreferenceUpdate,
    org_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user preferences.
    If org_id is provided and sync_across_orgs is False, 
    updates org-specific preferences only.
    """
    
    # Ensure user is attached to the current session
    current_user = db.merge(current_user)
    current_global = current_user.global_preferences or {}
    
    # Check if user wants to sync across orgs
    sync_enabled = current_global.get("sync_across_orgs", True)
    
    # Validate theme if provided
    if preferences.theme:
        # Get user's available themes based on their org's tier
        if current_user.organization:
            features = get_plan_features(current_user.organization.plan)
            available_themes = features.get(FEATURE_AVAILABLE_THEMES, [])
            
            # Check if theme is allowed (or if it's "all" for Church tier)
            if available_themes != "all" and preferences.theme not in available_themes:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Theme '{preferences.theme}' not available on your plan. Available themes: {', '.join(available_themes)}"
                )
    
    if org_id and not sync_enabled:
        # Update org-specific preferences only
        current_org_prefs = current_user.org_preferences or {}
        org_prefs = current_org_prefs.get(org_id, {})
        
        # Merge updates (use model_dump for Pydantic v2)
        updated_org_prefs = {**org_prefs, **preferences.model_dump(exclude_unset=True)}
        current_org_prefs[org_id] = updated_org_prefs
        
        current_user.org_preferences = current_org_prefs
    else:
        # Update global preferences (use model_dump for Pydantic v2)
        updated = {**current_global, **preferences.model_dump(exclude_unset=True)}
        current_user.global_preferences = updated
    
    db.commit()
    db.refresh(current_user)
    
    logger.info("user_preferences_updated", user_id=current_user.id, org_id=org_id)
    
    # Return effective preferences
    return await get_user_preferences(org_id, current_user)


@router.post("/user/preferences/reset")
async def reset_preferences(
    org_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reset preferences to defaults.
    If org_id provided, resets only that org's overrides.
    """
    if org_id:
        # Reset org-specific preferences only
        if current_user.org_preferences and org_id in current_user.org_preferences:
            del current_user.org_preferences[org_id]
            # Mark as modified for SQLAlchemy
            current_user.org_preferences = dict(current_user.org_preferences)
    else:
        # Reset all preferences
        current_user.global_preferences = {}
        current_user.org_preferences = {}
    
    db.commit()
    logger.info("user_preferences_reset", user_id=current_user.id, org_id=org_id)
    
    return {"message": "Preferences reset successfully"}


@router.get("/admin/analytics/themes", response_model=schemas.ThemeAnalytics)
async def get_theme_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get theme preference analytics for the current organization.
    Only accessible to Ministry/Church tier admins.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not current_user.organization:
        raise HTTPException(status_code=400, detail="No organization associated with user")
    
    # Check if org has analytics entitlement
    org = current_user.organization
    features = get_plan_features(org.plan)
    
    if not features.get(FEATURE_THEME_ANALYTICS):
        raise HTTPException(
            status_code=403, 
            detail="Theme analytics not available on your plan. Upgrade to Ministry or Church tier."
        )
    
    # Get all users in this org
    users = db.query(User).filter(User.org_id == org.id).all()
    
    # Count theme preferences
    theme_counts = {}
    for user in users:
        # Resolve user's theme (org-specific or global)
        prefs = user.org_preferences.get(str(org.id), {}) if user.org_preferences else {}
        theme = prefs.get("theme") or (user.global_preferences or {}).get("theme") or "default"
        
        theme_counts[theme] = theme_counts.get(theme, 0) + 1
    
    # Calculate percentages
    total = len(users)
    theme_stats = [
        {
            "theme": theme,
            "count": count,
            "percentage": round((count / total * 100), 1) if total > 0 else 0
        }
        for theme, count in sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
    ]
    
    logger.info("theme_analytics_viewed", org_id=str(org.id), admin_id=current_user.id)
    
    return {
        "total_users": total,
        "theme_distribution": theme_stats,
        "org_has_custom_theme": bool(org.branding and org.branding.get("theme"))
    }
