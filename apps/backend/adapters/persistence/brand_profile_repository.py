from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import Industry
from domain.models.workspace import BrandProfile


class BrandProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, workspace_id: UUID) -> BrandProfile | None:
        result = await self._session.execute(
            select(BrandProfile).where(BrandProfile.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def create(self, *, workspace_id: UUID, industry: Industry) -> BrandProfile:
        profile = BrandProfile(
            workspace_id=workspace_id,
            industry=industry,
            tone="",
            banned_claims=[],
            faq=[],
            brand_colors=[],
        )
        self._session.add(profile)
        await self._session.flush()
        return profile

    async def update(
        self,
        profile: BrandProfile,
        *,
        tone: str | None = None,
        banned_claims: list[str] | None = None,
        faq: list[dict] | None = None,
        logo_url: str | None = None,
        brand_colors: list[str] | None = None,
    ) -> BrandProfile:
        if tone is not None:
            profile.tone = tone
        if banned_claims is not None:
            profile.banned_claims = banned_claims
        if faq is not None:
            profile.faq = faq
        if logo_url is not None:
            profile.logo_url = logo_url
        if brand_colors is not None:
            profile.brand_colors = brand_colors
        await self._session.flush()
        return profile
