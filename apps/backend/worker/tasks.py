"""Các job của worker — khung rỗng, điền khi nối LLM và adapter thật.

Phễu listening (tiết kiệm token): 100% bài → keyword + rule (0 token) → ~5% → model rẻ
chấm điểm ý định → ~1% → LLM soạn trả lời → dừng ở pending_approval.
"""

from worker.celery_app import celery_app


@celery_app.task(name="havi.content.generate_drafts", bind=True, max_retries=3)
def generate_drafts(self, job_id: str) -> None:  # noqa: ANN001
    """Ingest media → đọc brand profile (cache) → 1 lần gọi LLM sinh mọi kênh.

    Trạng thái draft khi sinh xong lấy từ `core.content_state.initial_status(publish_mode)`.
    """
    del self, job_id
    raise NotImplementedError


@celery_app.task(name="havi.listening.classify", bind=True)
def classify_listening_item(self, inbox_item_id: str) -> None:  # noqa: ANN001
    """Rule + model nhỏ chấm điểm ý định trước khi động tới LLM xịn."""
    del self, inbox_item_id
    raise NotImplementedError


@celery_app.task(name="havi.reply.draft", bind=True)
def draft_reply(self, inbox_item_id: str) -> None:  # noqa: ANN001
    """Soạn `ai_suggested_reply`. Luôn dừng ở pending_approval — không tự gửi."""
    del self, inbox_item_id
    raise NotImplementedError


@celery_app.task(name="havi.publish.content_item", bind=True, max_retries=3)
def publish_content_item(self, content_item_id: str, idempotency_key: str) -> None:  # noqa: ANN001
    """Đăng qua adapter của kênh.

    `idempotency_key` có unique constraint để bài không bị đăng đúp khi user bấm 2 lần
    hoặc 2 worker cùng nhận job. Lỗi phân loại theo `PublishFailureKind`:
    temporary → retry backoff; auth_permission → báo chủ nối lại kênh; validation → không retry.
    """
    del self, content_item_id, idempotency_key
    raise NotImplementedError
