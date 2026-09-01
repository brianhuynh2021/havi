"""Dependency dùng chung: auth context, workspace scope, và service injection.

Mọi endpoint (trừ /health và /auth/*) yêu cầu `Authorization: Bearer <JWT>` và bị
scope theo `active_workspace_id` — không cho leak chéo tenant.
"""

from functools import lru_cache
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from adapters.email.debug import DebugEmailSender
from adapters.email.smtp import SmtpEmailSender
from adapters.media.ffmpeg_processor import FFmpegVideoProcessor
from adapters.oauth.base import OAuthClientPort
from adapters.oauth.facebook import FacebookOAuthClient
from adapters.oauth.google_business import GoogleBusinessOAuthClient
from adapters.oauth.google_youtube import GoogleYouTubeOAuthClient
from adapters.oauth.tiktok import TikTokOAuthClient
from adapters.oauth.zalo import ZaloOAuthClient
from adapters.persistence.billing_repository import BillingRepository
from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.db import DbSessionDep
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.inbox_repository import InboxRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.organization_repository import OrganizationRepository
from adapters.persistence.otp_repository import OtpRepository
from adapters.persistence.outbox_repository import OutboxRepository
from adapters.persistence.publish_repository import PublishRepository
from adapters.persistence.refresh_session_repository import RefreshSessionRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.video_post_repository import VideoPostRepository
from adapters.persistence.workspace_member_repository import WorkspaceMemberRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from adapters.publishers.facebook_reply import FacebookReplyAdapter
from adapters.publishers.fake_reply import FakeReplyPublisher
from adapters.ratelimit import NullRateLimiter, RedisRateLimiter
from adapters.storage.object_storage import ObjectStorage
from application.services.approval_service import ApprovalService
from application.services.auth_service import AuthService
from application.services.billing_service import BillingService
from application.services.brand_profile_service import BrandProfileService
from application.services.connection_service import ConnectionService
from application.services.content_service import ContentService
from application.services.inbox_service import InboxService
from application.services.job_queue import JobQueue, OutboxJobQueue
from application.services.media_service import MediaService
from application.services.publish_service import PublishService
from application.services.video_post_service import VideoPostService
from application.services.video_publish_service import VideoPublishService
from application.services.voice_service import VoiceService
from application.services.workspace_service import WorkspaceService
from core.alerts import AlertSink, LoggingAlertSink
from core.config import Settings, get_settings
from core.enums import Platform, WorkspaceRole
from core.security import decode_access_token
from domain.ports.email import EmailSender
from domain.ports.reply_publisher import ReplyPublisherPort

bearer_scheme = HTTPBearer(auto_error=True)

SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache
def _email_sender() -> EmailSender:
    settings = get_settings()
    if settings.email_provider == "debug":
        return DebugEmailSender()
    return SmtpEmailSender(settings)


