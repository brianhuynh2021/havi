"""SQLAlchemy models — nguồn sự thật của schema, dùng cho Alembic autogenerate.

Import mọi model ở đây để `Base.metadata` (dùng trong migrations/env.py) thấy
đủ bảng. Domain layer chỉ định nghĩa cấu trúc dữ liệu; business rule (approval,
quota, state transition) nằm ở application/domain service, không nằm trong model.
"""

from domain.models.audit import EventLog
from domain.models.base import Base
from domain.models.connection import PlatformConnection
from domain.models.content import ContentItem, ContentItemVersion, ContentJob
from domain.models.crm_nudge import CrmNudge
from domain.models.goal import Goal
from domain.models.inbox import InboxItem
from domain.models.lead import Lead
from domain.models.media import MediaAsset
from domain.models.publish import PublishJob
from domain.models.roadmap import EvidenceLog, Roadmap, RoadmapReview, RoadmapTask
from domain.models.user import OtpChallenge, RefreshSession, User
from domain.models.video_render import VideoRenderJob
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
    "VideoRenderJob",
    "ContentJob",
    "ContentItem",
    "ContentItemVersion",
    "EventLog",
    "PlatformConnection",
    "PublishJob",
    "InboxItem",
    "Lead",
    "CrmNudge",
    "Invoice",
    "Goal",
    "Roadmap",
    "RoadmapTask",
    "EvidenceLog",
    "RoadmapReview",
]

