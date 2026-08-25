"""REST API cho tầng doanh nghiệp — nhiều thương hiệu / chi nhánh trong một tổ chức.

Tầng này **không phải là lớp cách ly dữ liệu**. Mọi query nghiệp vụ vẫn scope
theo `workspace_id`, và đó là lớp cách ly duy nhất được test đầy đủ. Ở đây chỉ có
ba việc: liệt kê các thương hiệu của tôi, mở thêm một thương hiệu, và mời người
vào tổ chức.

Vì vậy mọi endpoint đều lọc theo *thành viên tổ chức* trước khi trả gì — biết id
tổ chức của người khác không được đọc ra danh sách thương hiệu của họ.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from adapters.persistence.organization_repository import OrganizationRepository
from adapters.persistence.user_repository import UserRepository
from api.deps import AuthDep, DbSessionDep, WorkspaceServiceDep
from core.enums import Industry, OrganizationRole
from core.schemas import (
    Organization,
    OrganizationBrand,
    OrganizationCreate,
    OrganizationWithBrands,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


class BrandCreate(BaseModel):
    """Mở thêm một thương hiệu / chi nhánh trong tổ chức đang có."""

    name: str = Field(min_length=1, max_length=160)
    industry: Industry


class OrganizationInvite(BaseModel):
    """Mời vào **tổ chức**, không phải vào một thương hiệu cụ thể.

    Quyền làm việc thật (soạn / duyệt / trả lời khách) vẫn cấp riêng ở từng
    workspace qua `/workspaces/{id}/members`. Vào tổ chức chỉ nghĩa là "người
    này thuộc công ty" — chưa vào được thương hiệu nào cả.
    """

    email: EmailStr


async def _require_member(
    session, organization_id: UUID, user_id: UUID
) -> OrganizationRole:  # noqa: ANN001
    role = await OrganizationRepository(session).get_role(
        organization_id=organization_id, user_id=user_id
    )
    if role is None:
        # 404 chứ không 403: xác nhận "tổ chức này tồn tại nhưng bạn không thuộc"
        # là đã tiết lộ một điều về công ty người khác.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy tổ chức")
    return role


async def _require_owner(session, organization_id: UUID, user_id: UUID) -> None:  # noqa: ANN001
    if await _require_member(session, organization_id, user_id) is not OrganizationRole.OWNER:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Chỉ chủ tổ chức mới mở thêm thương hiệu hoặc mời người vào.",
        )


@router.get("", response_model=list[OrganizationWithBrands])
async def list_my_organizations(
    auth: AuthDep, session: DbSessionDep
) -> list[OrganizationWithBrands]:
    """Các tổ chức tôi thuộc về, kèm thương hiệu của từng tổ chức.

    Trả kèm luôn danh sách thương hiệu thay vì bắt gọi thêm N lượt: màn chọn
    thương hiệu luôn cần cả hai cùng lúc, và N+1 request chỉ để dựng một menu là
    chi phí không mua được gì.
    """
    repo = OrganizationRepository(session)
    result: list[OrganizationWithBrands] = []
    for org in await repo.get_for_user(auth.user_id):
        brands = await repo.workspaces_of(org.id)
        result.append(
            OrganizationWithBrands(
                organization=Organization.model_validate(org),
                brands=[OrganizationBrand.model_validate(b) for b in brands],
            )
        )
    return result


@router.post("", response_model=Organization, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate, auth: AuthDep, session: DbSessionDep
) -> Organization:
    """Tạo một tổ chức mới. Người tạo thành chủ tổ chức."""
    org = await OrganizationRepository(session).create(
        name=payload.name, owner_user_id=auth.user_id
    )
    return Organization.model_validate(org)


@router.post(
    "/{organization_id}/brands",
    response_model=OrganizationBrand,
    status_code=status.HTTP_201_CREATED,
)
async def create_brand(
    organization_id: UUID,
    payload: BrandCreate,
    auth: AuthDep,
    session: DbSessionDep,
    workspaces: WorkspaceServiceDep,
) -> OrganizationBrand:
    """Mở thêm một thương hiệu / chi nhánh.

    Thương hiệu mới là một workspace hoàn chỉnh: kênh riêng, nội dung riêng, kho
    media riêng, thành viên riêng. Dữ liệu **không** chảy chéo giữa các thương
    hiệu trong cùng tổ chức — đó là điểm khiến multi-brand khác với gắn nhãn.
    """
    await _require_owner(session, organization_id, auth.user_id)
    workspace = await workspaces.create_workspace(
        owner_user_id=auth.user_id,
        name=payload.name,
        industry=payload.industry,
        organization_id=organization_id,
    )
    return OrganizationBrand.model_validate(workspace)


@router.post("/{organization_id}/members", status_code=status.HTTP_204_NO_CONTENT)
async def invite_to_organization(
    organization_id: UUID,
    payload: OrganizationInvite,
    auth: AuthDep,
    session: DbSessionDep,
) -> None:
    """Thêm người vào tổ chức. Họ chưa vào được thương hiệu nào cho tới khi được
    cấp vai ở đó qua `/workspaces/{id}/members`."""
    await _require_owner(session, organization_id, auth.user_id)

    user = await UserRepository(session).get_by_email(payload.email)
    if user is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Email chưa có tài khoản Havi — mời họ đăng ký trước.",
        )
    await OrganizationRepository(session).add_member(
        organization_id=organization_id, user_id=user.id
    )
