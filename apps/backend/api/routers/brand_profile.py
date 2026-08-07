"""/brand-profile — giọng văn, từ cấm, FAQ. Input bắt buộc cho mọi prompt chế bản."""

from fastapi import APIRouter, HTTPException, status

from api.deps import BrandProfileServiceDep, WorkspaceDep
from application.services.brand_profile_service import WorkspaceNotFound
from core.schemas import BrandProfile, BrandProfileUpdate

router = APIRouter(prefix="/brand-profile", tags=["brand-profile"])


@router.get("", response_model=BrandProfile)
async def get_brand_profile(
    workspace_id: WorkspaceDep, brand_profile_service: BrandProfileServiceDep
) -> BrandProfile:
    try:
        profile = await brand_profile_service.get_or_create(workspace_id)
    except WorkspaceNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy workspace") from exc
    return BrandProfile.model_validate(profile)


@router.put("", response_model=BrandProfile)
async def update_brand_profile(
    payload: BrandProfileUpdate,
    workspace_id: WorkspaceDep,
    brand_profile_service: BrandProfileServiceDep,
) -> BrandProfile:
    """Ghi xong phải invalidate cache profile của tenant để worker đọc bản mới.

    Hiện chưa có cache nào — worker đọc trực tiếp từ DB. Khi thêm cache
    (Redis, xem ROADMAP.md "Hạ tầng bắt buộc trước beta") thì invalidate ở đây.

    Lưu ý contract: mọi field trong `BrandProfileUpdate` đều optional, nên
    endpoint này hành xử như PATCH (field không gửi thì giữ nguyên) dù dùng verb
    PUT. Hệ quả: gửi `logo_url: null` **không** xoá logo — muốn xoá cần đổi
    contract sang sentinel value, chưa làm vì UI chưa có nút xoá logo.
    """
    try:
        profile = await brand_profile_service.update(
            workspace_id,
            tone=payload.tone,
            banned_claims=payload.banned_claims,
            faq=payload.faq,
            logo_url=payload.logo_url,
            brand_colors=payload.brand_colors,
        )
    except WorkspaceNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy workspace") from exc
    return BrandProfile.model_validate(profile)
