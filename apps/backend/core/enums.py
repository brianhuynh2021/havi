"""Public enums — nguồn sự thật của contract giữa backend và frontend.

Giá trị lấy từ docs/handoff/HANDOFF.md và docs/architecture/TECHNICAL_SPEC.md.
Đổi giá trị ở đây = đổi OpenAPI = frontend phải sinh lại client.
"""

from enum import StrEnum


class Industry(StrEnum):
    """6 ô trong bước 1 của Onboarding."""

    SPA = "spa"
    FOOD_BEVERAGE = "food_beverage"
    REAL_ESTATE = "real_estate"
    PROFESSIONAL = "professional"
    ONLINE_SHOP = "online_shop"
    OTHER = "other"


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    MARKETER = "marketer"
    REVIEWER = "reviewer"
    SALES = "sales"


class Plan(StrEnum):
    """Bảng giá landing page: 0đ 14 ngày / Tiệm Nhỏ 299K / Toàn Diện 599K."""

    TRIAL = "trial"
    TIEM_NHO = "tiem_nho"
    TOAN_DIEN = "toan_dien"


class Channel(StrEnum):
    """Kênh đầu ra của content — mỗi kênh 1 adapter, lõi AI không biết kênh."""

    FACEBOOK_PAGE = "facebook_page"
    GOOGLE_BUSINESS = "google_business"
    ZALO_OA = "zalo_oa"
    REELS = "reels"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    EMAIL = "email"


class Platform(StrEnum):
    """Nền tảng có OAuth connection (tập con của Channel)."""

    FACEBOOK = "facebook"
    GOOGLE_BUSINESS = "google_business"
    ZALO_OA = "zalo_oa"


class PublishMode(StrEnum):
    """Toggle "Chế độ đăng bài", lưu theo workspace. Không áp dụng cho reply khách."""

    REVIEW_FIRST = "review_first"
    FULL_AUTO = "full_auto"


class ContentStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class ContentJobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DRAFTS_READY = "drafts_ready"
    FAILED = "failed"


class PublishFailureKind(StrEnum):
    """Phân loại lỗi publish để quyết định có retry hay không."""

    TEMPORARY = "temporary"
    AUTH_PERMISSION = "auth_permission"
    VALIDATION_PERMANENT = "validation_permanent"


class RawInputKind(StrEnum):
    """Chip loại liệu thô trong tab Tạo nội dung."""

    PHOTO = "photo"
    VOICE = "voice"
    TEXT = "text"
    SALES_WEBHOOK = "sales_webhook"


class MediaType(StrEnum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class MediaStatus(StrEnum):
    RAW = "raw"
    USED = "used"
    ARCHIVED = "archived"


class ConnectionStatus(StrEnum):
    CONNECTED = "connected"
    EXPIRED = "expired"
    REVOKED = "revoked"


class InboxItemType(StrEnum):
    COMMENT = "comment"
    REVIEW = "review"
    MESSAGE = "message"


class InboxItemStatus(StrEnum):
    NEW = "new"
    DRAFTED = "drafted"
    SENT = "sent"


class LeadSource(StrEnum):
    FANPAGE = "fanpage"
    MAPS = "maps"
    GROUP = "group"
    CRM = "crm"


class LeadStage(StrEnum):
    """Pipeline kanban trong Settings/CRM (TECHNICAL_SPEC §8)."""

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    WON = "won"
    LOST = "lost"


class LeadReplyStatus(StrEnum):
    """Status pill trên lead card ở tab Khách tiềm năng (HANDOFF State Management).

    Tách khỏi LeadStage: đây là trạng thái của câu trả lời, không phải giai đoạn bán hàng.
    """

    NEW = "new"
    AUTO_REPLIED = "auto_replied"
    AWAITING_APPROVAL = "awaiting_approval"
    SENT = "sent"
    BOOKED = "booked"


class CrmChannel(StrEnum):
    ZALO = "zalo"
    EMAIL = "email"


class CrmMessageStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    SENT = "sent"


class SubscriptionStatus(StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
