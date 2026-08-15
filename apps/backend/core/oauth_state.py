"""Re-export OAuth state policy from domain/policies/oauth_state.py.

Moved to domain/policies per SYSTEM_ARCHITECTURE §0 and ROADMAP §13.4 Recommendation 5.
"""

from domain.policies.oauth_state import (
    _STATE_AUDIENCE,
    DEFAULT_RETURN_KEY,
    RETURN_PATHS,
    STATE_TTL_MINUTES,
    InvalidOAuthState,
    OAuthStatePayload,
    create_oauth_state,
    verify_oauth_state,
)

__all__ = [
    "_STATE_AUDIENCE",
    "DEFAULT_RETURN_KEY",
    "RETURN_PATHS",
    "STATE_TTL_MINUTES",
    "InvalidOAuthState",
    "OAuthStatePayload",
    "create_oauth_state",
    "verify_oauth_state",
]
