"""Hàng đợi việc — bốn nguồn về một danh sách, và cách ly theo workspace."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.inbox_repository import InboxRepository
from core.enums import (
    Channel,
    ContentStatus,
    InboxItemStatus,
    InboxItemType,
    Platform,
    PublishStatus,
)
from domain.models.content import ContentItem
from domain.models.publish import PublishJob


async def _onboard(client: AsyncClient, *, email: str) -> dict:
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "Chị Hương", "email": email, "password": "matkhau123"},
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()
    create = await client.post(
        "/workspaces",
        json={"name": "Resort An Nhiên"},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert create.status_code == 201, create.text
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    return refreshed.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


async def _add_inbox(
    session: AsyncSession,
    *,
    workspace_id: str,
    content: str,
    created_at: datetime,
    item_type: InboxItemType = InboxItemType.MESSAGE,
    external_message_id: str | None = None,
    status: InboxItemStatus = InboxItemStatus.NEW,
):
    item = await InboxRepository(session).create(
        workspace_id=UUID(workspace_id),
        platform=Platform.FACEBOOK,
        content=content,
        author_name="Minh Anh",
        type=item_type,
        status=status,
        external_message_id=external_message_id,
    )
    item.created_at = created_at
    await session.flush()
    return item


async def test_workspace_moi_thi_hang_doi_rong(client: AsyncClient):
    token_pair = await _onboard(client, email="queue-empty@havi.vn")

    response = await client.get("/queue", headers=_headers(token_pair))

    assert response.status_code == 200, response.text
    assert response.json() == {"items": [], "total": 0}


async def test_bon_nguon_ve_mot_danh_sach_va_xep_theo_thiet_hai(
    client: AsyncClient, db_session: AsyncSession
):
    """Đây là ý nghĩa của sản phẩm: một danh sách, xếp theo thiệt hại khi bỏ sót.

    Cố ý tạo theo thứ tự thời gian **ngược** với thứ tự ưu tiên: nháp chờ duyệt
    tạo sớm nhất, tin hỏi giá tạo muộn nhất. Nếu hàng đợi xếp thuần theo thời
    gian thì nháp lên đầu — và đó chính là lỗi mà thứ tự ưu tiên tồn tại để tránh.
    """
    token_pair = await _onboard(client, email="queue-mixed@havi.vn")
    workspace_id = token_pair["active_workspace_id"]
    now = datetime.now(UTC)

    draft = ContentItem(
        workspace_id=UUID(workspace_id),
        channel=Channel.FACEBOOK_PAGE,
        kind="Bài ảnh",
        text="Ưu đãi cuối tuần cho khách nghỉ dưỡng",
        status=ContentStatus.PENDING_APPROVAL,
    )
    db_session.add(draft)
    await db_session.flush()
    draft.created_at = now - timedelta(days=3)

    job = PublishJob(
        workspace_id=UUID(workspace_id),
        content_item_id=draft.id,
        channel=Channel.FACEBOOK_PAGE,
        idempotency_key=f"queue-test-{uuid4()}",
        status=PublishStatus.DEAD_LETTER,
        scheduled_at=now - timedelta(days=2),
        failure_detail="Rate limit",
    )
    db_session.add(job)

    await _add_inbox(
        db_session,
        workspace_id=workspace_id,
        content="Mấy giờ mở cửa vậy shop",
        created_at=now - timedelta(hours=6),
    )
    await _add_inbox(
        db_session,
        workspace_id=workspace_id,
        content="Cho em xin bảng giá phòng cuối tuần",
        created_at=now - timedelta(minutes=10),
    )
    await db_session.flush()

    response = await client.get("/queue", headers=_headers(token_pair))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 4
    kinds = [item["kind"] for item in body["items"]]
    # Hỏi giá (khách đang muốn mua) → bài đăng lỗi (mất âm thầm) → hỏi thông tin
    # → nháp chờ duyệt (chưa mất gì). KHÔNG theo thứ tự thời gian.
    assert kinds == ["inbox", "publish_failure", "inbox", "approval"]
    assert body["items"][0]["category"] == "price"
    assert body["items"][2]["category"] == "info"


async def test_hang_doi_khong_lan_sang_workspace_khac(
    client: AsyncClient, db_session: AsyncSession
):
    token_a = await _onboard(client, email="queue-tenant-a@havi.vn")
    token_b = await _onboard(client, email="queue-tenant-b@havi.vn")
    now = datetime.now(UTC)

    await _add_inbox(
        db_session,
        workspace_id=token_b["active_workspace_id"],
        content="Cho em xin báo giá",
        created_at=now,
    )
    await db_session.flush()

    response = await client.get("/queue", headers=_headers(token_a))

    assert response.json()["total"] == 0


async def test_tin_da_tra_loi_roi_thi_ra_khoi_hang_doi(
    client: AsyncClient, db_session: AsyncSession
):
    token_pair = await _onboard(client, email="queue-closed@havi.vn")
    now = datetime.now(UTC)

    await _add_inbox(
        db_session,
        workspace_id=token_pair["active_workspace_id"],
        content="Cho em xin báo giá",
        created_at=now,
        status=InboxItemStatus.SENT,
    )
    await _add_inbox(
        db_session,
        workspace_id=token_pair["active_workspace_id"],
        content="Đặt lịch giúp em",
        created_at=now,
        status=InboxItemStatus.DISMISSED,
    )
    await db_session.flush()

    assert (await client.get("/queue", headers=_headers(token_pair))).json()["total"] == 0


async def test_binh_luan_co_link_ra_nen_tang_tin_nhan_thi_khong(
    client: AsyncClient, db_session: AsyncSession
):
    """Thà không có nút hơn là nút dẫn sai — xem `domain/policies/platform_links.py`."""
    token_pair = await _onboard(client, email="queue-links@havi.vn")
    workspace_id = token_pair["active_workspace_id"]
    now = datetime.now(UTC)

    await _add_inbox(
        db_session,
        workspace_id=workspace_id,
        content="Bình luận hỏi giá phòng",
        created_at=now,
        item_type=InboxItemType.COMMENT,
        external_message_id="100_200",
    )
    await _add_inbox(
        db_session,
        workspace_id=workspace_id,
        content="Tin nhắn hỏi giá phòng",
        created_at=now - timedelta(minutes=1),
        item_type=InboxItemType.MESSAGE,
        external_message_id="psid-xyz",
    )
    await db_session.flush()

    items = (await client.get("/queue", headers=_headers(token_pair))).json()["items"]
    by_detail = {item["detail"]: item for item in items}
    assert by_detail["Bình luận hỏi giá phòng"]["platform_url"] == (
        "https://www.facebook.com/100_200"
    )
    assert by_detail["Tin nhắn hỏi giá phòng"]["platform_url"] is None


async def test_nhan_viec_roi_tra_lai_hang_doi(client: AsyncClient, db_session: AsyncSession):
    """Resort có nhiều nhân viên trực ca. Không có chỗ ghi "ai đang xử lý" thì hai
    người cùng mở một tin và cùng trả lời một khách."""
    token_pair = await _onboard(client, email="queue-assign@havi.vn")
    item = await _add_inbox(
        db_session,
        workspace_id=token_pair["active_workspace_id"],
        content="Cho em xin báo giá",
        created_at=datetime.now(UTC),
    )
    await db_session.flush()

    me = await client.get("/auth/me", headers=_headers(token_pair))
    assert me.status_code == 200, me.text
    user_id = me.json()["id"]

    claimed = await client.post(
        f"/queue/inbox/{item.id}/assign",
        json={"user_id": user_id},
        headers=_headers(token_pair),
    )
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["assigned_to_user_id"] == user_id
    assert claimed.json()["assigned_to_name"] == "Chị Hương"

    # Nhận việc KHÔNG đổi trạng thái phản hồi — việc vẫn đang chờ được trả lời,
    # nên vẫn phải nằm trong hàng đợi.
    queue = (await client.get("/queue", headers=_headers(token_pair))).json()
    assert queue["total"] == 1
    assert queue["items"][0]["assigned_to_name"] == "Chị Hương"

    released = await client.post(
        f"/queue/inbox/{item.id}/assign",
        json={"user_id": None},
        headers=_headers(token_pair),
    )
    assert released.status_code == 200, released.text
    assert released.json()["assigned_to_user_id"] is None


async def test_nhan_viec_khong_ton_tai_tra_404(client: AsyncClient):
    token_pair = await _onboard(client, email="queue-assign-404@havi.vn")

    response = await client.post(
        f"/queue/inbox/{uuid4()}/assign",
        json={"user_id": None},
        headers=_headers(token_pair),
    )
    assert response.status_code == 404


async def test_chi_so_ton_that_tranh_duoc(client: AsyncClient, db_session: AsyncSession):
    """Chỉ số bán được hàng: thời gian phản hồi và việc bị bỏ sót.

    Cố ý KHÔNG có chỉ số nào về doanh thu hay khách đến — Havi báo cáo việc nó đã
    làm, kết quả kinh doanh thuộc về doanh nghiệp.
    """
    token_pair = await _onboard(client, email="queue-metrics@havi.vn")
    workspace_id = token_pair["active_workspace_id"]
    now = datetime.now(UTC)
    repo = InboxRepository(db_session)

    # Một tin đã trả lời sau 30 phút.
    replied = await _add_inbox(
        db_session,
        workspace_id=workspace_id,
        content="Cho em xin bảng giá phòng",
        created_at=now - timedelta(hours=2),
    )
    await repo.update_status(
        replied, status=InboxItemStatus.SENT, now=now - timedelta(minutes=90)
    )

    # Một tin hỏi giá còn treo từ hai ngày trước — đây là "bỏ sót" thật.
    await _add_inbox(
        db_session,
        workspace_id=workspace_id,
        content="Báo giá giúp em với",
        created_at=now - timedelta(days=2),
    )
    # Một tin hỏi giờ mở cửa cũng treo hai ngày, nhưng KHÔNG tính là bỏ sót tốn
    # tiền: sót "mấy giờ mở cửa" khác sót "cho em báo giá".
    await _add_inbox(
        db_session,
        workspace_id=workspace_id,
        content="Mấy giờ mở cửa vậy",
        created_at=now - timedelta(days=2),
    )
    # Tin mới đến 10 phút trước: chậm chưa phải là sót.
    await _add_inbox(
        db_session,
        workspace_id=workspace_id,
        content="Cho em hỏi giá combo",
        created_at=now - timedelta(minutes=10),
    )
    await db_session.flush()

    today = now.date().isoformat()
    response = await client.get(
        "/queue/response-metrics",
        params={"start": today, "end": today},
        headers=_headers(token_pair),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["replied_count"] == 1
    # 2 giờ chờ − trả lời lúc còn 90 phút = 30 phút.
    assert body["avg_response_seconds"] == 30 * 60
    assert body["waiting_over_4h"] == 2
    assert body["waiting_over_1h"] == 2
    # Chỉ tin hỏi giá treo quá một ngày. Tin hỏi giờ mở cửa và tin mới không tính.
    assert body["missed_costly"] == 1


async def test_response_metrics_ngay_dao_nguoc_tra_422(client: AsyncClient):
    token_pair = await _onboard(client, email="queue-metrics-bad@havi.vn")

    response = await client.get(
        "/queue/response-metrics",
        params={"start": "2026-08-20", "end": "2026-08-10"},
        headers=_headers(token_pair),
    )
    assert response.status_code == 422