def get_auth_service(session: DbSessionDep, settings: SettingsDep) -> AuthService:
    return AuthService(
        users=UserRepository(session),
        otp_challenges=OtpRepository(session),
        refresh_sessions=RefreshSessionRepository(session),
        settings=settings,
        email_sender=_email_sender(),
        members=WorkspaceMemberRepository(session),
        workspaces=WorkspaceRepository(session),
        events=EventLogRepository(session),
        organizations=OrganizationRepository(session),
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_workspace_service(session: DbSessionDep, auth_service: AuthServiceDep) -> WorkspaceService:
    return WorkspaceService(
        workspaces=WorkspaceRepository(session),
        members=WorkspaceMemberRepository(session),
        organizations=OrganizationRepository(session),
        users=UserRepository(session),
        auth_service=auth_service,
        events=EventLogRepository(session),
        media_service=MediaService(media=MediaRepository(session), storage=_object_storage()),
    )


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


def get_brand_profile_service(session: DbSessionDep) -> BrandProfileService:
    return BrandProfileService(
        profiles=BrandProfileRepository(session),
        workspaces=WorkspaceRepository(session),
    )


BrandProfileServiceDep = Annotated[BrandProfileService, Depends(get_brand_profile_service)]


def get_billing_service(session: DbSessionDep) -> BillingService:
    return BillingService(
        billing=BillingRepository(session),
        workspaces=WorkspaceRepository(session),
        events=EventLogRepository(session),
    )


BillingServiceDep = Annotated[BillingService, Depends(get_billing_service)]


def get_inbox_service(session: DbSessionDep, settings: SettingsDep) -> InboxService:
    # Cùng cờ với worker (`build_reply_publishers`): hai đường gửi phải giống
    # nhau, lệch nhau thì bấm trả lời trên web gửi thật mà qua worker lại giả.
    if settings.use_fake_reply:
        reply_publishers: dict[Platform, ReplyPublisherPort] = {
            Platform.FACEBOOK: FakeReplyPublisher(Platform.FACEBOOK),
            Platform.ZALO_OA: FakeReplyPublisher(Platform.ZALO_OA),
        }
    else:
        reply_publishers = {
            Platform.FACEBOOK: FacebookReplyAdapter(ConnectionRepository(session)),
        }
    return InboxService(
        inbox=InboxRepository(session),
        profiles=BrandProfileRepository(session),
        events=EventLogRepository(session),
        reply_publishers=reply_publishers,
        connections=ConnectionRepository(session),
    )


InboxServiceDep = Annotated[InboxService, Depends(get_inbox_service)]


@lru_cache
def _alert_sink() -> AlertSink:
    return LoggingAlertSink()


AlertSinkDep = Annotated[AlertSink, Depends(_alert_sink)]


@lru_cache
def _object_storage() -> ObjectStorage:
    """Singleton — boto3 client giữ connection pool, tạo lại mỗi request là tốn vô
    ích. Không nhận `Settings` làm tham số vì Pydantic BaseSettings không hashable
    (lru_cache sẽ vỡ); `get_settings()` đã lru_cache nên vẫn là cùng một instance.
    """
    return ObjectStorage(get_settings())


ObjectStorageDep = Annotated[ObjectStorage, Depends(_object_storage)]


@lru_cache
def _rate_limiter() -> RedisRateLimiter | NullRateLimiter:
    """Singleton — `redis.asyncio.Redis` giữ connection pool, tạo lại mỗi request
    là mở socket mới liên tục.

    `decode_responses=False` (mặc định): chỉ INCR/EXPIRE/TTL nên không cần decode
    chuỗi, và bật decode chỉ thêm việc cho mỗi lượt.
    """
    settings = get_settings()
    if settings.disable_rate_limit:
        # Chỉ tới được đây khi HAVI_ENV=local — Settings ném lỗi lúc khởi động nếu
        # tắt rate limit ở staging/production.
        return NullRateLimiter()
    from redis.asyncio import Redis

    return RedisRateLimiter(Redis.from_url(settings.redis_url), alerts=_alert_sink())


RateLimiterDep = Annotated[RedisRateLimiter | NullRateLimiter, Depends(_rate_limiter)]


@lru_cache
def _video_processor() -> FFmpegVideoProcessor:
    """Một instance dùng chung: `__init__` chỉ chạy `shutil.which` hai lần, không
    giữ state, nên không cần dựng lại mỗi request."""
    return FFmpegVideoProcessor()


def get_media_service(session: DbSessionDep, settings: SettingsDep) -> MediaService:
    return MediaService(
        media=MediaRepository(session),
        storage=_object_storage(),
        video=_video_processor(),
        # Trần probe bám theo trần upload đã ký trong presigned POST — không có
        # object nào lớn hơn thế lọt được vào bucket, nên đây là biên đúng.
        max_probe_bytes=settings.media_max_upload_bytes,
    )


MediaServiceDep = Annotated[MediaService, Depends(get_media_service)]


def get_job_queue(session: DbSessionDep) -> JobQueue:
    """Outbox, không phải Celery trực tiếp.

    `OutboxJobQueue` ghi việc vào bảng `outbox` bằng **chính session của request**,
    nên bản ghi đó commit cùng transaction với dữ liệu nghiệp vụ. Đây là điều
    `CeleryJobQueue` không làm được: nó gọi Redis ngay, ngoài transaction, nên
    process chết giữa hai bước là mất job (xem `domain/models/outbox.py`).

    `CeleryJobQueue` vẫn còn trong codebase cho worker — chỗ đã ở ngoài vòng
    request và tự quản transaction của mình.
    """
    return OutboxJobQueue(OutboxRepository(session))


JobQueueDep = Annotated[JobQueue, Depends(get_job_queue)]


def get_content_service(
    session: DbSessionDep, queue: JobQueueDep, alerts: AlertSinkDep
) -> ContentService:
    return ContentService(
        content=ContentRepository(session),
        queue=queue,
        workspaces=WorkspaceRepository(session),
        events=EventLogRepository(session),
        alerts=alerts,
        media=MediaRepository(session),
        storage=_object_storage(),
    )


ContentServiceDep = Annotated[ContentService, Depends(get_content_service)]


def get_approval_service(session: DbSessionDep) -> ApprovalService:
    return ApprovalService(content=ContentRepository(session), events=EventLogRepository(session))


ApprovalServiceDep = Annotated[ApprovalService, Depends(get_approval_service)]


@lru_cache
def _oauth_clients() -> dict[Platform, OAuthClientPort]:
    settings = get_settings()
    return {
        Platform.FACEBOOK: FacebookOAuthClient(settings),
        Platform.GOOGLE_BUSINESS: GoogleBusinessOAuthClient(settings),
        Platform.TIKTOK: TikTokOAuthClient(settings),
        Platform.YOUTUBE: GoogleYouTubeOAuthClient(settings),
        Platform.ZALO_OA: ZaloOAuthClient(settings),
    }


def get_connection_service(session: DbSessionDep, settings: SettingsDep) -> ConnectionService:
    return ConnectionService(
        connections=ConnectionRepository(session),
        members=WorkspaceMemberRepository(session),
        oauth_clients=_oauth_clients(),
        settings=settings,
        events=EventLogRepository(session),
        workspaces=WorkspaceRepository(session),
    )


ConnectionServiceDep = Annotated[ConnectionService, Depends(get_connection_service)]


def get_publish_service(session: DbSessionDep) -> PublishService:
    """Dùng `build_publishers()` của worker, không dựng map riêng.

    Hai map sẽ lệch nhau: thêm adapter Zalo vào worker mà quên ở đây thì "Thử
    lại" trên API báo không hỗ trợ trong khi scheduler đăng được — hoặc ngược
    lại, tệ hơn. Import trong hàm vì module `worker.*` cần extra `queue`, còn
    `build_publishers` thì không — nhưng để import ở đầu file thì API phải cài cả
    Celery mới khởi động được.
    """
    from worker.publish_service_factory import build_publishers

    return PublishService(
        content=ContentRepository(session),
        connections=ConnectionRepository(session),
        publishes=PublishRepository(session),
        events=EventLogRepository(session),
        media=MediaRepository(session),
        storage=_object_storage(),
        alerts=_alert_sink(),
        publishers=build_publishers(),
    )


PublishServiceDep = Annotated[PublishService, Depends(get_publish_service)]


def get_video_post_service(session: DbSessionDep) -> VideoPostService:
    return VideoPostService(
        posts=VideoPostRepository(session),
        media=MediaRepository(session),
    )


VideoPostServiceDep = Annotated[VideoPostService, Depends(get_video_post_service)]


def get_video_publish_service(
    session: DbSessionDep, settings: SettingsDep
) -> VideoPublishService:
    from adapters.persistence.video_publish_repository import VideoPublishRepository
    from adapters.publishers.facebook import FacebookPublisher
    from adapters.storage.object_storage import ObjectStorage

    storage = ObjectStorage(settings)

    def signed_url_for(post) -> str:  # noqa: ANN001 — VideoPost
        """URL tải clip nguồn, ký lại mỗi lần gọi.

        Ký lại thay vì lưu sẵn một URL trong DB: URL ký có hạn dùng, nên một URL
        lưu từ hôm trước có thể đã hết hạn đúng lúc đăng. Ký lại rẻ hơn nhiều so
        với một lần đăng hỏng.
        """
        return storage.public_url(post.source_object_key)

    return VideoPublishService(
        posts=VideoPostRepository(session),
        attempts=VideoPublishRepository(session),
        connections=get_connection_service(session, settings),
        publisher=FacebookPublisher(settings),
        signed_url_for=signed_url_for,
    )


VideoPublishServiceDep = Annotated[VideoPublishService, Depends(get_video_publish_service)]


def get_voice_service(session: DbSessionDep, settings: SettingsDep) -> VoiceService:
    from adapters.voice.gemini_transcriber import GeminiVoiceTranscriber
    from adapters.voice.mock_transcriber import MockVoiceTranscriber
    from application.services.voice_service import VoiceService

    transcriber = (
        MockVoiceTranscriber() if settings.use_mock_llm else GeminiVoiceTranscriber(settings)
    )
    return VoiceService(
        transcriber=transcriber,
        events=EventLogRepository(session),
    )


VoiceServiceDep = Annotated[VoiceService, Depends(get_voice_service)]


class AuthContext:
    """Thông tin giải mã từ JWT."""

    def __init__(self, user_id: UUID, active_workspace_id: UUID | None) -> None:
        self.user_id = user_id
        self.active_workspace_id = active_workspace_id


async def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    settings: SettingsDep,
    session: DbSessionDep,
) -> AuthContext:
    try:
        decoded = decode_access_token(credentials.credentials, settings)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if decoded.active_workspace_id is not None:
        members = WorkspaceMemberRepository(session)
        is_member = await members.is_member(
            workspace_id=decoded.active_workspace_id, user_id=decoded.user_id
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Không còn là thành viên của workspace này",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return AuthContext(user_id=decoded.user_id, active_workspace_id=decoded.active_workspace_id)


AuthDep = Annotated[AuthContext, Depends(get_auth_context)]


def get_workspace_id(auth: AuthDep) -> UUID:
    if auth.active_workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tài khoản chưa chọn workspace — hoàn thành onboarding trước",
        )
    return auth.active_workspace_id


