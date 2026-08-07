from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import MediaStatus, MediaType
from domain.models.media import MediaAsset


class MediaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, workspace_id: UUID, asset_id: UUID) -> MediaAsset | None:
        """Luôn scope theo workspace_id — không cho đọc asset của tenant khác."""
        result = await self._session.execute(
            select(MediaAsset).where(
                MediaAsset.id == asset_id, MediaAsset.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        workspace_id: UUID,
        object_key: str,
        filename: str,
        content_type: str,
        type: MediaType,
    ) -> MediaAsset:
        asset = MediaAsset(
            workspace_id=workspace_id,
            object_key=object_key,
            filename=filename,
            content_type=content_type,
            type=type,
        )
        self._session.add(asset)
        await self._session.flush()
        return asset

    async def list_for_workspace(
        self,
        *,
        workspace_id: UUID,
        type: MediaType | None = None,
        status: MediaStatus | None = None,
        tag: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MediaAsset], int]:
        filters = [MediaAsset.workspace_id == workspace_id]
        if type is not None:
            filters.append(MediaAsset.type == type)
        if status is not None:
            filters.append(MediaAsset.status == status)
        if tag is not None:
            filters.append(MediaAsset.tags.contains([tag]))

        total = await self._session.execute(select(func.count()).where(*filters))
        rows = await self._session.execute(
            select(MediaAsset)
            .where(*filters)
            .order_by(MediaAsset.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().all()), total.scalar_one()

    async def mark_uploaded(self, asset: MediaAsset, *, size_bytes: int) -> MediaAsset:
        asset.status = MediaStatus.RAW
        asset.size_bytes = size_bytes
        asset.uploaded_at = datetime.now(UTC)
        await self._session.flush()
        return asset

    async def update(
        self,
        asset: MediaAsset,
        *,
        tags: list[str] | None = None,
        status: MediaStatus | None = None,
    ) -> MediaAsset:
        if tags is not None:
            asset.tags = tags
        if status is not None:
            asset.status = status
        await self._session.flush()
        return asset
