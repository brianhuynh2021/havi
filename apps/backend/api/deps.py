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
from adapters.oauth.base import OAuthClientPort
from adapters.oauth.facebook import FacebookOAuthClient
from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.connection_repository import ConnectionRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.db import DbSessionDep
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.otp_repository import OtpRepository
from adapters.persistence.publish_repository import PublishRepository
from adapters.persistence.refresh_session_repository import RefreshSessionRepository
from adapters.persistence.user_repository import UserRepository
from adapters.persistence.workspace_member_repository import WorkspaceMemberRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from adapters.ratelimit import NullRateLimiter, RedisRateLimiter
from adapters.storage.object_storage import ObjectStorage
from application.services.approval_service import ApprovalService
from application.services.auth_service import AuthService
from application.services.brand_profile_service import BrandProfileService
from application.services.connection_service import ConnectionService
from application.services.content_service import ContentService
from application.services.job_queue import CeleryJobQueue, JobQueue
from application.services.media_service import MediaService
from application.services.publish_service import PublishService
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
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_workspace_service(
    session: DbSessionDep, auth_service: AuthServiceDep
) -> WorkspaceService:
    return WorkspaceService(
        workspaces=WorkspaceRepository(session),
        members=WorkspaceMemberRepository(session),
        users=UserRepository(session),
        auth_service=auth_service,
    )


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


def get_brand_profile_service(session: DbSessionDep) -> BrandProfileService:
    return BrandProfileService(
        profiles=BrandProfileRepository(session),
        workspaces=WorkspaceRepository(session),
    )


BrandProfileServiceDep = Annotated[BrandProfileService, Depends(get_brand_profile_service)]


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


RateLimiterDep = Annotated[
    RedisRateLimiter | NullRateLimiter, Depends(_rate_limiter)
]


def get_media_service(session: DbSessionDep) -> MediaService:
    return MediaService(media=MediaRepository(session), storage=_object_storage())


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
    return ApprovalService(
        content=ContentRepository(session), events=EventLogRepository(session)
    )


ApprovalServiceDep = Annotated[ApprovalService, Depends(get_approval_service)]


@lru_cache
def _oauth_clients() -> dict[Platform, OAuthClientPort]:
    """Chỉ Facebook có adapter ở pilot — Zalo/Google vắng mặt ở đây là cố ý.

    `ConnectionService` sẽ ném `PlatformNotSupported` cho nền tảng không có
    trong dict, và router dịch thành 501. Như vậy UI không bao giờ hiện
    "đã nối" cho một kênh chưa có adapter thật (ROADMAP Tuần 7, mục frontend).

    Cùng lý do lru_cache như `_object_storage`: không nhận `Settings` làm tham
    số vì BaseSettings không hashable; `get_settings()` đã cache sẵn.
    """
    return {Platform.FACEBOOK: FacebookOAuthClient(get_settings())}


def get_connection_service(session: DbSessionDep, settings: SettingsDep) -> ConnectionService:
    return ConnectionService(
        connections=ConnectionRepository(session),
        members=WorkspaceMemberRepository(session),
        oauth_clients=_oauth_clients(),
        settings=settings,
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
