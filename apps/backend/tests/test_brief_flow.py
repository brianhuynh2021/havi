"""Bản tin buổi sáng — và chỗ nó cố ý im lặng.

Bản tin là màn của **chủ**, không phải hàng đợi của nhân viên: 24 giờ qua có gì,
còn gì phải xử lý, tuần tới chỗ nào trống lịch.

Nhóm test quan trọng nhất ở đây là `TestKhongBia`: nó khoá những thứ bản tin
**không được nói** vì Havi chưa đo được — doanh thu từ social, engagement theo
nền tảng, động thái đối thủ. Đó là ba câu hấp dẫn nhất trong mọi bản mô tả sản
phẩm loại này, và cũng là ba câu dễ thành lời nói dối nhất.
"""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.inbox_repository import InboxRepository
from core.enums import Channel, ContentStatus, InboxItemStatus, Platform, PublishStatus
from domain.models.content import ContentItem
from domain.models.publish import PublishJob
from domain.policies import brief as brief_policy


class TestPolicy:
    def test_bo_qua_hom_nay_khi_soi_cho_trong_lich(self):
        """Tới sáng nay mà chưa có bài thì đó không còn là chỗ trống để lấp — báo
        nó chỉ làm người đọc thấy một việc không làm được nữa."""
        today = date(2026, 8, 26)
        gaps = brief_policy.calendar_gaps(scheduled_dates=set(), today=today)
        assert today not in gaps
        assert gaps[0] == today + timedelta(days=1)

    def test_ngay_da_co_bai_khong_tinh_la_trong(self):
        today = date(2026, 8, 26)
        booked = today + timedelta(days=2)
        gaps = brief_policy.calendar_gaps(scheduled_dates={booked}, today=today)
        assert booked not in gaps
        assert len(gaps) == brief_policy.GAP_LOOKAHEAD_DAYS - 1

    def test_thu_trong_tuan_bang_tieng_viet(self):
        # 26/08/2026 là thứ Tư.
        assert brief_policy.weekday_name(date(2026, 8, 26)) == "Thứ Tư"

    def test_chi_dem_viec_havi_that_su_lam(self):
        """Chỉ hai dòng, và đó là chủ ý: phản hồi đã gửi và bài đã lên kênh là hai
        việc có bản ghi để đếm. "Phát hiện bài đăng lỗi" hay "khỏi mở 5 tab" là giá
        trị thật nhưng không có mốc nào để đo, nên không được biến thành phút."""
        actions = brief_policy.time_saved(replies_sent=10, posts_published=4)
        assert len(actions) == 2
        assert {action.action for action in actions} == {
            "Trả lời khách",
            "Đăng bài lên kênh",
        }

    def test_giu_dong_bang_khong_de_so_sanh_duoc_giua_cac_tuan(self):
        """Bảng chỉ hiện dòng khác 0 sẽ đổi hình mỗi tuần, và người đọc mất khả
        năng so tuần này với tuần trước."""
        actions = brief_policy.time_saved(replies_sent=0, posts_published=0)
        assert len(actions) == 2
        assert brief_policy.total_minutes_saved(actions) == 0

    def test_uoc_luong_de_dat_chu_khong_phong_dai(self):
        """Ước lượng thấp mà khách vẫn thấy đáng tiền thì con số đứng được; ước
        lượng cao thì khách tự đối chiếu với cảm giác của họ và mất niềm tin."""
        assert brief_policy.MINUTES_PER_REPLY <= 5
        assert brief_policy.MINUTES_PER_PUBLISH <= 5


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


async def test_workspace_moi_thi_ban_tin_toan_so_0_khong_bo_trong(client: AsyncClient):
    """Số 0 phải hiện, không được vắng: người đọc không phân biệt được "không có
    gì" với "chưa tải được" nếu con số biến mất."""
    token_pair = await _onboard(client, email="brief-empty@havi.vn")

    response = await client.get("/queue/brief", headers=_headers(token_pair))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["activity"] == {
        "published": 0,
        "inbox_received": 0,
        "replies_sent": 0,
        "publish_failed": 0,
    }
    assert body["attention_total"] == 0
    assert body["time_saved_minutes"] == 0
    # Workspace mới chưa xếp lịch gì nên cả bảy ngày tới đều trống.
    assert len(body["calendar_gaps"]) == brief_policy.GAP_LOOKAHEAD_DAYS


