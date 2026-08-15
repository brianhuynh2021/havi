"""Domain policies — Pure business logic with zero framework or infrastructure dependencies."""

from domain.policies.content_output import output_json_schema, parse_and_validate
from domain.policies.content_state import (
    MAX_PUBLISH_RETRIES,
    RESCHEDULABLE_STATUSES,
    TERMINAL_STATUSES,
    InvalidTransitionError,
    allowed_transitions,
    assert_transition,
    can_transition,
    initial_status,
    next_after_failure,
)
from domain.policies.oauth_state import (
    DEFAULT_RETURN_KEY,
    RETURN_PATHS,
    STATE_TTL_MINUTES,
    InvalidOAuthState,
    OAuthStatePayload,
    create_oauth_state,
    verify_oauth_state,
)
from domain.policies.phone import InvalidPhoneNumber, normalize_vietnamese_phone
from domain.policies.provider_router import AllProvidersFailed, ProviderRouter
from domain.policies.quota import (
    MONTHLY_TOKEN_QUOTA,
    QuotaExceeded,
    QuotaStatus,
    month_start_utc,
    next_month_start_utc,
    quota_for,
)
from domain.policies.quota import (
    evaluate as evaluate_quota,
)
from domain.policies.rate_limits import (
    AUTH_LOGIN,
    AUTH_PASSWORD_RESET,
    CONTENT_JOB,
    MEDIA_UPLOAD_TICKET,
)
from domain.policies.scheduling import (
    GOLDEN_HOURS,
    VIETNAM_TZ,
    next_golden_hour,
)
from domain.policies.subscription import (
    MONTHLY_PRICE_VND,
    TRIAL_DAYS,
    PlanChangeNotAllowed,
    SubscriptionState,
    check_plan_change,
    price_for,
    state_for,
    trial_end_for,
)
from domain.policies.video_constraints import (
    VIDEO_REQUIREMENTS,
    VideoRequirement,
    check_video_for_channel,
    eligible_channels,
)
from domain.policies.video_edit_plan import (
    EditPlan,
    VideoAudioConfig,
    VideoCaption,
    VideoCut,
    default_edit_plan_for_short_form,
    validate_edit_plan,
)

__all__ = [
    "AUTH_LOGIN",
    "AUTH_PASSWORD_RESET",
    "AllProvidersFailed",
    "CONTENT_JOB",
    "DEFAULT_RETURN_KEY",
    "EditPlan",
    "GOLDEN_HOURS",
    "InvalidOAuthState",
    "InvalidPhoneNumber",
    "InvalidTransitionError",
    "MAX_PUBLISH_RETRIES",
    "MEDIA_UPLOAD_TICKET",
    "MONTHLY_PRICE_VND",
    "MONTHLY_TOKEN_QUOTA",
    "OAuthStatePayload",
    "PlanChangeNotAllowed",
    "ProviderRouter",
    "QuotaExceeded",
    "QuotaStatus",
    "RESCHEDULABLE_STATUSES",
    "RETURN_PATHS",
    "STATE_TTL_MINUTES",
    "SubscriptionState",
    "TERMINAL_STATUSES",
    "TRIAL_DAYS",
    "VIDEO_REQUIREMENTS",
    "VIETNAM_TZ",
    "VideoAudioConfig",
    "VideoCaption",
    "VideoCut",
    "VideoRequirement",
    "allowed_transitions",
    "assert_transition",
    "can_transition",
    "check_plan_change",
    "check_video_for_channel",
    "create_oauth_state",
    "default_edit_plan_for_short_form",
    "derive_status",
    "eligible_channels",
    "evaluate_quota",
    "initial_status",
    "month_start_utc",
    "next_after_failure",
    "next_golden_hour",
    "next_month_start_utc",
    "normalize_vietnamese_phone",
    "output_json_schema",
    "parse_and_validate",
    "price_for",
    "quota_for",
    "state_for",
    "trial_end_for",
    "validate_edit_plan",
    "verify_oauth_state",
]
