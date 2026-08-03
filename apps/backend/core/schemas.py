"""Pydantic models dùng chung cho mọi router. Đây là contract xuất ra OpenAPI."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.enums import (
    Channel,
    ConnectionStatus,
    ContentJobStatus,
    ContentStatus,
    CrmChannel,
    CrmMessageStatus,
    InboxItemStatus,
    InboxItemType,
    Industry,
    LeadReplyStatus,
    LeadSource,
    LeadStage,
    MediaStatus,
    MediaType,
    Plan,
    Platform,
    PublishMode,
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


class OtpRequest(HaviModel):
    """SĐT + OTP là kênh chính (qua Zalo/SMS); email + mật khẩu là phụ."""

    phone: str = Field(min_length=9, max_length=15, examples=["0901234567"])


class OtpVerify(HaviModel):
    phone: str = Field(min_length=9, max_length=15)
    code: str = Field(min_length=6, max_length=6, examples=["111111"])


class SignUpRequest(HaviModel):
    """Đăng ký chỉ cần tên + SĐT; email/mật khẩu thêm sau trong Cài đặt."""

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=9, max_length=15)


class EmailLoginRequest(HaviModel):
    email: str
    password: str


class TokenPair(HaviModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    active_workspace_id: UUID | None = None
    needs_onboarding: bool = False


class RefreshRequest(HaviModel):
    refresh_token: str


class CurrentUser(HaviModel):
    id: UUID
    name: str
    phone: str
    email: str | None = None
    active_workspace_id: UUID | None = None


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
    phone: str = Field(min_length=9, max_length=15)
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
    type: MediaType
    tags: list[str] = Field(default_factory=list)
    status: MediaStatus
    uploaded_at: datetime


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


class ContentJobCreate(HaviModel):
    """Nút "Để Havi viết cho chị" — 1 job, 1 lần gọi LLM, nhiều đầu ra."""

    raw_inputs: list[RawInput] = Field(min_length=1)


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
    scheduled_at: datetime | None = None


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
    """Nút "Duyệt & đăng hết" trên thanh duyệt nhanh."""

    content_item_ids: list[UUID] = Field(min_length=1)


class BulkApproveResult(HaviModel):
    approved: list[UUID]
    rejected: list["BulkApproveFailure"]


class BulkApproveFailure(HaviModel):
    content_item_id: UUID
    reason: str


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


# --- Inbox ------------------------------------------------------------------


class InboxItem(HaviModel):
    id: UUID
    workspace_id: UUID
    platform: Platform
    type: InboxItemType
    content: str
    author_name: str
    sentiment: str | None = None
    ai_suggested_reply: str | None = None
    status: InboxItemStatus
    created_at: datetime


class InboxReplyRequest(HaviModel):
    """Không có full_auto: luôn phải bấm gửi."""

    text: str = Field(min_length=1)


# --- Leads ------------------------------------------------------------------


class Lead(HaviModel):
    id: UUID
    workspace_id: UUID
    name: str
    phone: str | None = None
    source: LeadSource
    stage: LeadStage
    reply_status: LeadReplyStatus
    message: str | None = None
    suggested_reply: str | None = None
    notes: str | None = None
    created_at: datetime


class LeadCreate(HaviModel):
    name: str
    phone: str | None = None
    source: LeadSource
    message: str | None = None


class LeadUpdate(HaviModel):
    name: str | None = None
    phone: str | None = None
    stage: LeadStage | None = None
    notes: str | None = None


class CrmMessage(HaviModel):
    id: UUID
    lead_id: UUID
    channel: CrmChannel
    draft_text: str
    status: CrmMessageStatus
    created_at: datetime


# --- Analytics --------------------------------------------------------------


class AnalyticsSummary(HaviModel):
    """Đo bằng khách hỏi giá / khách đến tiệm / khách quay lại — không phải like/reach."""

    price_inquiries: int
    walk_ins: int
    returning_customers: int
    published_posts: int
    new_leads: int
    lead_won_rate: float
    change_vs_previous_period: dict[str, float] = Field(default_factory=dict)


class ChannelAttribution(HaviModel):
    channel: Channel
    customers: int
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


class Invoice(HaviModel):
    id: UUID
    workspace_id: UUID
    amount_vnd: int
    status: str
    issued_at: datetime


BrandProfile.model_rebuild()
BulkApproveResult.model_rebuild()