async def test_dem_dung_viec_da_xay_ra_trong_cua_so(
    client: AsyncClient, db_session: AsyncSession
):
    token_pair = await _onboard(client, email="brief-activity@havi.vn")
    workspace_id = UUID(token_pair["active_workspace_id"])
    now = datetime.now(UTC)

    published = ContentItem(
        workspace_id=workspace_id,
        channel=Channel.FACEBOOK_PAGE,
        kind="Bài ảnh",
        text="Ưu đãi cuối tuần",
        status=ContentStatus.PUBLISHED,
        published_at=now - timedelta(hours=2),
    )
    db_session.add(published)

    repo = InboxRepository(db_session)
    replied = await repo.create(
        workspace_id=workspace_id,
        platform=Platform.FACEBOOK,
        content="Cho em xin bảng giá phòng",
        author_name="Minh Anh",
    )
    await repo.update_status(replied, status=InboxItemStatus.SENT, now=now - timedelta(hours=1))
    await repo.create(
        workspace_id=workspace_id,
        platform=Platform.FACEBOOK,
        content="Đặt lịch giúp em",
        author_name="Thu Hà",
    )
    await db_session.flush()

    body = (await client.get("/queue/brief", headers=_headers(token_pair))).json()

    assert body["activity"]["published"] == 1
    assert body["activity"]["inbox_received"] == 2
    assert body["activity"]["replies_sent"] == 1
    # Một tin đặt lịch còn treo → thuộc nhóm bỏ sót thì tốn tiền.
    assert body["attention_costly"] == 1


async def test_thoi_gian_tiet_kiem_hien_ca_phep_tinh(
    client: AsyncClient, db_session: AsyncSession
):
    """Con số tổng mà không kèm giả định thì chỉ là quảng cáo. `minutes_each` phải
    có trong API để UI hiện ra được."""
    token_pair = await _onboard(client, email="brief-saved@havi.vn")
    workspace_id = UUID(token_pair["active_workspace_id"])
    now = datetime.now(UTC)
    repo = InboxRepository(db_session)

    for index in range(3):
        item = await repo.create(
            workspace_id=workspace_id,
            platform=Platform.FACEBOOK,
            content=f"Hỏi giá {index}",
            author_name="Khách",
        )
        await repo.update_status(item, status=InboxItemStatus.SENT, now=now)
    await db_session.flush()

    body = (await client.get("/queue/brief", headers=_headers(token_pair))).json()

    replies = next(a for a in body["time_saved_actions"] if a["action"] == "Trả lời khách")
    assert replies["count"] == 3
    assert replies["minutes_each"] == brief_policy.MINUTES_PER_REPLY
    assert replies["minutes_total"] == 3 * brief_policy.MINUTES_PER_REPLY
    assert body["time_saved_minutes"] == replies["minutes_total"]


async def test_cho_trong_lich_bo_ngay_da_co_bai(
    client: AsyncClient, db_session: AsyncSession
):
    token_pair = await _onboard(client, email="brief-gaps@havi.vn")
    workspace_id = UUID(token_pair["active_workspace_id"])

    scheduled_at = datetime.now(UTC) + timedelta(days=2)
    db_session.add(
        ContentItem(
            workspace_id=workspace_id,
            channel=Channel.FACEBOOK_PAGE,
            kind="Bài ảnh",
            text="Bài đã xếp lịch",
            status=ContentStatus.SCHEDULED,
            scheduled_at=scheduled_at,
        )
    )
    await db_session.flush()

    body = (await client.get("/queue/brief", headers=_headers(token_pair))).json()

    assert len(body["calendar_gaps"]) == brief_policy.GAP_LOOKAHEAD_DAYS - 1
    for gap in body["calendar_gaps"]:
        assert gap["weekday"] in brief_policy.WEEKDAY_NAMES


