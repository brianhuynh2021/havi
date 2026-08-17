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
from adapters.persistence.crm_nudge_repository import CrmNudgeRepository
from adapters.persistence.db import DbSessionDep
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.inbox_repository import InboxRepository
from adapters.persistence.lead_repository import LeadRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.otp_repository import OtpRepository
from adapters.persistence.publish_repository import PublishRepository
from adapters.persistence.refresh_session_repository import RefreshSessionRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.video_render_repository import VideoRenderRepository
from adapters.persistence.workspace_member_repository import WorkspaceMemberRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from adapters.publishers.facebook_reply import FacebookReplyAdapter
from adapters.publishers.fake_reply import FakeReplyPublisher
from adapters.ratelimit import NullRateLimiter, RedisRateLimiter
from adapters.storage.object_storage import ObjectStorage
from application.services.ai_lead_agent_service import AILeadAgentService
from application.services.approval_service import ApprovalService
from application.services.auth_service import AuthService
from application.services.billing_service import BillingService
from application.services.brand_profile_service import BrandProfileService
from application.services.connection_service import ConnectionService
from application.services.content_service import ContentService
from application.services.crm_nudge_service import CrmNudgeService
from application.services.inbox_service import InboxService
from application.services.job_queue import CeleryJobQueue, JobQueue
from application.services.lead_service import LeadService
from application.services.media_service import MediaService
from application.services.publish_service import PublishService
from application.services.sales_service import SalesService
from application.services.video_render_service import VideoRenderService
from application.services.voice_service import VoiceService
from application.services.workspace_service import WorkspaceService
from core.alerts import AlertSink, LoggingAlertSink
from core.config import Settings, get_settings
from core.enums import Platform
from core.security import decode_access_token
from domain.ports.email import EmailSender

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
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_workspace_service(session: DbSessionDep, auth_service: AuthServiceDep) -> WorkspaceService:
    return WorkspaceService(
        workspaces=WorkspaceRepository(session),
        members=WorkspaceMemberRepository(session),
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
    connections = ConnectionRepository(session)
    fb_publisher = (
        FakeReplyPublisher(Platform.FACEBOOK)
        if settings.use_fake_publisher
        else FacebookReplyAdapter(connections)
    )
    reply_publishers = {
        Platform.FACEBOOK: fb_publisher,
        Platform.ZALO_OA: FakeReplyPublisher(Platform.ZALO_OA),
    }
    return InboxService(
        inbox=InboxRepository(session),
        profiles=BrandProfileRepository(session),
        events=EventLogRepository(session),
        reply_publishers=reply_publishers,
    )


InboxServiceDep = Annotated[InboxService, Depends(get_inbox_service)]


def get_lead_service(session: DbSessionDep) -> LeadService:
    return LeadService(leads=LeadRepository(session))


LeadServiceDep = Annotated[LeadService, Depends(get_lead_service)]


def get_crm_nudge_service(session: DbSessionDep) -> CrmNudgeService:
    return CrmNudgeService(
        nudge_repo=CrmNudgeRepository(session),
        workspace_repo=WorkspaceRepository(session),
        profile_repo=BrandProfileRepository(session),
        event_repo=EventLogRepository(session),
    )


CrmNudgeServiceDep = Annotated[CrmNudgeService, Depends(get_crm_nudge_service)]


def get_sales_service(session: DbSessionDep) -> SalesService:
    return SalesService(
        lead_repo=LeadRepository(session),
        event_repo=EventLogRepository(session),
    )


SalesServiceDep = Annotated[SalesService, Depends(get_sales_service)]


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


def get_job_queue() -> JobQueue:
    return CeleryJobQueue()


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
        alerts=_alert_sink(),
        publishers=build_publishers(),
    )


PublishServiceDep = Annotated[PublishService, Depends(get_publish_service)]


def get_video_render_service(session: DbSessionDep) -> VideoRenderService:
    return VideoRenderService(
        render_repo=VideoRenderRepository(session),
        media_repo=MediaRepository(session),
        event_repo=EventLogRepository(session),
    )


VideoRenderServiceDep = Annotated[VideoRenderService, Depends(get_video_render_service)]


def get_ai_lead_agent_service(session: DbSessionDep) -> AILeadAgentService:
    return AILeadAgentService(
        leads=LeadRepository(session),
        inbox=InboxRepository(session),
    )


AILeadAgentServiceDep = Annotated[AILeadAgentService, Depends(get_ai_lead_agent_service)]


def get_voice_service(session: DbSessionDep, settings: SettingsDep) -> VoiceService:
    from adapters.voice.gemini_transcriber import GeminiVoiceTranscriber
    from adapters.voice.mock_transcriber import MockVoiceTranscriber
    from application.services.voice_service import VoiceService

    transcriber = (
        MockVoiceTranscriber()
        if settings.use_mock_llm
        else GeminiVoiceTranscriber(settings)
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
