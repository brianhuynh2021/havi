"""Bài người dùng tự viết: Havi không sửa một chữ, và không lách bước duyệt.

Vì sao có đường riêng
---------------------
`POST /content/jobs` là nút "Để Havi viết bài" — nó luôn gọi LLM. Người đã có bài
hoàn chỉnh (viết ở nơi khác, dán vào) mà buộc đi đường đó thì phải nhờ Havi viết
một bản không ai cần, tốn quota, rồi ghi đè bài của mình lên. Đó là lý do
`POST /content/items` tồn tại.

Hai điều các test dưới đây giữ:

1. Không có model nào chạm vào chữ người dùng, và không tốn quota.
2. `publish_mode` vẫn quyết định trạng thái đầu tiên. Bật `review_first` nghĩa là
   muốn mọi bài đều qua người duyệt — bất kể ai viết ra nó.
"""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from core.enums import ContentStatus, PublishMode
from domain.models.content import ContentItem

BAI_HOAN_CHINH = (
    "Cuối tuần này tiệm giảm 20% gội đầu thảo dược. Nhắn tin để giữ chỗ nha chị."
)


async def _onboard(client: AsyncClient, *, email: str) -> dict:
    signup = await client.post(
        "/auth/sign-up", json={"name": "Chị Hương", "email": email, "password": "matkhau123"}
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()
    created = await client.post(
        "/workspaces",
        json={"name": "Spa An Nhiên", "industry": "spa"},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert created.status_code == 201, created.text
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    return refreshed.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


async def test_bai_tu_viet_vao_hang_cho_nguyen_van_khong_goi_llm(
    client: AsyncClient, db_session: AsyncSession
):
    """201 chứ không 202: không có gì để chờ, vì không có model nào chạy."""
    token_pair = await _onboard(client, email="own1@havi.vn")

    response = await client.post(
        "/content/items",
        json={"text": BAI_HOAN_CHINH, "channel": "facebook_page"},
        headers=_headers(token_pair),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["text"] == BAI_HOAN_CHINH, "Havi không được sửa một chữ nào"
    assert body["status"] == ContentStatus.PENDING_APPROVAL.value
    assert body["job_id"] is None, "không có job vì không có lần gọi LLM nào"


async def test_bai_tu_viet_khong_tao_ban_v1_cua_may(
    client: AsyncClient, db_session: AsyncSession
):
    """Chữ người viết không phải "bản AI" — bỏ vào tập học giọng văn là học nhiễu."""
    token_pair = await _onboard(client, email="own2@havi.vn")
    response = await client.post(
        "/content/items",
        json={"text": BAI_HOAN_CHINH},
        headers=_headers(token_pair),
    )
    assert response.status_code == 201, response.text
    item_id = UUID(response.json()["id"])

    versions = await ContentRepository(db_session).list_versions(item_id)
    assert versions == [], "bài tự viết không có bản máy nào để lưu"

    workspace_id = UUID(response.json()["workspace_id"])
    pairs = await ContentRepository(db_session).list_ai_human_pairs(workspace_id=workspace_id)
    assert pairs == [], "không được dạy nắn giọng văn theo chính giọng người dùng"


async def test_ton_trong_publish_mode_full_auto(
    client: AsyncClient, db_session: AsyncSession
):
    """`full_auto` thì vào SCHEDULED — cùng luật với bài AI viết, không có ngoại lệ."""
    token_pair = await _onboard(client, email="own3@havi.vn")
    workspace_id = UUID(token_pair["active_workspace_id"])
    workspaces = WorkspaceRepository(db_session)
    workspace = await workspaces.get_by_id(workspace_id)
    assert workspace is not None
    workspace.publish_mode = PublishMode.FULL_AUTO
    await db_session.flush()

    response = await client.post(
        "/content/items",
        json={"text": BAI_HOAN_CHINH},
        headers=_headers(token_pair),
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == ContentStatus.SCHEDULED.value


async def test_review_first_khong_bi_lach_qua_duong_tu_viet(
    client: AsyncClient, db_session: AsyncSession
):
    """Hồi quy của chính rủi ro: đường mới không được thành cửa sau bỏ duyệt."""
    token_pair = await _onboard(client, email="own4@havi.vn")
    workspace_id = UUID(token_pair["active_workspace_id"])
    workspace = await WorkspaceRepository(db_session).get_by_id(workspace_id)
    assert workspace is not None
    assert workspace.publish_mode is PublishMode.REVIEW_FIRST, "mặc định phải là duyệt trước"

    await client.post(
        "/content/items", json={"text": BAI_HOAN_CHINH}, headers=_headers(token_pair)
    )

    rows = await db_session.execute(
        select(ContentItem).where(ContentItem.workspace_id == workspace_id)
    )
    items = list(rows.scalars().all())
    assert items, "phải có bài vừa tạo"
    assert all(item.status is ContentStatus.PENDING_APPROVAL for item in items)
    assert all(item.published_at is None for item in items)


async def test_kenh_chua_mo_bi_tu_choi(client: AsyncClient):
    """Cưỡng chế `LIVE_CHANNELS` ở cả đường này, không chỉ ở `/content/jobs`."""
    token_pair = await _onboard(client, email="own5@havi.vn")

    response = await client.post(
        "/content/items",
        json={"text": BAI_HOAN_CHINH, "channel": "tiktok"},
        headers=_headers(token_pair),
    )

    assert response.status_code == 422, response.text
    assert "chưa mở" in response.json()["detail"]


async def test_bai_rong_bi_tu_choi(client: AsyncClient):
    token_pair = await _onboard(client, email="own6@havi.vn")
    response = await client.post(
        "/content/items", json={"text": ""}, headers=_headers(token_pair)
    )
    assert response.status_code == 422


async def test_anh_khong_ton_tai_tra_404(client: AsyncClient):
    """Không tạo bài với ảnh không có: bài sẽ hỏng lúc đăng, xa chỗ gây ra lỗi."""
    token_pair = await _onboard(client, email="own7@havi.vn")
    response = await client.post(
        "/content/items",
        json={"text": BAI_HOAN_CHINH, "media_id": str(uuid4())},
        headers=_headers(token_pair),
    )
    assert response.status_code == 404


# --- Preview ----------------------------------------------------------------


async def test_preview_khong_ghi_gi_vao_db(client: AsyncClient, db_session: AsyncSession):
    """Người dùng gõ và xem lại nhiều lần — mỗi lần một hàng rác thì hàng chờ đầy."""
    token_pair = await _onboard(client, email="prev1@havi.vn")
    workspace_id = UUID(token_pair["active_workspace_id"])

    for _ in range(3):
        response = await client.post(
            "/content/preview",
            json={"text": BAI_HOAN_CHINH},
            headers=_headers(token_pair),
        )
        assert response.status_code == 200, response.text

    rows = await db_session.execute(
        select(ContentItem).where(ContentItem.workspace_id == workspace_id)
    )
    assert list(rows.scalars().all()) == []


async def test_preview_bai_ngan_khong_canh_bao_va_khong_cat(client: AsyncClient):
    token_pair = await _onboard(client, email="prev2@havi.vn")
    response = await client.post(
        "/content/preview", json={"text": BAI_HOAN_CHINH}, headers=_headers(token_pair)
    )

    body = response.json()
    assert body["warnings"] == []
    assert body["truncate_at"] is None
    assert body["char_count"] == len(BAI_HOAN_CHINH)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a" * 1200, {"TRUNCATED"}),
        ("**Chữ đậm** trong bài ngắn", {"MARKDOWN_NOT_SUPPORTED"}),
        ("**Đậm** " + "chữ dài. " * 120, {"TRUNCATED", "MARKDOWN_NOT_SUPPORTED"}),
    ],
)
async def test_preview_bao_dung_van_de(
    client: AsyncClient, text: str, expected: set[str]
):
    token_pair = await _onboard(client, email=f"prev-{len(text)}-{len(expected)}@havi.vn")
    response = await client.post(
        "/content/preview", json={"text": text}, headers=_headers(token_pair)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert {w["code"] for w in body["warnings"]} == expected


async def test_preview_tra_ca_bai_khong_tu_cat_chuoi(client: AsyncClient):
    """Giao diện cần cả bài để vẽ nút "Xem thêm" mở ra được."""
    token_pair = await _onboard(client, email="prev3@havi.vn")
    text = "a" * 1500
    response = await client.post(
        "/content/preview", json={"text": text}, headers=_headers(token_pair)
    )

    body = response.json()
    assert body["text"] == text, "cắt ở backend thì phần sau không còn để mở ra"
    assert body["truncate_at"] == 800
    truncated = next(w for w in body["warnings"] if w["code"] == "TRUNCATED")
    assert truncated["at_char"] == 800
