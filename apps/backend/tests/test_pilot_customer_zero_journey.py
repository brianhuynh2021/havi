"""Hành trình vận hành thật của Customer Zero (Trung Tâm Nhật Minh).

Bản trước test vòng lặp Goal → Roadmap → Evidence → Review. Tầng đó đã được gỡ
khỏi sản phẩm ngày 2026-08-25 vì nó quản trị *mục tiêu kinh doanh của khách*,
không phải *hệ thống social của khách*.

Bộ test này thay bằng đúng thứ Havi làm: tạo workspace → soạn nội dung → duyệt →
xếp lịch → theo dõi trạng thái, và tin khách nhắn tới thì không bị rơi.

Vì sao giữ một test "hành trình" bên cạnh các test đơn lẻ đã có: từng bước đều
xanh không có nghĩa là **nối lại với nhau** vẫn xanh. Chỗ đứt thường nằm ở giao
giữa hai tầng — workspace vừa tạo chưa active, quota chưa cấp, bài duyệt xong
không xuất hiện ở lịch.
"""

import json
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.llm.fake import FakeProvider
from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from application.services.content_engine import ContentEngine
from domain.policies.provider_router import ProviderRouter

#: Ba bản nháp Facebook — đủ để kiểm việc rải lịch cho nhiều bài.
_DRAFTS = json.dumps(
    {
        "drafts": [
            {
                "channel": "facebook_page",
                "kind": "Bài viết",
                "text": f"Khai giảng lớp Lập trình AI — buổi {i}",
                "media_note": None,
            }
            for i in (1, 2, 3)
        ]
    }
)


def _engine(session: AsyncSession) -> ContentEngine:
    """LLM giả: hành trình này kiểm luồng nghiệp vụ, không kiểm chất lượng câu chữ."""
    provider = FakeProvider(response_text=_DRAFTS)
    return ContentEngine(
        content=ContentRepository(session),
        workspaces=WorkspaceRepository(session),
        profiles=BrandProfileRepository(session),
        media=MediaRepository(session),
        events=EventLogRepository(session),
        router=ProviderRouter({provider.provider: provider}),
    )


