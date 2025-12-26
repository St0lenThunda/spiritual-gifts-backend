from enum import Enum
from typing import Dict, Any, Optional

class Plan(str, Enum):
    FREE = "free"
    INDIVIDUAL = "individual"      # Was Starter
    MINISTRY = "ministry"          # Was Growth
    CHURCH = "church"              # Was Enterprise

# Feature Constants
FEATURE_USERS = "users"
FEATURE_ADMINS = "admins"
FEATURE_ASSESSMENTS_PER_MONTH = "assessments_per_month"
FEATURE_HISTORY_DAYS = "history_days"
FEATURE_EXPORTS = "exports"
FEATURE_ORG_SUPPORT = "org_support"
FEATURE_CUSTOM_WEIGHTING = "custom_weighting"
FEATURE_SUPPORT_LEVEL = "support_level"

# Support Levels
SUPPORT_NONE = "none"
SUPPORT_EMAIL = "email"
SUPPORT_PRIORITY = "priority"

TIER_FEATURES: Dict[Plan, Dict[str, Any]] = {
    Plan.FREE: {
        FEATURE_USERS: 10,
        FEATURE_ADMINS: 0,
        FEATURE_ASSESSMENTS_PER_MONTH: 20,
        FEATURE_HISTORY_DAYS: 30,
        FEATURE_EXPORTS: False,
        FEATURE_ORG_SUPPORT: False,
        FEATURE_CUSTOM_WEIGHTING: False,
        FEATURE_SUPPORT_LEVEL: SUPPORT_NONE
    },
    Plan.INDIVIDUAL: {
        FEATURE_USERS: 50,
        FEATURE_ADMINS: 1,
        FEATURE_ASSESSMENTS_PER_MONTH: 100,
        FEATURE_HISTORY_DAYS: 90,
        FEATURE_EXPORTS: False,
        FEATURE_ORG_SUPPORT: False,
        FEATURE_CUSTOM_WEIGHTING: False,
        FEATURE_SUPPORT_LEVEL: SUPPORT_EMAIL
    },
    Plan.MINISTRY: {
        FEATURE_USERS: 100,
        FEATURE_ADMINS: 5,
        FEATURE_ASSESSMENTS_PER_MONTH: 500,
        FEATURE_HISTORY_DAYS: 365,
        FEATURE_EXPORTS: True,
        FEATURE_ORG_SUPPORT: True,
        FEATURE_CUSTOM_WEIGHTING: False,
        FEATURE_SUPPORT_LEVEL: SUPPORT_PRIORITY
    },
    Plan.CHURCH: {
        FEATURE_USERS: float('inf'),
        FEATURE_ADMINS: float('inf'),
        FEATURE_ASSESSMENTS_PER_MONTH: float('inf'),
        FEATURE_HISTORY_DAYS: float('inf'),
        FEATURE_EXPORTS: True,
        FEATURE_ORG_SUPPORT: True,
        FEATURE_CUSTOM_WEIGHTING: True,
        FEATURE_SUPPORT_LEVEL: SUPPORT_PRIORITY
    }
}

def get_plan_features(plan_name: str) -> Dict[str, Any]:
    """Retrieve features for a given plan, defaulting to FREE if unknown."""
    try:
        plan = Plan(plan_name.lower())
    except ValueError:
        plan = Plan.FREE
    return TIER_FEATURES[plan]

def resolve_limit(plan_name: str, feature: str) -> Any:
    """Get a specific limit for a plan."""
    features = get_plan_features(plan_name)
    return features.get(feature, 0)
