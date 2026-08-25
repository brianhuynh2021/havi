"""SQLAlchemy models — nguồn sự thật của schema, dùng cho Alembic autogenerate.

Import mọi model ở đây để `Base.metadata` (dùng trong migrations/env.py) thấy
đủ bảng. Domain layer chỉ định nghĩa cấu trúc dữ liệu; business rule (approval,
quota, state transition) nằm ở application/domain service, không nằm trong model.
"""

from domain.models.audit import EventLog
from domain.models.base import Base
from domain.models.connection import PlatformConnection
from domain.models.content import ContentItem, ContentItemVersion, ContentJob
from domain.models.inbox import InboxItem
from domain.models.media import MediaAsset
from domain.models.organization import Organization, OrganizationMember
from domain.models.publish import PublishJob
from domain.models.user import OtpChallenge, RefreshSession, User
from domain.models.video_post import VideoPost
from domain.models.video_publish import VideoPublishAttempt
from domain.models.workspace import (
    BrandProfile,
    Invoice,
    Workspace,
    WorkspaceMember,
)

__all__ = [
    "Base",
    "User",
    "OtpChallenge",
    "RefreshSession",
    "Workspace",
    "WorkspaceMember",
    "BrandProfile",
    "MediaAsset",
    "Organization",
    "OrganizationMember",
    "VideoPublishAttempt",
    "VideoPost",
    "ContentJob",
    "ContentItem",
    "ContentItemVersion",
    "EventLog",
    "PlatformConnection",
    "PublishJob",
    "InboxItem",
    "Invoice",
]
