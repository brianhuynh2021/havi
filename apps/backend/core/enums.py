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
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


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


class PublishStatus(StrEnum):
    """Vòng đời một publish job.

    Tách khỏi `ContentStatus`: một content item có thể sinh nhiều publish job
    (đăng lại sau khi sửa, đăng nhiều kênh), và job có vòng đời riêng với retry
    và dead-letter mà content item không cần biết.
    """

    PENDING = "pending"
    IN_FLIGHT = "in_flight"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    # Hết số lần thử hoặc lỗi không thể tự sửa. Không retry tự động nữa — chờ
    # người bấm thử lại, để một bài hỏng không đập API nền tảng mãi.
    DEAD_LETTER = "dead_letter"


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
    """`PENDING` = đã cấp upload ticket nhưng client chưa PUT xong.

    Cần trạng thái này vì client upload thẳng lên object storage, API không biết
    upload có thành công không cho tới khi client gọi `/media/{id}/complete`.
    Không có nó thì mọi ticket cấp ra đều trông như file đã có thật.
    """

    PENDING = "pending"
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
    #: Chủ tiệm bấm "Bỏ qua". Phải là trạng thái riêng chứ không dùng lại `SENT`:
    #: gộp hai thứ vào một thì báo cáo đếm tin đã bỏ qua thành tin đã trả lời, và
    #: không cách nào tách lại sau này.
    DISMISSED = "dismissed"


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


class InvoiceStatus(StrEnum):
    """Vòng đời một hoá đơn.

    `PENDING` là trạng thái duy nhất hoá đơn đạt tới hôm nay: chưa nối cổng thanh
    toán nào nên không có gì xác nhận được đã thu tiền. Chỉ adapter cổng thanh
    toán mới được chuyển sang `PAID` — không có đường nào khác trong code làm
    việc đó, vì đánh dấu đã trả mà chưa nhận tiền là ghi sai sổ.
    """

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    VOID = "void"


class OAuthReturnTarget(StrEnum):
    """Màn hình đưa người dùng về sau khi cấp quyền OAuth xong.

    Enum chứ không phải URL: giá trị lạ bị chặn ngay ở 422, và callback không bao
    giờ redirect ra ngoài domain của Havi được. Giá trị phải khớp khoá trong
    `core.oauth_state.RETURN_PATHS`.
    """

    ONBOARDING = "onboarding"
    SETTINGS = "settings"
