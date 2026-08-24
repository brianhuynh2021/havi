"""Beat schedule ↔ task registry, và Celery task gọi đúng service.

Lý do file này tồn tại: một task name viết sai trong `beat_schedule` không làm
gì cả ở lúc import — beat vẫn khởi động, vẫn log "sending due task", và worker
âm thầm bỏ message vì không có task nào tên đó. Nghĩa là lịch đăng chết hoàn
toàn mà không có một dòng lỗi nào. Đúng kiểu sai lặng lẽ mà `HAVI_USE_FAKE_PUBLISHER`
được chặn ở staging để tránh (ROADMAP Tuần 7).

Không test phần chạy thật của task ở đây: `dispatch_due_posts` gọi `asyncio.run`
với `session_scope()` riêng, nên nó không thấy transaction mà fixture đang
rollback. Hành vi publish end-to-end đã test thật trên Postgres ở
`test_publish_flow.py`; ở đây chỉ kiểm phần dây nối.
"""

import scheduler.beat  # noqa: F401 — import mới nạp beat_schedule vào conf
import scheduler.tasks
import worker.tasks
from worker.celery_app import celery_app


class TestBeatSchedule:
    def test_moi_task_trong_lich_deu_ton_tai_trong_registry(self):
        """Task name gõ sai = lịch đăng chết lặng, không có lỗi nào để lần ra."""
        scheduled = {entry["task"] for entry in celery_app.conf.beat_schedule.values()}
        missing = scheduled - set(celery_app.tasks)
        assert not missing, f"beat_schedule trỏ tới task không tồn tại: {missing}"

    def test_dispatch_va_run_due_deu_co_trong_lich(self):
        """Hai chặng của luồng đăng bài. Thiếu `dispatch` thì không có job nào
        được tạo; thiếu `run_due` thì job nằm mãi ở `pending` và không bài nào lên
        Trang — cả hai đều là "im lặng không đăng gì"."""
        scheduled = {entry["task"] for entry in celery_app.conf.beat_schedule.values()}
        assert "havi.scheduler.dispatch_due_posts" in scheduled
        assert "havi.publish.run_due" in scheduled

    def test_task_chua_lam_khong_nam_trong_lich(self):
        """`refresh_platform_tokens`, `poll_engagement` chạy an toàn không crash worker."""
        chua_lam = {
            "havi.scheduler.refresh_platform_tokens",
            "havi.scheduler.poll_engagement",
        }
        for name in chua_lam:
            assert name in celery_app.tasks
            task = celery_app.tasks[name]
            # Chạy hàm task an toàn
            task.run()


class TestDispatchDuePosts:
    def test_tao_job_roi_goi_worker_chay(self, monkeypatch):
        """Beat không được đứng chờ Graph API: `dispatch_due_posts` chỉ tạo job
        rồi `delay()` sang worker."""
        from application.services.publish_service import DispatchResult

        calls: list[str] = []

        class _FakeService:
            async def dispatch_due(self):
                calls.append("dispatch_due")
                return DispatchResult(enqueued=2, skipped=1)

            async def run_due(self, **kwargs):  # pragma: no cover — không được gọi
                calls.append("run_due")
                return []

        monkeypatch.setattr(
            "worker.publish_service_factory.publish_service_scope",
            _scope(_FakeService()),
        )
        monkeypatch.setattr(worker.tasks.publish_run_due, "delay", lambda: calls.append("delay"))

        scheduler.tasks.dispatch_due_posts.run()

        assert calls == ["dispatch_due", "delay"], (
            "beat phải tạo job rồi giao việc đăng cho worker, không tự gọi run_due"
        )

    def test_khong_tao_job_moi_van_goi_worker(self, monkeypatch):
        """Job đang chờ backoff từ lượt trước cũng cần được chạy — bỏ `delay()`
        khi `enqueued == 0` là bài lỗi tạm thời không bao giờ được thử lại."""
        from application.services.publish_service import DispatchResult

        calls: list[str] = []

        class _FakeService:
            async def dispatch_due(self):
                return DispatchResult(enqueued=0, skipped=0)

        monkeypatch.setattr(
            "worker.publish_service_factory.publish_service_scope",
            _scope(_FakeService()),
        )
        monkeypatch.setattr(worker.tasks.publish_run_due, "delay", lambda: calls.append("delay"))

        scheduler.tasks.dispatch_due_posts.run()

        assert calls == ["delay"]


class TestPublishRunDue:
    def test_goi_run_due_va_tra_so_job(self, monkeypatch):
        seen: dict[str, int] = {}

        class _FakeService:
            async def run_due(self, *, limit):
                seen["limit"] = limit
                return [object(), object()]

        monkeypatch.setattr(
            "worker.publish_service_factory.publish_service_scope",
            _scope(_FakeService()),
        )

        assert worker.tasks.publish_run_due.run(limit=5) == 2
        assert seen["limit"] == 5

    def test_khong_nhan_content_item_id(self):
        """Job phải được nhận bằng `claim_due` (row lock ở Postgres), không bằng
        tham số của message: Celery *được phép* giao lại một message, và nếu id
        nằm trong message thì hai worker cùng đăng một bài."""
        import inspect

        params = inspect.signature(worker.tasks.publish_run_due.run).parameters
        assert "content_item_id" not in params
        assert "idempotency_key" not in params

    def test_tat_retry_cua_celery(self):
        """Retry do `mark_failed` xếp lịch theo `PublishFailureKind` (backoff
        60/300/900s, hoặc dead-letter ngay). Để Celery retry lên trên là hai cơ
        chế lệch nhau trên cùng một job: Celery đếm lần thử của *message*, còn
        `attempt_count` đếm lần thử của *job* — số không khớp thì dead-letter
        không bao giờ tới đúng lúc.

        Phải khai `max_retries=0` tường minh vì mặc định của Celery là 3."""
        assert worker.tasks.publish_run_due.max_retries == 0


def _scope(service):
    """Thay `publish_service_scope` bằng context manager trả service giả."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _fake():
        yield service

    return _fake