WorkspaceDep = Annotated[UUID, Depends(get_workspace_id)]


async def require_path_workspace_member(
    workspace_id: UUID, auth: AuthDep, session: DbSessionDep
) -> UUID:
    """Cho route có `{workspace_id}` trong path (get/update/members/...) — khác
    `WorkspaceDep` (đọc từ JWT). Không có check này thì bất kỳ JWT hợp lệ nào
    cũng đọc/sửa được workspace của người khác miễn biết UUID — đây là chặn
    cross-tenant leak thật, không chỉ ở active_workspace_id.
    """
    members = WorkspaceMemberRepository(session)
    if not await members.is_member(workspace_id=workspace_id, user_id=auth.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập workspace này",
        )
    return workspace_id


PathWorkspaceMemberDep = Annotated[UUID, Depends(require_path_workspace_member)]


async def require_path_workspace_owner(
    workspace_id: UUID, auth: AuthDep, session: DbSessionDep
) -> UUID:
    """Yêu cầu quyền OWNER cho các thao tác nhạy cảm: đổi publish_mode, quản trị thành viên."""
    members = WorkspaceMemberRepository(session)
    member = await members.get(workspace_id=workspace_id, user_id=auth.user_id)
    from core.enums import WorkspaceRole

    if member is None or member.role != WorkspaceRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ chủ sở hữu (Owner) mới có quyền thực hiện thao tác này",
        )
    return workspace_id


