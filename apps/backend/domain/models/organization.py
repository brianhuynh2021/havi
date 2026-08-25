"""organizations — tầng doanh nghiệp phía TRÊN workspace.

Multi-brand / multi-branch được làm bằng cách **thêm một tầng lên trên**, không
phải bằng cách thêm `brand_id`/`branch_id` vào từng bảng.

Vì sao: một workspace **đã là** một thương hiệu hoặc một chi nhánh — nó có kênh
riêng, nội dung riêng, kho media riêng, thành viên riêng, chế độ duyệt riêng. Và
mười hai bảng nghiệp vụ đều đã scope theo `workspace_id`, với bộ test cách ly
tenant đầy đủ. Nhét thêm hai khoá ngoại vào cả mười hai bảng là viết lại lớp
cách ly đang chạy đúng — đổi lấy đúng thứ đã có.

Thứ thật sự còn thiếu chỉ có ba:

1. một chỗ **gom** các workspace của cùng một doanh nghiệp,
2. mời người **một lần cho cả tổ chức** thay vì mời lại ở từng thương hiệu,
3. một chỗ nhìn **chéo các workspace** để trả lời "toàn bộ social của công ty
   đang thế nào".

Ba thứ đó là hai bảng ở đây cộng một khoá ngoại nullable trên `workspaces` —
không đụng vào bảng nghiệp vụ nào.

`organization_id` để nullable: workspace tạo trước khi có tầng này vẫn hợp lệ, và
một chủ tiệm đơn lẻ không cần biết khái niệm "tổ chức" tồn tại.
"""

import uuid

from sqlalchemy import Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from core.enums import OrganizationRole
from domain.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Doanh nghiệp sở hữu một hoặc nhiều workspace (thương hiệu / chi nhánh)."""

    __tablename__ = "organizations"

    name: Mapped[str]
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)


class OrganizationMember(CreatedAtMixin, Base):
    """Thành viên cấp tổ chức.

    Tách khỏi `workspace_members` chứ không thay thế nó. Hai câu hỏi khác nhau:

    * `organization_members` — "người này thuộc công ty nào".
    * `workspace_members` — "người này làm được gì **ở thương hiệu nào**".

    Một người có thể ở trong tổ chức mà chỉ được vào hai trong năm chi nhánh, với
    vai khác nhau ở mỗi nơi. Gộp hai bảng là mất khả năng diễn đạt điều đó.
    """

    __tablename__ = "organization_members"
    # Khoá chính đã là (organization_id, user_id) — thêm UniqueConstraint trên
    # đúng hai cột đó chỉ tạo một index thừa và một cách nữa để cùng một luật
    # trôi lệch nhau.
    __table_args__ = (Index("ix_org_members_user", "user_id"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[OrganizationRole] = mapped_column(
        Enum(OrganizationRole, native_enum=False), default=OrganizationRole.MEMBER
    )