async def _signup_and_get_workspace(
    client: AsyncClient, *, email: str, name: str, ws_name: str, industry: str
):
    signup = await client.post(
        "/auth/sign-up", json={"name": name, "email": email, "password": "matkhau123"}
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()
    headers = {"Authorization": f"Bearer {token_pair['access_token']}"}

    create_ws = await client.post(
        "/workspaces",
        json={"name": ws_name, "industry": industry},
        headers=headers,
    )
    assert create_ws.status_code == 201, create_ws.text
    ws_id = create_ws.json()["id"]

    # Token cũ chưa mang `active_workspace_id` — phải refresh, nếu không mọi
    # request sau đó đều 403. Đây đúng là chỗ đứt mà test từng bước không thấy.
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new_headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    return new_headers, ws_id


async def test_hanh_trinh_soan_duyet_xep_lich_cua_customer_zero(
    client: AsyncClient, db_session: AsyncSession
):
    """Từ lúc đăng ký tới lúc bài nằm trong lịch chờ đăng."""
    headers, ws_id = await _signup_and_get_workspace(
        client,
        email="nhatminh_c0@havi.vn",
        name="Thầy Minh (Customer Zero)",
        ws_name="Trung Tâm Công Nghệ Nhật Minh",
        industry="education",
    )

    # 1. Tổng quan lúc mới tinh: mọi ô bằng 0, không có số liệu mẫu nào.
    dashboard = await client.get("/analytics/dashboard", headers=headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["published"] == 0
    assert dashboard.json()["pending_approval"] == 0

    # 2. Soạn nội dung từ vài dòng ghi chú.
    job = await client.post(
        "/content/jobs",
        json={
            "raw_inputs": [
                {"kind": "text", "text": "Khai giảng lớp Lập trình AI cho học sinh cấp 3"}
            ],
            "idempotency_key": "pilot-c0-job-1",
            "channels": ["facebook_page"],
        },
        headers=headers,
    )
    # 202 = đã xếp hàng. Worker chạy ngầm ở production; trong test gọi thẳng
    # engine để hành trình không phụ thuộc vào Redis/Celery.
    assert job.status_code == 202, job.text
    await _engine(db_session).generate_drafts(
        workspace_id=UUID(job.json()["workspace_id"]), job_id=UUID(job.json()["id"])
    )

    # 3. Bản nháp phải nằm ở hàng chờ duyệt — không tự lên Trang.
    pending = await client.get("/content", headers=headers, params={"status": "pending_approval"})
    assert pending.status_code == 200, pending.text
    items = pending.json()["items"]
    assert items, "job chạy xong phải sinh ra ít nhất một bản nháp"
    assert all(item["status"] == "pending_approval" for item in items)

    # 4. Duyệt cả loạt, rải lịch — KHÔNG đăng ngay.
    approve = await client.post(
        "/content/approve-all",
        json={
            "content_item_ids": [item["id"] for item in items],
            "publish_now": False,
            "posts_per_day": 1,
        },
        headers=headers,
    )
    assert approve.status_code == 200, approve.text
    approved_ids = approve.json()["approved"]
    assert approved_ids

    # 5. Mỗi bài nhận một mốc giờ RIÊNG — đây là điểm khiến "chuẩn bị cả tuần
    #    nội dung trong một buổi" có nghĩa. Dồn tất cả vào một phút là spam.
    scheduled = await client.get("/content", headers=headers, params={"status": "approved"})
    assert scheduled.status_code == 200
    stamps = [item["scheduled_at"] for item in scheduled.json()["items"]]
    assert all(stamps), "bài đã duyệt phải có giờ đăng"
    assert len(set(stamps)) == len(stamps), "không bài nào được trùng giờ với bài khác"

    # 6. Tổng quan phản ánh đúng việc vừa làm.
    after = await client.get("/analytics/dashboard", headers=headers)
    assert after.json()["scheduled"] >= len(approved_ids)
    assert after.json()["published"] == 0, "chưa tới giờ thì chưa có bài nào đã đăng"


async def test_tin_khach_nhan_toi_khong_bi_roi(client: AsyncClient):
    """Khách nhắn hỏi giá → vào hộp thư, và KHÔNG tự trả lời khi chưa ai duyệt.

    Đây là ràng buộc đắt nhất của sản phẩm: câu trả lời tự động là đường duy
    nhất trong Havi đi tới người ngoài. Nói sai với khách thì không rút lại được.
    """
    headers, ws_id = await _signup_and_get_workspace(
        client,
        email="resort_pilot@havi.vn",
        name="Quản lý Resort",
        ws_name="Boutique Resort Ven Biển",
        industry="other",
    )

    inbound = await client.post(
        f"/webhooks/dev/simulate?workspace_id={ws_id}",
        json={
            "platform": "facebook",
            "author_name": "Khách Lan",
            "content": "Phòng view biển cuối tuần này còn không shop?",
            "external_message_id": "pilot-msg-1",
        },
        headers=headers,
    )
    assert inbound.status_code == 200, inbound.text

    inbox = await client.get("/inbox", headers=headers)
    assert inbox.status_code == 200, inbox.text
    items = inbox.json()["items"]
    assert len(items) == 1

    # Không khớp FAQ đã duyệt → phải là bản nháp chờ người, không phải đã gửi.
    assert items[0]["status"] != "sent", "không được tự trả lời khách khi chưa ai duyệt"

    # Webhook gửi lại cùng một message_id không được đẻ thêm tin nhắn khách.
    again = await client.post(
        f"/webhooks/dev/simulate?workspace_id={ws_id}",
        json={
            "platform": "facebook",
            "author_name": "Khách Lan",
            "content": "Phòng view biển cuối tuần này còn không shop?",
            "external_message_id": "pilot-msg-1",
        },
        headers=headers,
    )
    assert again.status_code == 200
    assert len((await client.get("/inbox", headers=headers)).json()["items"]) == 1
