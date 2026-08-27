"""Test vòng sửa → duyệt → lên lịch trên Postgres thật (ROADMAP Tuần 6).

Đây là vòng khoá nguyên tắc #1 của Havi: không bài nào lên mạng khi chủ chưa
duyệt. Nên test ở đây không chỉ kiểm "API trả 200" mà kiểm cả những đường vòng —
duyệt hai lần, duyệt bài của workspace khác, đổi giờ bài đã đăng.

Draft được tạo trực tiếp qua repository thay vì chạy Content Engine: phần sinh
draft đã có `test_content_flow.py` lo, ở đây chỉ cần một item đúng trạng thái.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.content_repository import ContentRepository
from core.enums import Channel, ContentStatus
from domain.models.audit import EventLog
from domain.models.content import ContentItem
from domain.policies.scheduling import VIETNAM_TZ, next_golden_hour


async def _onboard(client: AsyncClient, *, email: str) -> dict:
    signup = await client.post(
        "/auth/sign-up", json={"name": "Chị Hương", "email": email, "password": "matkhau123"}
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()
    create = await client.post(
        "/workspaces",
        json={"name": "Spa An Nhiên", "industry": "spa"},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert create.status_code == 201, create.text
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    return refreshed.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


async def _draft(
    session: AsyncSession,
    token_pair: dict,
    *,
    status: ContentStatus = ContentStatus.PENDING_APPROVAL,
    text: str = "Gội đầu thảo dược cuối tuần có ưu đãi nha chị.",
) -> ContentItem:
    item = await ContentRepository(session).create_item(
        workspace_id=UUID(token_pair["active_workspace_id"]),
        job_id=None,
        channel=Channel.FACEBOOK_PAGE,
        kind="Bài ảnh",
        text=text,
        media_note=None,
        status=status,
    )
    return item


# --- Sửa draft và version history ------------------------------------------


async def test_sua_text_tao_version_moi_khong_ghi_de(client: AsyncClient, db_session: AsyncSession):
    token_pair = await _onboard(client, email="a1@havi.vn")
    item = await _draft(db_session, token_pair, text="Bản gốc của Havi")

    response = await client.patch(
        f"/content/{item.id}",
        json={"text": "Bản chị Hương sửa lại cho gần gũi hơn"},
        headers=_headers(token_pair),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["text"] == "Bản chị Hương sửa lại cho gần gũi hơn"
    assert body["version_no"] == 2

    versions = await client.get(f"/content/{item.id}/versions", headers=_headers(token_pair))
    rows = versions.json()
    assert len(rows) == 1
    assert rows[0]["version_no"] == 2
    assert rows[0]["text"] == "Bản chị Hương sửa lại cho gần gũi hơn"
    # Audit phải trả lời được "ai sửa" — không chỉ "đã sửa".
    assert rows[0]["edited_by"] is not None

    # Trajectory audit event được ghi vào event_log
    events_res = await client.get("/analytics/events?job_kind=content.edit", headers=_headers(token_pair))
    assert events_res.status_code == 200
    ev_items = events_res.json()["items"]
    assert len(ev_items) == 1
    assert "v2" in ev_items[0]["input_summary"]


async def test_patch_khong_gui_text_thi_khong_tang_version(
    client: AsyncClient, db_session: AsyncSession
):
    """PATCH là partial update: đổi mỗi media_note không được đẻ ra version rỗng."""
    token_pair = await _onboard(client, email="a2@havi.vn")
    item = await _draft(db_session, token_pair)

    response = await client.patch(
        f"/content/{item.id}",
        json={"media_note": "Chụp lúc đang gội"},
        headers=_headers(token_pair),
    )

    assert response.status_code == 200
    assert response.json()["version_no"] == 1
    assert response.json()["media_note"] == "Chụp lúc đang gội"
    versions = await client.get(f"/content/{item.id}/versions", headers=_headers(token_pair))
    assert versions.json() == []


async def test_sua_text_giong_het_ban_cu_khong_tao_version(
    client: AsyncClient, db_session: AsyncSession
):
    token_pair = await _onboard(client, email="a3@havi.vn")
    item = await _draft(db_session, token_pair, text="Y hệt")

    await client.patch(f"/content/{item.id}", json={"text": "Y hệt"}, headers=_headers(token_pair))
    versions = await client.get(f"/content/{item.id}/versions", headers=_headers(token_pair))
    assert versions.json() == []


async def test_khong_sua_duoc_bai_da_dang(client: AsyncClient, db_session: AsyncSession):
    """Sửa bài đã lên Facebook làm DB và bản thật lệch nhau — audit trail nói dối."""
    token_pair = await _onboard(client, email="a4@havi.vn")
    item = await _draft(db_session, token_pair, status=ContentStatus.PUBLISHED)

    response = await client.patch(
        f"/content/{item.id}", json={"text": "sửa lén"}, headers=_headers(token_pair)
    )
    assert response.status_code == 409


# --- Duyệt lẻ ---------------------------------------------------------------


async def test_duyet_le_ghi_approved_by_va_len_lich(client: AsyncClient, db_session: AsyncSession):
    token_pair = await _onboard(client, email="a5@havi.vn")
    item = await _draft(db_session, token_pair)
    when = datetime.now(UTC) + timedelta(days=1)

    response = await client.post(
        f"/content/{item.id}/approve",
        json={"scheduled_at": when.isoformat()},
        headers=_headers(token_pair),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["approved_by"] is not None
    assert body["approved_at"] is not None
    assert datetime.fromisoformat(body["scheduled_at"]) == when


async def test_duyet_khong_chon_gio_thi_havi_chon_khung_gio_vang(
    client: AsyncClient, db_session: AsyncSession
):
    """Chủ tiệm bấm "Duyệt" mà không chọn giờ — backend phải tự chọn giờ VN hợp lý."""
    token_pair = await _onboard(client, email="a6@havi.vn")
    item = await _draft(db_session, token_pair)

    response = await client.post(
        f"/content/{item.id}/approve", json={}, headers=_headers(token_pair)
    )

    assert response.status_code == 200
    scheduled = datetime.fromisoformat(response.json()["scheduled_at"])
    assert scheduled > datetime.now(UTC)
    assert scheduled.astimezone(VIETNAM_TZ).hour in {8, 12, 20}


async def test_duyet_hai_lan_thi_lan_hai_tra_409(client: AsyncClient, db_session: AsyncSession):
    """Double-click nút Duyệt không được ghi đè `approved_by` của lần đầu."""
    token_pair = await _onboard(client, email="a7@havi.vn")
    item = await _draft(db_session, token_pair)

    first = await client.post(f"/content/{item.id}/approve", json={}, headers=_headers(token_pair))
    second = await client.post(f"/content/{item.id}/approve", json={}, headers=_headers(token_pair))

    assert first.status_code == 200
    assert second.status_code == 409


async def test_khong_duyet_duoc_bai_da_dang(client: AsyncClient, db_session: AsyncSession):
    token_pair = await _onboard(client, email="a8@havi.vn")
    item = await _draft(db_session, token_pair, status=ContentStatus.PUBLISHED)

    response = await client.post(
        f"/content/{item.id}/approve", json={}, headers=_headers(token_pair)
    )
    assert response.status_code == 409


async def test_tu_choi_dua_bai_ve_draft(client: AsyncClient, db_session: AsyncSession):
    token_pair = await _onboard(client, email="a9@havi.vn")
    item = await _draft(db_session, token_pair)

    response = await client.post(f"/content/{item.id}/reject", headers=_headers(token_pair))

    assert response.status_code == 200
    assert response.json()["status"] == "draft"
    # Từ chối là để sửa lại, không phải xoá.
    assert response.json()["text"]


async def test_khong_duyet_duoc_bai_cua_workspace_khac(
    client: AsyncClient, db_session: AsyncSession
):
    """Biết UUID của bài người khác cũng không duyệt được — 404, không lộ tồn tại."""
    token_a = await _onboard(client, email="a10@havi.vn")
    token_b = await _onboard(client, email="a11@havi.vn")
    item = await _draft(db_session, token_a)

    response = await client.post(f"/content/{item.id}/approve", json={}, headers=_headers(token_b))
    assert response.status_code == 404


# --- Duyệt hàng loạt --------------------------------------------------------


async def test_duyet_het_duyet_duoc_bai_hop_le_va_bao_ly_do_bai_hong(
    client: AsyncClient, db_session: AsyncSession
):
    """Một bài hỏng không được làm fail cả lô — chủ tiệm bấm "Duyệt & đăng hết"."""
    token_pair = await _onboard(client, email="a12@havi.vn")
    ok_one = await _draft(db_session, token_pair)
    ok_two = await _draft(db_session, token_pair)
    already_published = await _draft(db_session, token_pair, status=ContentStatus.PUBLISHED)

    response = await client.post(
        "/content/approve-all",
        json={
            "content_item_ids": [
                str(ok_one.id),
                str(already_published.id),
                str(ok_two.id),
            ]
        },
        headers=_headers(token_pair),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body["approved"]) == {str(ok_one.id), str(ok_two.id)}
    assert len(body["rejected"]) == 1
    assert body["rejected"][0]["content_item_id"] == str(already_published.id)
    assert body["rejected"][0]["reason"]


async def test_duyet_het_bo_qua_id_khong_thuoc_workspace(
    client: AsyncClient, db_session: AsyncSession
):
    token_a = await _onboard(client, email="a13@havi.vn")
    token_b = await _onboard(client, email="a14@havi.vn")
    mine = await _draft(db_session, token_a)
    theirs = await _draft(db_session, token_b)

    response = await client.post(
        "/content/approve-all",
        json={"content_item_ids": [str(mine.id), str(theirs.id)]},
        headers=_headers(token_a),
    )

    body = response.json()
    assert body["approved"] == [str(mine.id)]
    assert [r["content_item_id"] for r in body["rejected"]] == [str(theirs.id)]

    # Bài của workspace B phải nguyên trạng — không bị duyệt ké.
    stored = await ContentRepository(db_session).get_item(
        workspace_id=UUID(token_b["active_workspace_id"]), item_id=theirs.id
    )
    assert stored is not None and stored.status == ContentStatus.PENDING_APPROVAL


# --- Calendar và reschedule -------------------------------------------------


async def test_bai_da_duyet_hien_dung_ngay_tren_lich(client: AsyncClient, db_session: AsyncSession):
    """Lịch gom theo ngày Việt Nam: 8h sáng VN = 1h sáng UTC cùng ngày."""
    token_pair = await _onboard(client, email="a15@havi.vn")
    item = await _draft(db_session, token_pair)
    when = datetime(2026, 9, 15, 8, 0, tzinfo=VIETNAM_TZ)

    await client.post(
        f"/content/{item.id}/approve",
        json={"scheduled_at": when.isoformat()},
        headers=_headers(token_pair),
    )
    response = await client.get(
        "/calendar",
        params={"start": "2026-09-14", "end": "2026-09-20"},
        headers=_headers(token_pair),
    )

    assert response.status_code == 200, response.text
    days = {d["date"]: d["items"] for d in response.json()["days"]}
    assert len(days) == 7, "phải trả đủ 7 ô, kể cả ngày rỗng"
    assert [i["id"] for i in days["2026-09-15"]] == [str(item.id)]
    assert days["2026-09-14"] == []


async def test_bai_dat_luc_6h_sang_vn_khong_roi_sang_ngay_hom_truoc(
    client: AsyncClient, db_session: AsyncSession
):
    """6h sáng 15/9 giờ VN là 23h 14/9 UTC — gom theo UTC sẽ hiện sai ô trên lịch."""
    token_pair = await _onboard(client, email="a16@havi.vn")
    item = await _draft(db_session, token_pair)
    when = datetime(2026, 9, 15, 6, 0, tzinfo=VIETNAM_TZ)

    await client.post(
        f"/content/{item.id}/approve",
        json={"scheduled_at": when.isoformat()},
        headers=_headers(token_pair),
    )
    response = await client.get(
        "/calendar",
        params={"start": "2026-09-15", "end": "2026-09-15"},
        headers=_headers(token_pair),
    )

    days = {d["date"]: d["items"] for d in response.json()["days"]}
    assert [i["id"] for i in days["2026-09-15"]] == [str(item.id)]


async def test_lich_khong_thay_bai_cua_workspace_khac(
    client: AsyncClient, db_session: AsyncSession
):
    token_a = await _onboard(client, email="a17@havi.vn")
    token_b = await _onboard(client, email="a18@havi.vn")
    item = await _draft(db_session, token_a)
    await client.post(
        f"/content/{item.id}/approve",
        json={"scheduled_at": datetime(2026, 9, 15, 8, 0, tzinfo=VIETNAM_TZ).isoformat()},
        headers=_headers(token_a),
    )

    response = await client.get(
        "/calendar",
        params={"start": "2026-09-15", "end": "2026-09-15"},
        headers=_headers(token_b),
    )
    assert all(day["items"] == [] for day in response.json()["days"])


async def test_doi_gio_dang_bai_da_duyet(client: AsyncClient, db_session: AsyncSession):
    token_pair = await _onboard(client, email="a19@havi.vn")
    item = await _draft(db_session, token_pair, status=ContentStatus.SCHEDULED)
    when = datetime(2026, 9, 20, 20, 0, tzinfo=VIETNAM_TZ)

    response = await client.post(
        f"/calendar/{item.id}/reschedule",
        json={"scheduled_at": when.isoformat()},
        headers=_headers(token_pair),
    )

    assert response.status_code == 200, response.text
    assert datetime.fromisoformat(response.json()["scheduled_at"]) == when
    # Đổi giờ không được đổi trạng thái.
    assert response.json()["status"] == "scheduled"


async def test_khong_doi_duoc_gio_bai_da_dang(client: AsyncClient, db_session: AsyncSession):
    token_pair = await _onboard(client, email="a20@havi.vn")
    item = await _draft(db_session, token_pair, status=ContentStatus.PUBLISHED)

    response = await client.post(
        f"/calendar/{item.id}/reschedule",
        json={"scheduled_at": datetime.now(UTC).isoformat()},
        headers=_headers(token_pair),
    )
    assert response.status_code == 409


async def test_lich_khoang_qua_dai_bi_tu_choi(client: AsyncClient):
    token_pair = await _onboard(client, email="a21@havi.vn")
    response = await client.get(
        "/calendar",
        params={"start": "2026-01-01", "end": "2027-01-01"},
        headers=_headers(token_pair),
    )
    assert response.status_code == 422


# --- Timezone round-trip ----------------------------------------------------


async def test_gio_dang_luu_dung_moc_utc_khong_bi_nuot_offset(
    client: AsyncClient, db_session: AsyncSession
):
    """Cột naive sẽ lưu 20h thành 20h UTC (3h sáng VN hôm sau) — test này bắt lỗi đó."""
    token_pair = await _onboard(client, email="a22@havi.vn")
    item = await _draft(db_session, token_pair)
    when = datetime(2026, 9, 15, 20, 0, tzinfo=VIETNAM_TZ)

    await client.post(
        f"/content/{item.id}/approve",
        json={"scheduled_at": when.isoformat()},
        headers=_headers(token_pair),
    )

    stored = (
        await db_session.execute(select(ContentItem).where(ContentItem.id == item.id))
    ).scalar_one()
    assert stored.scheduled_at is not None
    assert stored.scheduled_at == when
    assert stored.scheduled_at.astimezone(UTC).hour == 13  # 20h VN = 13h UTC


# --- Audit ------------------------------------------------------------------


async def test_duyet_va_doi_lich_deu_ghi_event_log(client: AsyncClient, db_session: AsyncSession):
    """Definition of Done §7: hành động nhạy cảm phải có audit event."""
    token_pair = await _onboard(client, email="a23@havi.vn")
    workspace_id = UUID(token_pair["active_workspace_id"])
    item = await _draft(db_session, token_pair)

    await client.post(f"/content/{item.id}/approve", json={}, headers=_headers(token_pair))
    await client.post(
        f"/calendar/{item.id}/reschedule",
        json={"scheduled_at": datetime(2026, 9, 20, 20, 0, tzinfo=VIETNAM_TZ).isoformat()},
        headers=_headers(token_pair),
    )

    rows = (
        (await db_session.execute(select(EventLog).where(EventLog.workspace_id == workspace_id)))
        .scalars()
        .all()
    )
    kinds = [r.job_kind for r in rows]
    assert "content.approve" in kinds
    assert "content.reschedule" in kinds
    approve_row = next(r for r in rows if r.job_kind == "content.approve")
    assert str(item.id) in approve_row.input_summary


# --- Chính sách chọn giờ vàng ----------------------------------------------


@pytest.mark.parametrize(
    ("now_vn", "expected_vn"),
    [
        # Trước khung đầu tiên → 8h cùng ngày.
        (datetime(2026, 9, 15, 6, 30, tzinfo=VIETNAM_TZ), datetime(2026, 9, 15, 8, 0)),
        # Giữa hai khung → khung kế tiếp.
        (datetime(2026, 9, 15, 9, 0, tzinfo=VIETNAM_TZ), datetime(2026, 9, 15, 12, 0)),
        # Qua khung cuối → 8h sáng hôm sau, không phải 20h hôm nay đã trôi qua.
        (datetime(2026, 9, 15, 21, 0, tzinfo=VIETNAM_TZ), datetime(2026, 9, 16, 8, 0)),
    ],
)
def test_khung_gio_vang_luon_o_tuong_lai(now_vn: datetime, expected_vn: datetime):
    result = next_golden_hour(now=now_vn)
    assert result > now_vn
    assert result.astimezone(VIETNAM_TZ).replace(tzinfo=None) == expected_vn


# --- Xoá bỏ / Dismiss & Hoãn về nháp ---------------------------------------


async def test_dismiss_item_chuyen_sang_dismissed_va_an_khoi_list(
    client: AsyncClient, db_session: AsyncSession
):
    token_pair = await _onboard(client, email="dismiss1@havi.vn")
    item = await _draft(db_session, token_pair)

    # Dismiss item
    resp = await client.post(f"/content/{item.id}/dismiss", headers=_headers(token_pair))
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"

    # Verify that it is filtered out of default list_content
    list_resp = await client.get("/content", headers=_headers(token_pair))
    assert list_resp.status_code == 200
    item_ids = [i["id"] for i in list_resp.json()["items"]]
    assert str(item.id) not in item_ids


async def test_dismiss_all_xoa_hang_loat(client: AsyncClient, db_session: AsyncSession):
    token_pair = await _onboard(client, email="dismiss_all@havi.vn")
    item1 = await _draft(db_session, token_pair)
    item2 = await _draft(db_session, token_pair)

    resp = await client.post(
        "/content/dismiss-all",
        json={"content_item_ids": [str(item1.id), str(item2.id)]},
        headers=_headers(token_pair),
    )
    assert resp.status_code == 200
    assert len(resp.json()["dismissed"]) == 2

    # Verify both are filtered out
    list_resp = await client.get("/content", headers=_headers(token_pair))
    assert list_resp.status_code == 200
    assert list_resp.json()["items"] == []


async def test_hoan_bai_tren_lich_ve_nhap_xoa_scheduled_at(
    client: AsyncClient, db_session: AsyncSession
):
    token_pair = await _onboard(client, email="unschedule1@havi.vn")
    item = await _draft(db_session, token_pair)

    # Approve and schedule
    when = datetime.now(UTC) + timedelta(days=2)
    approve_resp = await client.post(
        f"/content/{item.id}/approve",
        json={"scheduled_at": when.isoformat()},
        headers=_headers(token_pair),
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "scheduled"

    # Reject / Unschedule to draft
    reject_resp = await client.post(f"/content/{item.id}/reject", headers=_headers(token_pair))
    assert reject_resp.status_code == 200
    body = reject_resp.json()
    assert body["status"] == "draft"
    assert body["scheduled_at"] is None


async def test_update_item_media_url_va_xoa_anh(client: AsyncClient, db_session: AsyncSession):
    token_pair = await _onboard(client, email="editmedia1@havi.vn")
    item = await _draft(db_session, token_pair)

    # Set custom media url
    patch_resp = await client.patch(
        f"/content/{item.id}",
        json={"media_url": "https://example.com/my-uploaded-photo.jpg"},
        headers=_headers(token_pair),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["media_url"] == "https://example.com/my-uploaded-photo.jpg"

    # Remove photo (__NONE__)
    remove_resp = await client.patch(
        f"/content/{item.id}",
        json={"media_url": "__NONE__"},
        headers=_headers(token_pair),
    )
    assert remove_resp.status_code == 200
    assert remove_resp.json()["media_url"] is None
