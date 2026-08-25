"""Public enums — nguồn sự thật của contract giữa backend và frontend.

Giá trị lấy từ docs/handoff/HANDOFF.md và docs/architecture/TECHNICAL_SPEC.md.
Đổi giá trị ở đây = đổi OpenAPI = frontend phải sinh lại client.
"""

from enum import StrEnum


class Industry(StrEnum):
    """8 nhóm ngành kinh doanh toàn diện trong bước 1 của Onboarding."""

    SPA = "spa"
    FOOD_BEVERAGE = "food_beverage"
    RETAIL_SHOP = "retail_shop"
    ONLINE_SHOP = "online_shop"  # backward compatibility alias
    EDUCATION = "education"
    LOCAL_SERVICE = "local_service"
    REAL_ESTATE = "real_estate"
    PROFESSIONAL = "professional"
    OTHER = "other"


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    MARKETER = "marketer"
    REVIEWER = "reviewer"
    SALES = "sales"


class Plan(StrEnum):
    """Bảng giá: 0đ 7 ngày / Khởi Nghiệp 189K / Chuyên Nghiệp 369K / Chuỗi Doanh Nghiệp 799K."""

    TRIAL = "trial"
    TIEM_NHO = "tiem_nho"
    TOAN_DIEN = "toan_dien"
    DOANH_NGHIEP = "doanh_nghiep"


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
    DISMISSED = "dismissed"


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
    # Nền tảng có thể đã nhận request nhưng Havi không nhận được response.
    # Tuyệt đối không retry tự động vì có thể tạo bài trùng.
    PENDING_RECONCILIATION = "pending_reconciliation"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    # Hết số lần thử hoặc lỗi không thể tự sửa. Không retry tự động nữa — chờ
    # người bấm thử lại, để một bài hỏng không đập API nền tảng mãi.
    DEAD_LETTER = "dead_letter"


class PublishFailureKind(StrEnum):
    """Phân loại lỗi publish để quyết định có retry hay không."""

    TEMPORARY = "temporary"
    AMBIGUOUS_OUTCOME = "ambiguous_outcome"
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


class VideoPostStatus(StrEnum):
    """Đường đi của một clip đã tải lên, từ lúc nhận tới lúc Facebook xác nhận.

    Mỗi trạng thái là một điều đã *xảy ra thật*, không phải một ý định:

    * `READY_FOR_REVIEW` — clip đã lên storage và đã qua kiểm ràng buộc kênh
      (khung hình, thời lượng, tiếng). Havi không đụng vào file.
    * `APPROVED` — chủ tiệm đã xem lại và đồng ý đăng.
    * `PUBLISHING` — đã gửi bytes sang Facebook, chưa biết kết quả.
    * `VERIFYING` — Facebook nhận rồi, đang đọc lại để lấy `external_post_id`.
    * `PUBLISHED` — đã đọc lại và xác nhận bài có thật trên Trang.

    Ba nhánh lỗi tách nhau vì cách xử lý khác hẳn nhau: `FAILED` thử lại được,
    `FAILED_PERMANENT` thì không (clip hỏng, kênh mất kết nối vĩnh viễn),
    `PENDING_RECONCILIATION` là "đã gửi Facebook nhưng mất dấu" — tuyệt đối
    không tự đăng lại, phải đi kiểm tra xem bài đã lên chưa.
    """

    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    PUBLISHING = "publishing"
    VERIFYING = "verifying"
    PUBLISHED = "published"
    FAILED = "failed"
    FAILED_PERMANENT = "failed_permanent"
    PENDING_RECONCILIATION = "pending_reconciliation"
    CANCELLED = "cancelled"


class VideoPublishAttemptStatus(StrEnum):
    """Vòng đời một lần gửi video sang nền tảng.

    `PENDING` là trạng thái nguy hiểm nhất và là lý do bảng này tồn tại: đã gửi
    đi nhưng chưa biết kết quả. Ràng buộc unique ở Postgres chặn không cho tạo
    lần gửi thứ hai khi còn một lần `PENDING` — đó là lớp chặn đăng trùng thật
    sự, không phải cái `if` trong service.
    """

    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"
    #: Đã gửi, mất dấu kết quả. Phải đối soát, tuyệt đối không gửi lại.
    AMBIGUOUS = "ambiguous"




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
    FAILED = "failed"
    #: Chủ tiệm bấm "Bỏ qua". Phải là trạng thái riêng chứ không dùng lại `SENT`:
    #: gộp hai thứ vào một thì báo cáo đếm tin đã bỏ qua thành tin đã trả lời, và
    #: không cách nào tách lại sau này.
    DISMISSED = "dismissed"


class LeadSource(StrEnum):
    FANPAGE = "fanpage"
    MAPS = "maps"
    GOOGLE_BUSINESS = "google_business"
    TIKTOK = "tiktok"
    INBOX = "inbox"
    GROUP = "group"
    CRM = "crm"
    POS = "pos"


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


class CrmNudgeType(StrEnum):
    INACTIVE_30_DAYS = "inactive_30_days"
    FOLLOWUP_14_DAYS = "followup_14_days"
    BIRTHDAY_SPECIAL = "birthday_special"


class CrmMessageStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    SENT = "sent"
    DISMISSED = "dismissed"


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


class GoalCategory(StrEnum):
    """8 nhóm mục tiêu cơ bản theo Havi 3.0 (§26.7)."""

    ACQUIRE_CUSTOMERS = "acquire_customers"
    SELL_OFFER = "sell_offer"
    LAUNCH = "launch"
    RECRUIT = "recruit"
    DELIVER_PROJECT = "deliver_project"
    LEARN_SKILL = "learn_skill"
    GROW_AUDIENCE = "grow_audience"
    IMPROVE_OPERATIONS = "improve_operations"
    OTHER = "other"


class GoalStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class RoadmapStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class TaskOwnerType(StrEnum):
    USER = "user"
    HAVI = "havi"
    COLLABORATIVE = "collaborative"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class ReviewDecision(StrEnum):
    CONTINUE = "continue"
    IMPROVE = "improve"
    PIVOT = "pivot"
    PAUSE = "pause"
    STOP = "stop"
