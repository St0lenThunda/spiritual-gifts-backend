
import pytest
from app.services.entitlements import (
    get_plan_features,
    resolve_limit,
    Plan,
    TIER_FEATURES,
    LEGACY_PLAN_MAPPING
)

def test_get_plan_features_valid():
    """Test retrieving features for valid plans."""
    for plan in Plan:
        features = get_plan_features(plan.value)
        assert features == TIER_FEATURES[plan]

def test_get_plan_features_legacy():
    """Test retrieving features for legacy plan names."""
    for legacy, modern in LEGACY_PLAN_MAPPING.items():
        features = get_plan_features(legacy)
        assert features == TIER_FEATURES[modern]

def test_get_plan_features_invalid():
    """Test fallback to FREE plan for invalid inputs."""
    assert get_plan_features("unknown") == TIER_FEATURES[Plan.INDIVIDUAL]
    assert get_plan_features(None) == TIER_FEATURES[Plan.INDIVIDUAL]
    assert get_plan_features("") == TIER_FEATURES[Plan.INDIVIDUAL]

def test_resolve_limit():
    """Test resolving specific limits."""
    # Known limit
    limit = resolve_limit(Plan.INDIVIDUAL.value, "users")
    assert limit == 1
    
    # Unknown feature (default 0)
    limit = resolve_limit(Plan.INDIVIDUAL.value, "non_existent_feature")
    assert limit == 0
    
    # Legacy plan
    limit = resolve_limit("starter", "users")
    assert limit == 50
