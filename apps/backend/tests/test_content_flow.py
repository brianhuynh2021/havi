"""Test Content Engine end-to-end trên Postgres thật, LLM dùng FakeProvider.

Không gọi API LLM thật: tốn tiền, chậm, và cần key mà CI không có. FakeProvider
cho phép kiểm đủ thứ quan trọng — fallback provider, validation schema, chặn
banned claims, idempotency, trạng thái draft theo publish_mode.

Celery cũng không chạy thật: `RecordingJobQueue` thay cho Redis (xem
`application/services/job_queue.py` để biết vì sao `task_always_eager` không dùng
được ở đây), còn engine được gọi trực tiếp với session của test.
"""

import json
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.llm.fake import FakeProvider
from adapters.persistence.brand_profile_repository import BrandProfileRepository
from adapters.persistence.content_repository import ContentRepository
from adapters.persistence.event_log_repository import EventLogRepository
from adapters.persistence.media_repository import MediaRepository
from adapters.persistence.workspace_repository import WorkspaceRepository
from api.deps import get_job_queue
from application.services.content_engine import ContentEngine, GenerationFailed
from application.services.job_queue import RecordingJobQueue
from core.enums import ContentJobStatus, ContentStatus, PublishMode
from domain.models.audit import EventLog
from domain.models.content import ContentItem
from domain.policies.provider_router import ProviderRouter
from domain.ports.llm import LLMProvider, LLMTransientError

GOOD_OUTPUT = json.dumps(
    {
        "drafts": [
            {
                "channel": "facebook_page",
                "kind": "Bài ảnh",
                "text": "Gội đầu thảo dược cuối tuần này có ưu đãi nhỏ cho khách quen nha.",
                "media_note": "Chụp 1 tấm lúc đang gội",
            },
            {
                "channel": "zalo_oa",
                "kind": "Tin Zalo",
                "text": "Chị ơi, tuần này tiệm có ưu đãi gội đầu thảo dược, chị ghé nha.",
            },
            {
                "channel": "google_business",
                "kind": "Cập nhật Google",
                "text": "Spa An Nhiên cập nhật dịch vụ gội đầu thảo dược, nguyên liệu tự nhiên.",
            },
        ]
    },
    ensure_ascii=False,
)


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


def _engine(session: AsyncSession, *providers: FakeProvider) -> ContentEngine:
    return ContentEngine(
        content=ContentRepository(session),
        workspaces=WorkspaceRepository(session),
        profiles=BrandProfileRepository(session),
        media=MediaRepository(session),
        events=EventLogRepository(session),
        router=ProviderRouter({p.provider: p for p in providers}),
    )


@pytest.fixture
def job_queue(client: AsyncClient) -> RecordingJobQueue:
    """Override enqueue để không cần Redis; client fixture đã tạo app."""
    queue = RecordingJobQueue()
    client._transport.app.dependency_overrides[get_job_queue] = lambda: queue  # type: ignore[attr-defined]
    return queue


# --- Tạo job qua API --------------------------------------------------------


