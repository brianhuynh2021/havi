"""SQLAlchemy models — nguồn sự thật của schema, dùng cho Alembic autogenerate.

Import mọi model ở đây để `Base.metadata` (dùng trong migrations/env.py) thấy
đủ bảng. Domain layer chỉ định nghĩa cấu trúc dữ liệu; business rule (approval,
quota, state transition) nằm ở application/domain service, không nằm trong model.
"""

from domain.models.audit import EventLog
from domain.models.base import Base
from domain.models.media import MediaAsset
from domain.models.user import OtpChallenge, RefreshSession, User
from domain.models.workspace import BrandProfile, Workspace, WorkspaceMember

__all__ = [
    "Base",
    "User",
    "OtpChallenge",
    "RefreshSession",
    "Workspace",
    "WorkspaceMember",
    "BrandProfile",
    "MediaAsset",
    "EventLog",
]
