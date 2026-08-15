"""Re-export phone normalization policy from domain/policies/phone.py.

Moved to domain/policies per SYSTEM_ARCHITECTURE §0 and ROADMAP §13.4 Recommendation 5.
"""

from domain.policies.phone import (
    InvalidPhoneNumber,
    normalize_vietnamese_phone,
)

__all__ = [
    "InvalidPhoneNumber",
    "normalize_vietnamese_phone",
]
