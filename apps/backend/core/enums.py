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


class OrganizationRole(StrEnum):
    """Vai ở cấp doanh nghiệp — cố tình chỉ có hai.

    Quyền chi tiết (ai soạn, ai duyệt, ai trả lời khách) nằm ở `WorkspaceRole`,
    tức ở từng thương hiệu. Nhân đôi bảng quyền ở cấp tổ chức chỉ tạo ra hai
    nguồn sự thật cho cùng một câu hỏi.
    """

    #: Tạo/xoá thương hiệu, mời người vào tổ chức.
    OWNER = "owner"
    #: Thuộc tổ chức; quyền thật sự phụ thuộc vai ở từng workspace.
    MEMBER = "member"


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    MARKETER = "marketer"
    REVIEWER = "reviewer"
    SALES = "sales"


class BillingCycle(StrEnum):
    """Chu kỳ thanh toán.

    Gói năm tồn tại vì VietQR không có auto-renew: mỗi tháng khách phải chủ động
    quyết định trả tiếp. Gói năm đổi mười hai quyết định thành một — đối sách
    chống churn mạnh nhất làm được mà không cần card-on-file.
    """

    MONTHLY = "monthly"
    ANNUAL = "annual"


class Plan(StrEnum):
    """Bảng giá: 0đ 7 ngày / Khởi Nghiệp 189K / Chuyên Nghiệp 369K / Chuỗi Doanh Nghiệp 799K."""

    TRIAL = "trial"
    TIEM_NHO = "tiem_nho"
    TOAN_DIEN = "toan_dien"
    DOANH_NGHIEP = "doanh_nghiep"


class ContentKind(StrEnum):
    """Loại nội dung người dùng chọn ở bước đầu của luồng Đăng bài.

    Quyết định **kênh nào nhận được** — TikTok và YouTube chỉ nhận video, nên bộ
    chọn kênh là hàm của giá trị này. Xem `domain/policies/channel_capabilities.py`.
    """

    POST = "post"
    VIDEO = "video"


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