async def test_ban_tin_khong_lan_sang_workspace_khac(
    client: AsyncClient, db_session: AsyncSession
):
    token_a = await _onboard(client, email="brief-tenant-a@havi.vn")
    token_b = await _onboard(client, email="brief-tenant-b@havi.vn")

    await InboxRepository(db_session).create(
        workspace_id=UUID(token_b["active_workspace_id"]),
        platform=Platform.FACEBOOK,
        content="Cho em xin báo giá",
        author_name="Khách của B",
    )
    await db_session.flush()

    body = (await client.get("/queue/brief", headers=_headers(token_a))).json()
    assert body["activity"]["inbox_received"] == 0
    assert body["attention_total"] == 0


async def test_bai_dang_loi_vao_ca_hoat_dong_va_viec_cho_xu_ly(
    client: AsyncClient, db_session: AsyncSession
):
    token_pair = await _onboard(client, email="brief-failed@havi.vn")
    workspace_id = UUID(token_pair["active_workspace_id"])
    now = datetime.now(UTC)

    item = ContentItem(
        workspace_id=workspace_id,
        channel=Channel.FACEBOOK_PAGE,
        kind="Bài ảnh",
        text="Bài hỏng",
        status=ContentStatus.SCHEDULED,
    )
    db_session.add(item)
    await db_session.flush()
    db_session.add(
        PublishJob(
            workspace_id=workspace_id,
            content_item_id=item.id,
            channel=Channel.FACEBOOK_PAGE,
            idempotency_key=f"brief-{uuid4()}",
            status=PublishStatus.DEAD_LETTER,
            scheduled_at=now - timedelta(hours=3),
            updated_at=now - timedelta(hours=2),
            failure_detail="Rate limit",
        )
    )
    await db_session.flush()

    body = (await client.get("/queue/brief", headers=_headers(token_pair))).json()

    assert body["activity"]["publish_failed"] == 1
    assert body["attention_total"] >= 1


class TestKhongBia:
    """Chỗ bản tin cố ý im lặng.

    Ba con số dưới đây là ba câu hấp dẫn nhất trong mọi bản mô tả "AI social
    manager", và Havi **không đo được** cái nào: không có dữ liệu đơn hàng, chưa
    có quyền đọc insights của nền tảng, không có nguồn dữ liệu đối thủ. Thiếu thì
    để trống, không đoán.
    """

    async def test_khong_co_truong_nao_ve_doanh_thu(self, client: AsyncClient):
        token_pair = await _onboard(client, email="brief-no-revenue@havi.vn")
        body = (await client.get("/queue/brief", headers=_headers(token_pair))).json()

        flat = str(body).lower()
        for banned in ("revenue", "doanh_thu", "doanh thu", "conversion", "roi"):
            assert banned not in flat, f"bản tin không được nói về {banned}"

    async def test_khong_co_truong_nao_ve_engagement_hay_doi_thu(self, client: AsyncClient):
        token_pair = await _onboard(client, email="brief-no-engagement@havi.vn")
        body = (await client.get("/queue/brief", headers=_headers(token_pair))).json()

        flat = str(body).lower()
        for banned in ("engagement", "competitor", "doi_thu", "follower", "reach"):
            assert banned not in flat, f"bản tin không được nói về {banned}"

    async def test_khong_goi_llm_nen_khong_ton_token(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Một bản tin LLM mỗi sáng cho mỗi workspace là một dòng chi phí chạy
        mãi. Bản tin này đếm bằng SQL, nên nó không ghi thêm event token nào."""
        from adapters.persistence.event_log_repository import EventLogRepository

        token_pair = await _onboard(client, email="brief-no-tokens@havi.vn")
        workspace_id = UUID(token_pair["active_workspace_id"])
        events = EventLogRepository(db_session)
        before = await events.tokens_used_since(
            workspace_id=workspace_id, since=datetime.now(UTC) - timedelta(days=1)
        )

        await client.get("/queue/brief", headers=_headers(token_pair))

        after = await events.tokens_used_since(
            workspace_id=workspace_id, since=datetime.now(UTC) - timedelta(days=1)
        )
        assert after == before
