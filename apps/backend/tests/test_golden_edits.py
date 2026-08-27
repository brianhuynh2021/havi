"""Bản gốc do AI viết phải sống sót qua lần chủ tiệm sửa.

Vì sao có file này
------------------
`update_item` **ghi đè** `content_items.text` khi có người sửa. Trước đây bản v1
— chính chữ AI vừa sinh — không được lưu ở đâu cả, nên sau lần sửa đầu tiên nó
biến mất vĩnh viễn.

Hệ quả không nhìn thấy ngay: cặp (AI viết gì → người sửa thành gì) là dữ liệu
duy nhất nói lên giọng thật của một tiệm, và nó chỉ tồn tại nếu được ghi *trước*
khi bị ghi đè. Bật tính năng học giọng văn sau ba tháng pilot mà không có nó thì
ba tháng dữ liệu đã mất, và không có cách nào dựng lại.

Nên các test dưới đây khẳng định hai điều: v1 được ghi lúc sinh, và nó vẫn còn
nguyên văn sau khi người sửa.
"""

from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.persistence.content_repository import ContentRepository
from core.enums import Channel, ContentStatus


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


def _workspace_id(token_pair: dict) -> UUID:
    return UUID(token_pair["active_workspace_id"])


async def _job(repo: ContentRepository, workspace_id: UUID):
    """`create_job` trả `(job, created)` — chỉ cần job."""
    job, _ = await repo.create_job(
        workspace_id=workspace_id,
        raw_inputs=[{"kind": "text", "text": "gội đầu thảo dược"}],
        idempotency_key=f"golden-{workspace_id}",
    )
    return job


async def test_ban_v1_duoc_ghi_ngay_khi_ai_sinh_bai(
    client: AsyncClient, db_session: AsyncSession
):
    """Sinh bài xong là đã có v1 trong lịch sử, `edited_by` trống vì đó là máy."""
    token_pair = await _onboard(client, email="golden1@havi.vn")
    workspace_id = _workspace_id(token_pair)
    repo = ContentRepository(db_session)
    job = await _job(repo, workspace_id)

    item = await repo.create_item(
        workspace_id=workspace_id,
        job_id=job.id,
        channel=Channel.FACEBOOK_PAGE,
        kind="post",
        text="Chào quý khách, tiệm có ưu đãi gội đầu.",
        media_note=None,
        status=ContentStatus.PENDING_APPROVAL,
    )

    versions = await repo.list_versions(item.id)
    assert len(versions) == 1, "sinh bài phải để lại đúng một bản gốc"
    assert versions[0].version_no == 1
    assert versions[0].text == "Chào quý khách, tiệm có ưu đãi gội đầu."
    assert versions[0].edited_by is None, "bản của máy không mang id người nào"


async def test_ban_goc_con_nguyen_van_sau_khi_chu_tiem_sua(
    client: AsyncClient, db_session: AsyncSession
):
    """Đây là hồi quy của chính cái bug: `item.text` bị ghi đè, v1 thì không."""
    token_pair = await _onboard(client, email="golden2@havi.vn")
    workspace_id = _workspace_id(token_pair)
    repo = ContentRepository(db_session)
    job = await _job(repo, workspace_id)

    item = await repo.create_item(
        workspace_id=workspace_id,
        job_id=job.id,
        channel=Channel.FACEBOOK_PAGE,
        kind="post",
        text="Chào quý khách, tiệm có ưu đãi gội đầu.",
        media_note=None,
        status=ContentStatus.PENDING_APPROVAL,
    )
    editor = UUID(token_pair["user_id"]) if "user_id" in token_pair else None

    await repo.update_item(
        item,
        text="Chào chị em, tiệm có ưu đãi gội đầu nha!",
        media_note=None,
        scheduled_at=None,
        edited_by=editor,
    )

    assert item.text == "Chào chị em, tiệm có ưu đãi gội đầu nha!"
    assert item.version_no == 2

    versions = await repo.list_versions(item.id)
    assert [v.version_no for v in versions] == [1, 2]
    assert versions[0].text == "Chào quý khách, tiệm có ưu đãi gội đầu.", (
        "bản AI viết phải còn nguyên — đây là thứ duy nhất nói lên chỗ chủ tiệm sửa"
    )
    assert versions[0].edited_by is None
    assert versions[1].text == "Chào chị em, tiệm có ưu đãi gội đầu nha!"


async def test_cap_ai_nguoi_chi_lay_bai_da_bi_sua(
    client: AsyncClient, db_session: AsyncSession
):
    """Bài duyệt nguyên văn không nằm trong tập học: nó không chứa vết sửa nào."""
    token_pair = await _onboard(client, email="golden3@havi.vn")
    workspace_id = _workspace_id(token_pair)
    repo = ContentRepository(db_session)
    job = await _job(repo, workspace_id)

    untouched = await repo.create_item(
        workspace_id=workspace_id,
        job_id=job.id,
        channel=Channel.FACEBOOK_PAGE,
        kind="post",
        text="Bài này chủ tiệm duyệt luôn, không sửa gì.",
        media_note=None,
        status=ContentStatus.PENDING_APPROVAL,
    )
    edited = await repo.create_item(
        workspace_id=workspace_id,
        job_id=job.id,
        channel=Channel.FACEBOOK_PAGE,
        kind="post",
        text="Chào quý khách.",
        media_note=None,
        status=ContentStatus.PENDING_APPROVAL,
    )
    await repo.update_item(
        edited,
        text="Chào chị em nha.",
        media_note=None,
        scheduled_at=None,
        edited_by=None,
    )

    pairs = await repo.list_ai_human_pairs(workspace_id=workspace_id)

    assert ("Chào quý khách.", "Chào chị em nha.") in pairs
    assert all(untouched.text not in pair for pair in pairs), (
        "bài không ai sửa thì không có tín hiệu gì để học"
    )


async def test_cap_ai_nguoi_lay_ban_sua_cuoi_cung(
    client: AsyncClient, db_session: AsyncSession
):
    """Sửa hai lần thì cặp phải là (v1, v3) — bản đang dùng thật, không phải v2."""
    token_pair = await _onboard(client, email="golden4@havi.vn")
    workspace_id = _workspace_id(token_pair)
    repo = ContentRepository(db_session)
    job = await _job(repo, workspace_id)

    item = await repo.create_item(
        workspace_id=workspace_id,
        job_id=job.id,
        channel=Channel.FACEBOOK_PAGE,
        kind="post",
        text="Bản AI.",
        media_note=None,
        status=ContentStatus.PENDING_APPROVAL,
    )
    for text in ("Sửa lần một.", "Sửa lần hai."):
        await repo.update_item(
            item, text=text, media_note=None, scheduled_at=None, edited_by=None
        )

    assert item.version_no == 3
    pairs = await repo.list_ai_human_pairs(workspace_id=workspace_id)
    assert ("Bản AI.", "Sửa lần hai.") in pairs
    assert ("Bản AI.", "Sửa lần một.") not in pairs
