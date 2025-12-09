"""Authorization (authZ) system for API tiers and permissions."""

from enum import Enum
from typing import Set, List
from dataclasses import dataclass


class APITier(Enum):
    """API access tiers defining what endpoints a key can access."""
    BASIC = "basic"  # Original/legacy endpoints
    PREMIUM = "premium"  # Advanced features
    ENTERPRISE = "enterprise"  # All features


# Define which endpoints belong to which tier
TIER_PERMISSIONS = {
    APITier.BASIC: {
        # All original endpoints that current keys have access to
        "GET /",
        "GET /api/v1/health",
        "GET /privacy",
        "POST /api/v1/predictions/calculate",
        "POST /api/v1/predictions/week-analysis",
        "POST /api/v1/scout/players",
        "GET /api/v1/scout/teams",
        "POST /api/v1/scout/free-agents",
        "POST /api/v1/team/{team_id}",
        "POST /api/v1/team/{team_id}/roster",
        "POST /api/v1/players-playing/{scoring_period}",
        "POST /api/v1/scoreboard/{week_index}",
    },
    APITier.PREMIUM: {
        # All BASIC endpoints plus premium features
        *[], # Add premium endpoints here in the future
    },
    APITier.ENTERPRISE: {
        # All endpoints (no restrictions)
        "*",  # Wildcard means all endpoints
    }
}

# Add PREMIUM permissions inherit from BASIC
TIER_PERMISSIONS[APITier.PREMIUM].update(TIER_PERMISSIONS[APITier.BASIC])


@dataclass
class AuthZPolicy:
    """Authorization policy for an API key."""
    tier: APITier
    allowed_endpoints: Set[str]
    
    @classmethod
    def for_tier(cls, tier: APITier) -> "AuthZPolicy":
        """Create an AuthZPolicy for a given tier."""
        endpoints = TIER_PERMISSIONS.get(tier, set())
        return cls(tier=tier, allowed_endpoints=endpoints)


def check_endpoint_access(tier: APITier, method: str, path: str) -> bool:
    """Check if a tier has access to an endpoint.
    
    Args:
        tier: The API tier to check
        method: HTTP method (GET, POST, etc.)
        path: The endpoint path (e.g., /api/v1/predictions/calculate)
    
    Returns:
        True if the tier has access, False otherwise
    """
    # Get permissions for the tier
    permissions = TIER_PERMISSIONS.get(tier, set())
    
    # If tier has wildcard access (enterprise), allow everything
    if "*" in permissions:
        return True
    
    # Check exact endpoint match
    endpoint = f"{method} {path}"
    
    # Try exact match first
    if endpoint in permissions:
        return True
    
    # Try pattern matching for parameterized endpoints
    # e.g., POST /api/v1/team/{team_id} matches POST /api/v1/team/1
    for perm in permissions:
        if _endpoint_matches(endpoint, perm):
            return True
    
    return False


def _endpoint_matches(endpoint: str, pattern: str) -> bool:
    """Check if an endpoint matches a pattern with parameters.
    
    Examples:
        "POST /api/v1/team/1" matches pattern "POST /api/v1/team/{team_id}"
        "POST /api/v1/scoreboard/5" matches pattern "POST /api/v1/scoreboard/{week_index}"
    """
    endpoint_parts = endpoint.split("/")
    pattern_parts = pattern.split("/")
    
    if len(endpoint_parts) != len(pattern_parts):
        return False
    
    for ep, pat in zip(endpoint_parts, pattern_parts):
        # Check if pattern is a parameter placeholder
        if pat.startswith("{") and pat.endswith("}"):
            # Parameter matches anything
            continue
        elif ep != pat:
            return False
    
    return True