async def test_tao_job_tra_202_queued_va_day_vao_hang_doi(
    client: AsyncClient, job_queue: RecordingJobQueue
):
    token_pair = await _onboard(client, email="c1@havi.vn")
    response = await client.post(
        "/content/jobs",
        json={"raw_inputs": [{"kind": "text", "text": "Tuần này giảm giá gội đầu"}]},
        headers=_headers(token_pair),
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["status"] == "queued"
    assert body["content_item_ids"] == []
    assert len(job_queue.enqueued) == 1


async def test_tao_job_truyen_request_id_sang_hang_doi(
    client: AsyncClient, job_queue: RecordingJobQueue
):
    token_pair = await _onboard(client, email="c1-request@havi.vn")
    response = await client.post(
        "/content/jobs",
        json={"raw_inputs": [{"kind": "text", "text": "Tuần này giảm giá gội đầu"}]},
        headers=_headers(token_pair) | {"X-Request-ID": "req_content_123"},
    )

    assert response.status_code == 202, response.text
    assert response.headers["X-Request-ID"] == "req_content_123"
    assert job_queue.enqueued[0][2] == "req_content_123"


async def test_cung_idempotency_key_khong_tao_job_thu_hai(
    client: AsyncClient, job_queue: RecordingJobQueue
):
    """Bấm "Để Havi viết cho chị" hai lần không được tốn hai lần tiền LLM."""
    token_pair = await _onboard(client, email="c2@havi.vn")
    headers = _headers(token_pair) | {"Idempotency-Key": "abc-123"}
    payload = {"raw_inputs": [{"kind": "text", "text": "Ưu đãi cuối tuần"}]}

    first = await client.post("/content/jobs", json=payload, headers=headers)
    second = await client.post("/content/jobs", json=payload, headers=headers)

    assert first.status_code == second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert len(job_queue.enqueued) == 1, "lần thứ hai không được enqueue lại"


async def test_khong_co_idempotency_key_thi_moi_lan_la_job_moi(
    client: AsyncClient, job_queue: RecordingJobQueue
):
    token_pair = await _onboard(client, email="c3@havi.vn")
    payload = {"raw_inputs": [{"kind": "text", "text": "x"}]}
    first = await client.post("/content/jobs", json=payload, headers=_headers(token_pair))
    second = await client.post("/content/jobs", json=payload, headers=_headers(token_pair))
    assert first.json()["id"] != second.json()["id"]
    assert len(job_queue.enqueued) == 2


async def test_raw_inputs_rong_bi_tu_choi_422(client: AsyncClient, job_queue: RecordingJobQueue):
    token_pair = await _onboard(client, email="c4@havi.vn")
    response = await client.post(
        "/content/jobs", json={"raw_inputs": []}, headers=_headers(token_pair)
    )
    assert response.status_code == 422


async def test_chua_onboarding_thi_bi_chan_409(client: AsyncClient, job_queue: RecordingJobQueue):
    signup = await client.post(
        "/auth/sign-up", json={"name": "A", "email": "c5@havi.vn", "password": "matkhau123"}
    )
    response = await client.post(
        "/content/jobs",
        json={"raw_inputs": [{"kind": "text", "text": "x"}]},
        headers={"Authorization": f"Bearer {signup.json()['access_token']}"},
    )
    assert response.status_code == 409


async def test_khong_doc_duoc_job_cua_workspace_khac(
    client: AsyncClient, job_queue: RecordingJobQueue
):
    token_a = await _onboard(client, email="c6@havi.vn")
    token_b = await _onboard(client, email="c7@havi.vn")
    job = await client.post(
        "/content/jobs",
        json={"raw_inputs": [{"kind": "text", "text": "x"}]},
        headers=_headers(token_a),
    )
    response = await client.get(
        f"/content/jobs/{job.json()['id']}", headers=_headers(token_b)
    )
    assert response.status_code == 404


# --- Content Engine sinh draft ---------------------------------------------


async def test_sinh_draft_dung_so_luong_va_dung_pending_approval(
    client: AsyncClient, db_session: AsyncSession, job_queue: RecordingJobQueue
):
    token_pair = await _onboard(client, email="c8@havi.vn")
    job = (
        await client.post(
            "/content/jobs",
            json={"raw_inputs": [{"kind": "text", "text": "Gội đầu thảo dược"}]},
            headers=_headers(token_pair),
        )
    ).json()

    engine = _engine(db_session, FakeProvider(response_text=GOOD_OUTPUT))
    result = await engine.generate_drafts(
        workspace_id=UUID(job["workspace_id"]), job_id=UUID(job["id"])
    )

    assert len(result.items) == 3
    assert result.job.status == ContentJobStatus.DRAFTS_READY
    # review_first là mặc định — draft phải dừng ở pending_approval, không tự đăng.
    assert {i.status for i in result.items} == {ContentStatus.PENDING_APPROVAL}
    assert {i.channel.value for i in result.items} == {
        "facebook_page",
        "zalo_oa",
        "google_business",
    }


async def test_full_auto_thi_draft_vao_thang_scheduled(
    client: AsyncClient, db_session: AsyncSession, job_queue: RecordingJobQueue
):
    token_pair = await _onboard(client, email="c9@havi.vn")
    workspace_id = token_pair["active_workspace_id"]
    await client.patch(
        f"/workspaces/{workspace_id}",
        json={"publish_mode": "full_auto"},
        headers=_headers(token_pair),
    )
    job = (
        await client.post(
            "/content/jobs",
            json={"raw_inputs": [{"kind": "text", "text": "x"}]},
            headers=_headers(token_pair),
        )
    ).json()

    engine = _engine(db_session, FakeProvider(response_text=GOOD_OUTPUT))
    result = await engine.generate_drafts(
        workspace_id=UUID(workspace_id), job_id=UUID(job["id"])
    )

    assert {i.status for i in result.items} == {ContentStatus.SCHEDULED}
    # Sanity: workspace phải đúng là full_auto, không phải test pass vì lý do khác.
    workspace = await WorkspaceRepository(db_session).get_by_id(UUID(workspace_id))
    assert workspace is not None and workspace.publish_mode == PublishMode.FULL_AUTO


async def test_output_sai_schema_thi_fallback_provider_khac(
    client: AsyncClient, db_session: AsyncSession, job_queue: RecordingJobQueue
):
    token_pair = await _onboard(client, email="c10@havi.vn")
    job = (
        await client.post(
            "/content/jobs",
            json={"raw_inputs": [{"kind": "text", "text": "x"}]},
            headers=_headers(token_pair),
        )
    ).json()

    engine = _engine(
        db_session,
        FakeProvider(provider=LLMProvider.GEMINI, response_text='{"drafts": []}'),
        FakeProvider(provider=LLMProvider.ANTHROPIC, response_text=GOOD_OUTPUT),
    )
    result = await engine.generate_drafts(
        workspace_id=UUID(job["workspace_id"]), job_id=UUID(job["id"])
    )
    assert len(result.items) == 3


async def test_banned_claim_bi_chan_va_fallback_provider_khac(
    client: AsyncClient, db_session: AsyncSession, job_queue: RecordingJobQueue
):
    """Không tin model tự nhớ danh sách từ cấm trong prompt — phải chặn ở validation."""
    token_pair = await _onboard(client, email="c11@havi.vn")
    await client.put(
        "/brand-profile",
        json={"banned_claims": ["cam ket 100%"]},
        headers=_headers(token_pair),
    )
    job = (
        await client.post(
            "/content/jobs",
            json={"raw_inputs": [{"kind": "text", "text": "x"}]},
            headers=_headers(token_pair),
        )
    ).json()

    bad_output = GOOD_OUTPUT.replace(
        "Gội đầu thảo dược cuối tuần này có ưu đãi nhỏ cho khách quen nha.",
        "Cam Kết 100% trắng da sau một lần gội.",
    )
    engine = _engine(
        db_session,
        FakeProvider(provider=LLMProvider.GEMINI, response_text=bad_output),
        FakeProvider(provider=LLMProvider.ANTHROPIC, response_text=GOOD_OUTPUT),
    )
    result = await engine.generate_drafts(
        workspace_id=UUID(job["workspace_id"]), job_id=UUID(job["id"])
    )

    # Viết hoa/khác dấu vẫn phải bị bắt — "Cam Kết 100%" vs "cam ket 100%".
    assert all("Cam Kết 100%" not in i.text for i in result.items)
    assert len(result.items) == 3


async def test_moi_provider_that_bai_thi_job_failed_co_reason(
    client: AsyncClient, db_session: AsyncSession, job_queue: RecordingJobQueue
):
    token_pair = await _onboard(client, email="c12@havi.vn")
    job = (
        await client.post(
            "/content/jobs",
            json={"raw_inputs": [{"kind": "text", "text": "x"}]},
            headers=_headers(token_pair),
        )
    ).json()

    engine = _engine(
        db_session,
        FakeProvider(
            provider=LLMProvider.GEMINI,
            error=LLMTransientError(LLMProvider.GEMINI, "HTTP 429"),
        ),
    )
    with pytest.raises(GenerationFailed):
        await engine.generate_drafts(
            workspace_id=UUID(job["workspace_id"]), job_id=UUID(job["id"])
        )

    stored = await ContentRepository(db_session).get_job(
        workspace_id=UUID(job["workspace_id"]), job_id=UUID(job["id"])
    )
    assert stored is not None
    assert stored.status == ContentJobStatus.FAILED
    assert stored.failure_reason and "429" in stored.failure_reason


async def test_malformed_output_cua_moi_provider_khong_tao_draft_rac(
    client: AsyncClient, db_session: AsyncSession, job_queue: RecordingJobQueue
):
    """Contract test: output hỏng schema/JSON phải fail sạch, không lọt draft."""
    token_pair = await _onboard(client, email="c12-contract@havi.vn")
    job = (
        await client.post(
            "/content/jobs",
            json={"raw_inputs": [{"kind": "text", "text": "x"}]},
            headers=_headers(token_pair),
        )
    ).json()
    workspace_id, job_id = UUID(job["workspace_id"]), UUID(job["id"])

    engine = _engine(
        db_session,
        FakeProvider(provider=LLMProvider.GEMINI, response_text="không phải JSON"),
        FakeProvider(provider=LLMProvider.ANTHROPIC, response_text='{"drafts": []}'),
        FakeProvider(
            provider=LLMProvider.OPENAI,
            response_text=json.dumps(
                    {
                        "drafts": [
                            {"channel": "threads", "kind": "Threads", "text": "x"},
                            {"channel": "threads", "kind": "Threads", "text": "x"},
                            {"channel": "threads", "kind": "Threads", "text": "x"},
                        ]
                    }
                ),
        ),
    )

    with pytest.raises(GenerationFailed):
        await engine.generate_drafts(workspace_id=workspace_id, job_id=job_id)

    stored = await ContentRepository(db_session).get_job(
        workspace_id=workspace_id, job_id=job_id
    )
    assert stored is not None
    assert stored.status == ContentJobStatus.FAILED
    assert stored.failure_reason
    assert "invalid_output" in stored.failure_reason
    assert "output sai schema" in stored.failure_reason

    items = (
        await db_session.execute(select(ContentItem).where(ContentItem.job_id == job_id))
    ).scalars().all()
    assert items == []

    events = (
        await db_session.execute(select(EventLog).where(EventLog.job_id == job_id))
    ).scalars().all()
    assert len(events) == 1
    assert events[0].error and "invalid_output" in events[0].error


async def test_event_log_ghi_token_va_provider_vao_db(
    client: AsyncClient, db_session: AsyncSession, job_queue: RecordingJobQueue
):
    """Roadmap §9: phải đo được cost mỗi content job — không đo được thì không giữ margin."""
    token_pair = await _onboard(client, email="c13@havi.vn")
    job = (
        await client.post(
            "/content/jobs",
            json={"raw_inputs": [{"kind": "text", "text": "x"}]},
            headers=_headers(token_pair),
        )
    ).json()

    engine = _engine(
        db_session,
        FakeProvider(
            provider=LLMProvider.GEMINI,
            response_text="không phải JSON",
            tokens_in=11,
            tokens_out=22,
        ),
        FakeProvider(
            provider=LLMProvider.ANTHROPIC,
            response_text=GOOD_OUTPUT,
            tokens_in=33,
            tokens_out=44,
        ),
    )
    await engine.generate_drafts(
        workspace_id=UUID(job["workspace_id"]), job_id=UUID(job["id"])
    )

    rows = (
        await db_session.execute(select(EventLog).where(EventLog.job_id == UUID(job["id"])))
    ).scalars().all()
    assert len(rows) == 1
    entry = rows[0]
    assert entry.job_kind == "content.generate_drafts"
    # Cộng cả lần thử thất bại: 11+33 và 22+44 — provider lỗi vẫn tốn token thật.
    assert entry.tokens_in == 44
    assert entry.tokens_out == 66
    assert "anthropic" in entry.output_summary


async def test_prompt_chua_brand_voice_va_banned_claims(
    client: AsyncClient, db_session: AsyncSession, job_queue: RecordingJobQueue
):
    """Brand profile là input bắt buộc của prompt (TECHNICAL_SPEC §2) — verify thật."""
    token_pair = await _onboard(client, email="c14@havi.vn")
    await client.put(
        "/brand-profile",
        json={"tone": "vui vẻ, gọi khách là chị", "banned_claims": ["cam kết 100%"]},
        headers=_headers(token_pair),
    )
    job = (
        await client.post(
            "/content/jobs",
            json={"raw_inputs": [{"kind": "text", "text": "Ưu đãi gội đầu"}]},
            headers=_headers(token_pair),
        )
    ).json()

    provider = FakeProvider(response_text=GOOD_OUTPUT)
    engine = _engine(db_session, provider)
    await engine.generate_drafts(
        workspace_id=UUID(job["workspace_id"]), job_id=UUID(job["id"])
    )

    assert len(provider.calls) == 1
    system_prompt = provider.calls[0].system_prompt
    assert "vui vẻ, gọi khách là chị" in system_prompt
    assert "cam kết 100%" in system_prompt
    assert "Ưu đãi gội đầu" in provider.calls[0].user_prompt


async def test_job_failed_song_sot_khi_worker_rollback(
    client: AsyncClient, db_session: AsyncSession, job_queue: RecordingJobQueue
):
    """Trạng thái `failed` phải sống sót đúng cái exception đang đẩy nó đi.

    Worker chạy engine trong `session_scope`, mà scope đó rollback khi gặp
    exception — và engine ném `GenerationFailed` ngay sau khi đánh dấu failed.
    Nếu `mark_job_failed` chỉ flush chứ không commit, bản ghi bị rollback cuốn
    theo và job kẹt ở `queued` vĩnh viễn: frontend poll 3 phút rồi báo sai, chủ
    tiệm không biết là phải bấm tạo lại.

    Các test khác đọc lại bằng chính session đã ghi nên không thấy lỗi này —
    flush chưa commit vẫn hiện trong cùng session. Test này mô phỏng đúng ranh
    giới transaction của worker: bọc trong một transaction ngoài, rollback nó,
    rồi đọc lại bằng connection khác.
    """
    token_pair = await _onboard(client, email="c15@havi.vn")
    job = (
        await client.post(
            "/content/jobs",
            json={"raw_inputs": [{"kind": "text", "text": "x"}]},
            headers=_headers(token_pair),
        )
    ).json()
    workspace_id, job_id = UUID(job["workspace_id"]), UUID(job["id"])

    engine = _engine(
        db_session,
        FakeProvider(
            provider=LLMProvider.GEMINI,
            error=LLMTransientError(LLMProvider.GEMINI, "HTTP 429"),
        ),
    )
    with pytest.raises(GenerationFailed):
        await engine.generate_drafts(workspace_id=workspace_id, job_id=job_id)

    # Đúng việc `session_scope` làm khi thấy exception.
    await db_session.rollback()

    stored = await ContentRepository(db_session).get_job(
        workspace_id=workspace_id, job_id=job_id
    )
    assert stored is not None
    assert stored.status == ContentJobStatus.FAILED, (
        "job phải còn `failed` sau rollback — nếu là `queued` thì mark_job_failed "
        "chỉ flush chứ chưa commit"
    )
    assert stored.failure_reason and "429" in stored.failure_reason
