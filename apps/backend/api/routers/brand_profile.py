"""/brand-profile — giọng văn, từ cấm, FAQ. Input bắt buộc cho mọi prompt chế bản."""

from fastapi import APIRouter

from api.deps import WorkspaceDep
from api.errors import NotImplementedEndpoint
from core.schemas import BrandProfile, BrandProfileUpdate

router = APIRouter(prefix="/brand-profile", tags=["brand-profile"])


@router.get("", response_model=BrandProfile)
def get_brand_profile(workspace_id: WorkspaceDep) -> BrandProfile:
    del workspace_id
    raise NotImplementedEndpoint()


@router.put("", response_model=BrandProfile)
def update_brand_profile(payload: BrandProfileUpdate, workspace_id: WorkspaceDep) -> BrandProfile:
    """Ghi xong phải invalidate cache profile của tenant để worker đọc bản mới."""
    del payload, workspace_id
    raise NotImplementedEndpoint()
