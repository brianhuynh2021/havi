"""Mặc định của Postgres phải khớp cách SQLAlchemy đọc enum.

Hồi quy cho một bug đã xảy ra thật (`f4a5b6c7d8e9`).

`Enum(SomeEnum, native_enum=False)` lưu **tên** thành viên (`MONTHLY`), không lưu
giá trị (`monthly`). Một migration đặt `server_default` bằng giá trị chữ thường sẽ
tạo ra những dòng mà **ORM không đọc nổi**: `LookupError` ném lúc hydrate, nên
*bất cứ* truy vấn nào load bảng đó đều đổ — không chỉ màn hình dùng cột mới.

Và nó khó nhìn ra: dòng do ORM chèn sau migration thì đúng, nên tính năng chạy
bình thường với dữ liệu mới và chỉ vỡ với dữ liệu cũ.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.workspace_repository import WorkspaceRepository
from core.enums import BillingCycle, Plan
from domain.models.user import User


async def _owner(session: AsyncSession) -> uuid.UUID:
    """Workspace cần chủ; tạo một user tối thiểu cho khoá ngoại."""
    user = User(
        name="Chủ",
        email=f"enum-default-{uuid.uuid4().hex[:8]}@havi.vn",
        password_hash="x",
    )
    session.add(user)
    await session.flush()
    return user.id


async def test_dong_dung_mac_dinh_cua_postgres_van_doc_duoc_bang_orm(
    db_session: AsyncSession,
):
    """Chèn bằng SQL thô, **không** nêu `billing_cycle`, rồi đọc lại bằng ORM.

    Đây là đúng đường đi của bug: migration điền `server_default`, ORM đọc lại.
    Test qua ORM cả hai đầu sẽ không bắt được, vì ORM tự ghi đúng tên.
    """
    owner_id = await _owner(db_session)
    workspace_id = uuid.uuid4()
    await db_session.execute(
        text(
            "INSERT INTO workspaces "
            "(id, owner_user_id, name, industry, plan, publish_mode, created_at) "
            "VALUES (:id, :owner, :name, 'OTHER', 'TRIAL', 'REVIEW_FIRST', now())"
        ),
        {"id": workspace_id, "owner": owner_id, "name": "Kiểm tra mặc định"},
    )
    await db_session.flush()

    # Ném `LookupError` ở đây nghĩa là server_default không khớp tên enum.
    workspace = await WorkspaceRepository(db_session).get_by_id(workspace_id)

    assert workspace is not None
    assert workspace.billing_cycle is BillingCycle.MONTHLY
    assert workspace.plan is Plan.TRIAL
    # Phần đã mua thêm mặc định bằng 0, không phải NULL — `effective_limits` cộng
    # trực tiếp nên NULL sẽ thành lỗi kiểu chứ không thành trần đúng.
    assert workspace.extra_seats == 0
    assert workspace.extra_channels == 0


async def test_hoa_don_dung_mac_dinh_cung_doc_duoc(db_session: AsyncSession):
    """Cùng bug, bảng khác — `invoices` cũng nhận ba cột đó trong cùng migration."""
    owner_id = await _owner(db_session)
    workspace_id = uuid.uuid4()
    await db_session.execute(
        text(
            "INSERT INTO workspaces "
            "(id, owner_user_id, name, industry, plan, publish_mode, created_at) "
            "VALUES (:id, :owner, 'Hoá đơn', 'OTHER', 'TIEM_NHO', 'REVIEW_FIRST', now())"
        ),
        {"id": workspace_id, "owner": owner_id},
    )
    invoice_id = uuid.uuid4()
    await db_session.execute(
        text(
            "INSERT INTO invoices (id, workspace_id, plan, amount_vnd, status, issued_at, "
            "created_at) VALUES (:id, :ws, 'TIEM_NHO', 189000, 'PENDING', now(), now())"
        ),
        {"id": invoice_id, "ws": workspace_id},
    )
    await db_session.flush()

    from adapters.persistence.billing_repository import BillingRepository

    invoice = await BillingRepository(db_session).get_invoice(invoice_id)

    assert invoice is not None
    assert invoice.billing_cycle is BillingCycle.MONTHLY
    assert invoice.extra_seats == 0
