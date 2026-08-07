"""Use case cho /brand-profile — giọng văn, từ cấm, FAQ của một workspace.

Profile là resource 1:1 với workspace (workspace_id là primary key), tạo lazy ở
lần GET/PUT đầu tiên với `industry` lấy từ workspace — không cần workspace tạo
sẵn profile rỗng, và không có trạng thái "workspace tồn tại nhưng thiếu profile".
"""

from uuid import UUID

from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from core.schemas import FaqEntry
from domain.models.workspace import BrandProfile


class WorkspaceNotFound(Exception):
    pass


class BrandProfileService:
    def __init__(
        self,
        *,
        profiles: BrandProfileRepository,
        workspaces: WorkspaceRepository,
    ) -> None:
        self._profiles = profiles
        self._workspaces = workspaces

    async def get_or_create(self, workspace_id: UUID) -> BrandProfile:
        existing = await self._profiles.get(workspace_id)
        if existing is not None:
            return existing

        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise WorkspaceNotFound()
        return await self._profiles.create(
            workspace_id=workspace_id, industry=workspace.industry
        )

    async def update(
        self,
        workspace_id: UUID,
        *,
        tone: str | None,
        banned_claims: list[str] | None,
        faq: list[FaqEntry] | None,
        logo_url: str | None,
        brand_colors: list[str] | None,
    ) -> BrandProfile:
        profile = await self.get_or_create(workspace_id)
        # JSONB chỉ nhận kiểu JSON thuần — Pydantic model phải dump trước khi ghi.
        faq_rows = [entry.model_dump() for entry in faq] if faq is not None else None
        return await self._profiles.update(
            profile,
            tone=tone,
            banned_claims=banned_claims,
            faq=faq_rows,
            logo_url=logo_url,
            brand_colors=brand_colors,
        )
