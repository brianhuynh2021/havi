"""Pydantic models dùng chung cho mọi router. Đây là contract xuất ra OpenAPI."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from core.enums import (
    Channel,
    ConnectionStatus,
    ContentJobStatus,
    ContentStatus,
    InboxItemStatus,
    InboxItemType,
    Industry,
    MediaStatus,
    MediaType,
    Plan,
    Platform,
    PublishFailureKind,
    PublishMode,
    PublishStatus,
    RawInputKind,
    SubscriptionStatus,
    WorkspaceRole,
)


class HaviModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=False)


class Page[T](HaviModel):
    items: list[T]
    total: int
    limit: int = 50
    offset: int = 0


# --- Auth -------------------------------------------------------------------


MIN_PASSWORD_LENGTH = 8


class SignUpRequest(HaviModel):
    """Email + mật khẩu là kênh duy nhất để tạo tài khoản.

    Không dùng SĐT: OTP SMS ở VN tốn phí thật nên ăn vào margin gói 299K/tháng,
    và chủ tiệm e dè đưa số vì spam. SĐT thêm sau trong Cài đặt, chỉ để Zalo OA.
    """

    name: str = Field(min_length=1, max_length=120, examples=["Nguyễn Thu Hương"])
    email: EmailStr = Field(examples=["huong@spaannhien.vn"])
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)


class EmailLoginRequest(HaviModel):
    email: EmailStr
    password: str


class SocialLoginRequest(HaviModel):
    provider: str = Field(examples=["google", "facebook"])
    email: EmailStr
    name: str | None = None


class PasswordResetRequest(HaviModel):
    """Bước 1 màn "Quên mật khẩu" — gửi mã 6 số qua email."""

    email: EmailStr


class PasswordResetConfirm(HaviModel):
    """Bước 2 — nhập mã trong email + mật khẩu mới."""

    email: EmailStr
    code: str = Field(min_length=6, max_length=6, examples=["111111"])
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=128)


class PhoneUpdateRequest(HaviModel):
    """SĐT tuỳ chọn — chỉ để nhận bản nháp/nhắc duyệt qua Zalo OA, không để đăng nhập."""

    phone: str = Field(min_length=9, max_length=15, examples=["0901234567"])


class TokenPair(HaviModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    active_workspace_id: UUID | None = None
    needs_onboarding: bool = False


class RefreshRequest(HaviModel):
    refresh_token: str | None = None


class CurrentUser(HaviModel):
    id: UUID
    name: str
    email: str
    phone: str | None = None
    active_workspace_id: UUID | None = None

    #: Vai trong workspace đang active, và các quyền suy ra từ vai đó.
    #:
    #: Frontend cần chúng để **không hiện nút người dùng không bấm được**. Đây
    #: thuần tuý là trải nghiệm: backend vẫn kiểm lại ở từng endpoint, vì ẩn nút
    #: không phải là phân quyền — ai cũng gọi thẳng API được.
    #:
    #: `None` khi tài khoản chưa chọn workspace.
    role: WorkspaceRole | None = None
    permissions: list[str] = Field(default_factory=list)


# --- Organization -----------------------------------------------------------


class Organization(HaviModel):
    """Doanh nghiệp sở hữu một hoặc nhiều workspace (thương hiệu / chi nhánh)."""

    id: UUID
    name: str
    owner_user_id: UUID
    created_at: datetime


class OrganizationCreate(HaviModel):
    name: str = Field(min_length=1, max_length=160, examples=["Chuỗi Spa An Nhiên"])


class OrganizationBrand(HaviModel):
    """Một workspace nhìn từ cấp tổ chức — chỉ những gì cần để chọn và điều hướng.

    Không trả `plan`, `publish_mode`, hay số liệu: màn chọn thương hiệu chỉ cần
    trả lời "vào cái nào", còn chi tiết thuộc về chính workspace đó.
    """

    id: UUID
    name: str
    industry: Industry
    created_at: datetime


class OrganizationWithBrands(HaviModel):
    organization: Organization
    brands: list[OrganizationBrand]


# --- Workspace --------------------------------------------------------------


class Workspace(HaviModel):
    id: UUID
    name: str
    industry: Industry
    plan: Plan
    publish_mode: PublishMode
    created_at: datetime


class WorkspaceCreate(HaviModel):
    name: str = Field(min_length=1, max_length=160)
    industry: Industry


class WorkspaceUpdate(HaviModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    industry: Industry | None = None
    publish_mode: PublishMode | None = None


class WorkspaceMember(HaviModel):
    user_id: UUID
    name: str
    role: WorkspaceRole


class WorkspaceMemberInvite(HaviModel):
    """Mời bằng email, không bằng SĐT: SĐT giờ là field tuỳ chọn nên phần lớn
    tài khoản không có, mời bằng SĐT sẽ luôn không tìm thấy người."""

    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.MARKETER


# --- Brand profile ----------------------------------------------------------


class BrandProfile(HaviModel):
    """Input bắt buộc cho mọi prompt chế bản — worker đọc từ đây, không hardcode."""

    workspace_id: UUID
    industry: Industry
    tone: str = Field(default="", examples=["thân thiện, gần gũi"])
    banned_claims: list[str] = Field(
        default_factory=list, examples=[["chắc chắn tăng giá", "cam kết 100%"]]
    )
    faq: list["FaqEntry"] = Field(default_factory=list)
    logo_url: str | None = None
    brand_colors: list[str] = Field(default_factory=list)


class FaqEntry(HaviModel):
    """Chỉ câu chủ đã duyệt sẵn mới được trả lời tự động 24/7."""

    question: str
    answer: str
    approved: bool = False


class BrandProfileUpdate(HaviModel):
    tone: str | None = None
    banned_claims: list[str] | None = None
    faq: list[FaqEntry] | None = None
    logo_url: str | None = None
    brand_colors: list[str] | None = None


# --- Media ------------------------------------------------------------------


class MediaAsset(HaviModel):
    id: UUID
    workspace_id: UUID
    url: str
    filename: str
    content_type: str
    type: MediaType
    tags: list[str] = Field(default_factory=list)
    status: MediaStatus
    size_bytes: int | None = None
    # None khi status là `pending` — client chưa gọi /media/{id}/complete.
    uploaded_at: datetime | None = None

    # Chỉ có với video, đọc bằng ffprobe lúc complete. None = chưa/không đọc
    # được, KHÔNG phải bằng 0 — UI phải phân biệt "chưa biết" với "không có".
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None
    aspect_ratio: str | None = None
    has_audio: bool | None = None
    #: Ảnh bìa trích từ clip lúc complete. None = chưa/không lấy được, UI hiện
    #: placeholder thay vì khoảng trắng.
    thumbnail_url: str | None = None
    #: Kênh video clip này đăng được, suy từ thông số trên
    #: (`domain/policies/video_constraints.py`). Rỗng với ảnh/audio.
    eligible_channels: list[Channel] = Field(default_factory=list)


class MediaUploadTicket(HaviModel):
    """Client upload thẳng lên object storage; API chỉ lưu metadata."""

    asset_id: UUID
    upload_url: str
    fields: dict[str, str] = Field(default_factory=dict)
    expires_at: datetime


class MediaUploadRequest(HaviModel):
    filename: str
    content_type: str
    type: MediaType


class MediaUpdate(HaviModel):
    tags: list[str] | None = None
    status: MediaStatus | None = None


# --- Content ----------------------------------------------------------------


class RawInput(HaviModel):
    kind: RawInputKind
    text: str | None = None
    media_asset_id: UUID | None = None
    preview_url: str | None = None


class ContentJobCreate(HaviModel):
    """Nút "Để Havi viết bài" — 1 job, 1 lần gọi LLM, nhiều đầu ra."""

    raw_inputs: list[RawInput] = Field(min_length=1)
    target_channels: list[Channel] | None = None


class ContentJob(HaviModel):
    id: UUID
    workspace_id: UUID
    status: ContentJobStatus
    raw_inputs: list[RawInput]
    content_item_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime


class ContentItem(HaviModel):
    id: UUID
    workspace_id: UUID
    job_id: UUID | None
    channel: Channel
    kind: str = Field(examples=["Bài ảnh", "Bài đánh giá", "Video ngắn"])
    text: str
    media_note: str | None = None
    media_url: str | None = None
    status: ContentStatus
    version_no: int = 1
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    created_at: datetime


class ContentItemUpdate(HaviModel):
    """Sửa text tạo version mới, không ghi đè."""

    text: str | None = None
    media_note: str | None = None
    media_url: str | None = None
    scheduled_at: datetime | None = None


class GenerateImageRequest(HaviModel):
    prompt: str | None = None
    style: str | None = Field(
        default="photorealistic", description="photorealistic | 3d_studio | cinematic"
    )


class GenerateImageResponse(HaviModel):
    media_url: str
    prompt_used: str


class GenerateVideoRequest(HaviModel):
    target_aspect_ratio: str = Field(default="9:16", description="9:16 | 1:1 | 16:9")
    title: str | None = None
    #: Clip thật đã tải lên. Bắt buộc — bộ dựng cắt từ clip chứ không sinh hình.
    source_media_id: UUID | None = None
    target_duration_seconds: float | None = Field(default=None, ge=3, le=180)


class GenerateVideoResponse(HaviModel):
    media_url: str | None = None
    target_aspect_ratio: str = "9:16"
    status: str = "completed"


class ContentItemVersion(HaviModel):
    content_item_id: UUID
    version_no: int
    text: str
    edited_by: UUID | None
    edited_at: datetime


class ApproveRequest(HaviModel):
    scheduled_at: datetime | None = Field(
        default=None, description="Bỏ trống để Havi chọn khung giờ vàng."
    )


class BulkApproveRequest(HaviModel):
    """Duyệt cả loạt: đăng ngay, hoặc rải ra nhiều ngày.

    `content_item_ids` giữ nguyên thứ tự — bài đầu danh sách lên trước. Đó là
    cách chủ tiệm sắp xếp câu chuyện của tuần.
    """

    content_item_ids: list[UUID] = Field(min_length=1)
    publish_now: bool = Field(default=True, description="Đăng ngay lập tức thay vì rải lịch")
    posts_per_day: int = Field(
        default=1,
        ge=1,
        le=3,
        description=(
            "Số bài mỗi ngày khi rải lịch. Chỉ dùng khi publish_now=false. "
            "Tối đa 3 vì mỗi ngày chỉ có 3 khung giờ vàng (8h, 12h, 20h)."
        ),
    )


class BulkApproveResult(HaviModel):
    approved: list[UUID]
    rejected: list["BulkApproveFailure"]


class BulkApproveFailure(HaviModel):
    content_item_id: UUID
    reason: str


class BulkDismissRequest(HaviModel):
    """Nút "Xoá tất cả bản nháp" trên thanh tác vụ."""

    content_item_ids: list[UUID] = Field(min_length=1)


class BulkDismissResult(HaviModel):
    dismissed: list[UUID]


# --- Calendar ---------------------------------------------------------------


class CalendarDay(HaviModel):
    """Lịch là view trên content_item.scheduled_at, không phải bảng riêng."""

    date: str = Field(examples=["2026-08-03"])
    items: list[ContentItem]


class CalendarView(HaviModel):
    days: list[CalendarDay]


class RescheduleRequest(HaviModel):
    scheduled_at: datetime


# --- Connections ------------------------------------------------------------


class PlatformConnection(HaviModel):
    """Token mã hoá bằng TOKEN_ENCRYPTION_KEY — không bao giờ xuất ra response."""

    workspace_id: UUID
    platform: Platform
    status: ConnectionStatus
    account_name: str | None = None
    expires_at: datetime | None = None
    connected_by: UUID | None = None


class OAuthStartResponse(HaviModel):
    authorization_url: str
    state: str


# --- Quota ------------------------------------------------------------------


class TokenQuota(HaviModel):
    """Token đã dùng / trần tháng này.

    Đo bằng *token*, không bằng tiền: mỗi provider một đơn giá và giá LLM đổi
    liên tục, nên một bảng giá hardcode cho ra số nhìn như đúng mà sai — tệ hơn
    không có quota. Quy ra tiền làm ở chỗ định giá gói, không ở đây.
    """

    used: int
    limit: int
    remaining: int
    #: Đã qua 80% trần nhưng chưa bị chặn — UI cảnh báo trước, đừng để chủ tiệm
    #: chỉ biết khi đang cần đăng bài thì bị chặn.
    near_limit: bool
    exceeded: bool
    #: Mốc quota mở lại (đầu tháng sau theo giờ VN).
    resets_at: datetime


# --- Publish jobs -----------------------------------------------------------


class PublishJob(HaviModel):
    """Một lượt đăng bài. Frontend đọc để hiện trạng thái và nút "Thử lại".

    Không xuất `idempotency_key`: nó là chi tiết nội bộ, và cho phép người ngoài
    đoán khoá là mở đường tự tạo job trùng key.
    """

    id: UUID
    workspace_id: UUID
    content_item_id: UUID
    channel: Channel
    status: PublishStatus
    scheduled_at: datetime
    attempt_count: int
    next_attempt_at: datetime | None = None
    external_post_id: str | None = None
    published_at: datetime | None = None
    failure_kind: PublishFailureKind | None = None
    failure_detail: str | None = None


# --- Inbox ------------------------------------------------------------------


class InboxItem(HaviModel):
    id: UUID
    workspace_id: UUID
    platform: Platform
    type: InboxItemType
    content: str
    author_name: str
    recipient_id: str | None = None
    external_message_id: str | None = None
    sentiment: str | None = None
    ai_suggested_reply: str | None = None
    status: InboxItemStatus
    created_at: datetime


class InboxReplyRequest(HaviModel):
    """Không có full_auto: luôn phải bấm gửi."""

    text: str = Field(min_length=1)


# --- Analytics --------------------------------------------------------------


class AnalyticsSummary(HaviModel):
    """Bốn số liệu vận hành có nguồn dữ liệu trực tiếp trong Havi."""

    published_posts: int
    inbox_items: int
    replies_sent: int
    failed_posts: int
    change_vs_previous_period: dict[str, float] = Field(default_factory=dict)


class DashboardContentSummary(HaviModel):
    """Số liệu tối thiểu cho tab Tổng quan trước khi có engagement snapshot."""

    drafts: int
    pending_approval: int
    scheduled: int
    published: int
    failed: int
    broken_connections: int
    unhandled_inbox: int
    total_connections: int


class EventLogRecord(HaviModel):
    """Dòng event_log đã được scope theo workspace để support debug."""

    id: UUID
    workspace_id: UUID | None
    job_id: UUID | None
    request_id: str | None = None
    job_kind: str
    input_summary: str
    output_summary: str
    tokens_in: int
    tokens_out: int
    provider: str | None = None
    duration_ms: int
    error: str | None = None
    created_at: datetime


class OperationsProviderMetric(HaviModel):
    provider: str
    event_count: int
    error_count: int
    tokens_total: int


class OperationsPublishMetric(HaviModel):
    total: int
    succeeded: int
    dead_letter: int
    success_rate: float
    dead_letter_rate: float


class OperationsMetrics(HaviModel):
    """Số liệu nội bộ đủ để nhìn nhanh job có chậm/hỏng/tốn token không."""

    window_start: datetime
    window_end: datetime
    event_count: int
    error_count: int
    error_rate: float
    avg_duration_ms: int
    p95_duration_ms: int
    tokens_in: int
    tokens_out: int
    tokens_total: int
    job_count: int = 0
    avg_tokens_per_job: int = 0
    est_cost_per_job_vnd: int = 0
    approved_draft_count: int = 0
    est_cost_per_approved_draft_vnd: int = 0
    providers: list[OperationsProviderMetric]
    publish: OperationsPublishMetric


class ChannelAttribution(HaviModel):
    channel: Channel
    posts: int
    share: float
    note: str | None = None


class TimeseriesPoint(HaviModel):
    period: str = Field(examples=["2026-W31"])
    value: int


class AnalyticsTimeseries(HaviModel):
    metric: str
    points: list[TimeseriesPoint]


# --- Billing ----------------------------------------------------------------


class Subscription(HaviModel):
    workspace_id: UUID
    plan: Plan
    status: SubscriptionStatus
    current_period_end: datetime | None = None
    token_quota_used: int = 0
    token_quota_limit: int = 0


class ChangePlanRequest(HaviModel):
    plan: Plan


class Invoice(HaviModel):
    id: UUID
    workspace_id: UUID
    plan: Plan
    amount_vnd: int
    status: str
    issued_at: datetime


BrandProfile.model_rebuild()
BulkApproveResult.model_rebuild()