PathWorkspaceOwnerDep = Annotated[UUID, Depends(require_path_workspace_owner)]


def _require_permission(permission: str):  # noqa: ANN202
    """Dựng một dependency cưỡng chế đúng một quyền trên workspace đang active.

    Trả về `workspace_id` giống `WorkspaceDep` để router thay thế được tại chỗ,
    không phải nhận thêm tham số.

    Thông báo lỗi nêu **vai nào làm được**: "bạn không có quyền" khiến người dùng
    đi hỏi support, còn "cần vai Người duyệt hoặc Chủ workspace" thì họ tự nhắn
    cho đúng đồng nghiệp.
    """

    async def dependency(
        workspace_id: WorkspaceDep, auth: AuthDep, session: DbSessionDep
    ) -> UUID:
        from domain.policies.permissions import can, roles_with

        member = await WorkspaceMemberRepository(session).get(
            workspace_id=workspace_id, user_id=auth.user_id
        )
        if not can(member.role if member else None, permission):
            allowed = ", ".join(_ROLE_NAMES.get(r, r.value) for r in roles_with(permission))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Thao tác này cần vai: {allowed}.",
            )
        return workspace_id

    return dependency


#: Tên vai bằng tiếng Việt cho thông báo lỗi. Tên kỹ thuật (`reviewer`) không
#: giúp người đang bị chặn biết phải nhắn cho ai.
_ROLE_NAMES = {
    WorkspaceRole.OWNER: "Chủ workspace",
    WorkspaceRole.MARKETER: "Người soạn",
    WorkspaceRole.REVIEWER: "Người duyệt",
    WorkspaceRole.SALES: "Trực hội thoại",
}

#: Chỉ Người duyệt và Chủ workspace được đưa nội dung lên kênh.
ApproverWorkspaceDep = Annotated[UUID, Depends(_require_permission("approve_content"))]
#: Xem lịch sử hoạt động của cả workspace.
AuditViewerWorkspaceDep = Annotated[UUID, Depends(_require_permission("view_audit_log"))]


async def require_active_subscription_workspace(
    workspace_id: WorkspaceDep, session: DbSessionDep
) -> UUID:
    """Cưỡng chế subscription còn hiệu lực trước khi chạy các tác vụ tốn CPU/LLM cost (P0-3)."""
    from datetime import UTC, datetime

    from domain.policies import subscription

    ws_repo = WorkspaceRepository(session)
    ws = await ws_repo.get_by_id(workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy workspace",
        )

    now_dt = datetime.now(UTC)
    trial_dt = (
        ws.trial_ends_at.replace(tzinfo=UTC)
        if ws.trial_ends_at and ws.trial_ends_at.tzinfo is None
        else ws.trial_ends_at
    )
    paid_dt = (
        ws.paid_until.replace(tzinfo=UTC)
        if ws.paid_until and ws.paid_until.tzinfo is None
        else ws.paid_until
    )

    sub_state = subscription.state_for(
        plan=ws.plan,
        trial_ends_at=trial_dt,
        paid_until=paid_dt,
        now=now_dt,
    )
    if not sub_state.is_active:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Hạn dùng thử hoặc gói cước đã hết. Vui lòng nâng cấp gói cước để tiếp tục.",
        )
    return workspace_id


ActiveWorkspaceDep = Annotated[UUID, Depends(require_active_subscription_workspace)]
