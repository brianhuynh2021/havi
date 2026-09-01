"""Ghi event_log vào Postgres.

`core/events.py` giữ `EventLogEntry` làm contract và chỉ log ra stdout — nó không
được import SQLAlchemy (domain không phụ thuộc framework, xem
SYSTEM_ARCHITECTURE.md §0). Repository này là chỗ duy nhất thực sự insert.
"""

from datetime import datetime
from math import ceil
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.events import EventLogEntry, record_event
from core.request_context import get_request_id
from domain.models.audit import EventLog
from domain.policies import pricing, quota

SLOW_CONTENT_GENERATION_MS = 20_000


class EventLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, entry: EventLogEntry) -> EventLog:
        effective_entry = entry.model_copy(
            update={"request_id": entry.request_id or get_request_id()}
        )
        # Log ra stdout luôn: nếu transaction rollback vì lỗi sau đó, ít nhất vẫn
        # còn dấu vết trong log để debug.
        record_event(effective_entry)
        row = EventLog(
            workspace_id=effective_entry.workspace_id,
            job_id=effective_entry.job_id,
            content_item_id=effective_entry.content_item_id,
            request_id=effective_entry.request_id,
            job_kind=effective_entry.job_kind,
            input_summary=effective_entry.input_summary,
            output_summary=effective_entry.output_summary,
            tokens_in=effective_entry.tokens_in,
            tokens_out=effective_entry.tokens_out,
            duration_ms=effective_entry.duration_ms,
            provider=effective_entry.provider,
            model=effective_entry.model,
            error=effective_entry.error,
            # Lấy `created_at` từ entry, không để default của cột tự điền: bảng
            # này giờ append-only (trigger chặn UPDATE), nên sửa lại thời điểm
            # *sau* khi insert là không thể nữa. Thời điểm phải đúng ngay từ đầu.
            #
            # `EventLogEntry.created_at` vốn đã có default là `now()`, nên đường
            # chạy production không đổi gì; điều này chỉ mở đường cho caller biết
            # rõ thời điểm thật của sự kiện (backfill, test) khai báo tường minh.
            created_at=effective_entry.created_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def verify_chain(self, *, workspace_id: UUID) -> dict:
        """Kiểm hash chain của một workspace, trả chỗ đứt đầu tiên nếu có.

        Trigger Postgres đã chặn UPDATE/DELETE, nên hàm này không phải tuyến
        phòng thủ hàng ngày — nó là *bằng chứng*. Ai có SUPERUSER thì tắt được
        trigger; điều họ không làm được là sửa một dòng mà mọi `row_hash` phía
        sau vẫn khớp. Đây là nơi trả lời câu hỏi đó của auditor.

        Tính lại hash bằng SQL (`digest`) chứ không bằng Python: công thức phải
        **giống hệt** trigger, và giữ một bản sao công thức trong Python là mời
        gọi hai bản trôi lệch nhau — lúc đó verify sẽ báo đứt chuỗi ở dữ liệu
        hoàn toàn nguyên vẹn, thứ báo động giả tệ nhất trong cả hệ thống.

        Bỏ qua dòng có `row_hash IS NULL` (ghi trước migration f2a3b4c5d6e7):
        chúng không thuộc chuỗi, và coi chúng là đứt sẽ khiến mọi workspace cũ
        đều báo lỗi vĩnh viễn.
        """
        result = await self._session.execute(
            text(
                """
                WITH chain AS (
                    SELECT
                        id,
                        created_at,
                        row_hash,
                        prev_hash,
                        LAG(row_hash) OVER (ORDER BY created_at, id) AS expected_prev,
                        encode(
                            digest(
                                concat_ws(
                                    chr(31),
                                    COALESCE(
                                        LAG(row_hash) OVER (ORDER BY created_at, id), ''
                                    ),
                                    id::text,
                                    COALESCE(workspace_id::text, ''),
                                    COALESCE(job_id::text, ''),
                                    COALESCE(content_item_id::text, ''),
                                    COALESCE(request_id, ''),
                                    job_kind,
                                    input_summary,
                                    output_summary,
                                    tokens_in::text,
                                    tokens_out::text,
                                    duration_ms::text,
                                    COALESCE(provider, ''),
                                    COALESCE(model, ''),
                                    COALESCE(error, ''),
                                    created_at::text
                                ),
                                'sha256'
                            ),
                            'hex'
                        ) AS recomputed
                    FROM event_log
                    WHERE workspace_id = :workspace_id AND row_hash IS NOT NULL
                )
                SELECT id, created_at, row_hash, recomputed,
                       prev_hash IS DISTINCT FROM expected_prev AS link_broken
                FROM chain
                WHERE row_hash IS DISTINCT FROM recomputed
                   OR prev_hash IS DISTINCT FROM expected_prev
                ORDER BY created_at, id
                LIMIT 1
                """
            ),
            {"workspace_id": str(workspace_id)},
        )
        broken = result.first()
        counted = await self._session.execute(
            select(func.count()).where(
                EventLog.workspace_id == workspace_id, EventLog.row_hash.is_not(None)
            )
        )
        total = counted.scalar_one()
        if broken is None:
            return {"ok": True, "rows_checked": total, "broken_at": None}
        return {
            "ok": False,
            "rows_checked": total,
            "broken_at": {
                "id": str(broken.id),
                "created_at": broken.created_at,
                "link_broken": bool(broken.link_broken),
            },
        }

    async def tokens_used_since(self, *, workspace_id: UUID, since: datetime) -> int:
        """Token đã dùng của workspace từ `since`, **tính trọng số theo chi phí**.

        Bản trước cộng thẳng `tokens_in + tokens_out` với lý do "quota tính theo
        token, không theo tiền". Lý do đó nghe đúng nhưng để lại một lỗ: token
        output đắt gấp 4–5 lần input ở mọi provider, nên hai workspace cùng đụng
        trần 500k token có thể chênh nhau **vài lần** chi phí thật. Quota lúc đó
        chặn *khối lượng*, không chặn *chi phí* — mà chặn chi phí mới là việc nó
        tồn tại để làm.

        Giờ output được nhân `quota.OUTPUT_WEIGHT`. Đơn vị vẫn là "token" và vẫn
        không phụ thuộc bảng giá của provider nào (một tỷ lệ, không phải một mức
        giá), nhưng nó phản ánh chi phí thật. Trần trong `MONTHLY_TOKEN_QUOTA` đã
        được điều chỉnh theo cùng lúc nên khối lượng dùng được không đổi.

        Đếm cả dòng có `error`: provider trả lỗi vẫn tốn token đã gửi. Bỏ chúng ra
        là mở đường cho một workspace liên tục gửi prompt lỗi mà không tính vào
        quota.
        """
        result = await self._session.execute(
            select(
                func.coalesce(
                    func.sum(
                        EventLog.tokens_in + EventLog.tokens_out * quota.OUTPUT_WEIGHT
                    ),
                    0,
                )
            ).where(EventLog.workspace_id == workspace_id, EventLog.created_at >= since)
        )
        return int(result.scalar() or 0)

    async def list_for_workspace(
        self,
        *,
        workspace_id: UUID,
        job_id: UUID | None = None,
        content_item_id: UUID | None = None,
        job_kind: str | None = None,
        provider: str | None = None,
        request_id: str | None = None,
        error_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[EventLog], int]:
        """Tra event log đã scope theo workspace.

        Đây là query hỗ trợ vận hành, không phải analytics public. Chỉ lọc trên
        cột có cấu trúc (`job_id`, `content_item_id`, `job_kind`, `provider`, `error`), tránh parse
        `input_summary`/`output_summary` tự do rồi tạo cảm giác tìm kiếm chính
        xác trong khi thực ra phụ thuộc format câu chữ.
        """
        filters = [EventLog.workspace_id == workspace_id]
        if job_id is not None:
            filters.append(EventLog.job_id == job_id)
        if content_item_id is not None:
            filters.append(EventLog.content_item_id == content_item_id)
        if job_kind is not None:
            filters.append(EventLog.job_kind == job_kind)
        if provider is not None:
            filters.append(EventLog.provider == provider)
        if request_id is not None:
            filters.append(EventLog.request_id == request_id)
        if error_only:
            filters.append(EventLog.error.is_not(None))

        total = await self._session.execute(select(func.count()).where(*filters))
        rows = await self._session.execute(
            select(EventLog)
            .where(*filters)
            .order_by(EventLog.created_at.desc(), EventLog.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(rows.scalars().all()), total.scalar_one()

    async def avg_weighted_tokens_per_content_job(
        self, *, workspace_id: UUID, since: datetime
    ) -> int | None:
        """Token (đã trọng số) trung bình cho một content job của workspace này.

        Trả `None` khi chưa đủ mẫu — xem `quota.MIN_SAMPLES_FOR_MEASURED_RATE`.
        `None` nghĩa là "chưa đo được", và chỗ dùng phải nói ra điều đó chứ không
        được lặng lẽ thay bằng một hằng số: một con số ước lượng trình bày như số
        đo là cùng loại sai với việc bịa chỉ số.

        Đếm theo `job_id` chứ không theo dòng log: một job có thể thử nhiều
        provider và ghi nhiều dòng, nhưng với người dùng nó vẫn là một lần "Havi
        viết bài".
        """
        result = await self._session.execute(
            select(
                func.count(func.distinct(EventLog.job_id)),
                func.coalesce(
                    func.sum(EventLog.tokens_in + EventLog.tokens_out * quota.OUTPUT_WEIGHT),
                    0,
                ),
            ).where(
                EventLog.workspace_id == workspace_id,
                EventLog.created_at >= since,
                EventLog.job_id.is_not(None),
                EventLog.job_kind.startswith("content."),
            )
        )
        jobs, weighted = result.one()
        if not jobs or jobs < quota.MIN_SAMPLES_FOR_MEASURED_RATE:
            return None
        return int(weighted // jobs) or None

    async def operations_metrics(
        self, *, workspace_id: UUID, start: datetime, end: datetime
    ) -> dict:
        """Aggregate event_log cho dashboard vận hành nội bộ.

        Fetch các dòng trong cửa sổ rồi tính p95 ở Python để không khóa mình vào
        hàm percentile riêng của một database. Pilot chưa có volume lớn; khi có
        metrics backend thật thì adapter này sẽ được thay.

        Trả về `content_cost_vnd` thô chứ **không** tự chia ra "chi phí mỗi bản
        nháp được duyệt": số bản nháp thật sự được duyệt nằm ở bảng
        `content_items`, không nằm trong event_log. Bản trước đếm số *sự kiện*
        sinh nội dung rồi gọi đó là số bản nháp được duyệt — mà một job sinh ra
        nhiều nháp và người dùng chỉ dùng vài cái, nên con số đó thấp hơn chi phí
        thật đúng bằng tỷ lệ nháp bị vứt. Router ghép hai nguồn.
        """
        result = await self._session.execute(
            select(EventLog).where(
                EventLog.workspace_id == workspace_id,
                EventLog.created_at >= start,
                EventLog.created_at < end,
            )
        )
        rows = list(result.scalars().all())
        durations = sorted(row.duration_ms for row in rows)
        p95_duration_ms = 0
        if durations:
            p95_duration_ms = durations[ceil(len(durations) * 0.95) - 1]

        content_generation_durations = sorted(
            row.duration_ms
            for row in rows
            if row.job_kind.startswith("content.generate") and row.duration_ms > 0
        )
        content_generation_p95_ms = 0
        if content_generation_durations:
            content_generation_p95_ms = content_generation_durations[
                ceil(len(content_generation_durations) * 0.95) - 1
            ]

        providers: dict[str, dict[str, int | float]] = {}
        total_cost_vnd = 0.0
        content_cost_vnd = 0.0

        for row in rows:
            provider = row.provider or "unknown"
            bucket = providers.setdefault(
                provider, {"event_count": 0, "error_count": 0, "tokens_total": 0, "cost_vnd": 0.0}
            )
            bucket["event_count"] += 1
            bucket["tokens_total"] += row.tokens_in + row.tokens_out
            if row.error is not None:
                bucket["error_count"] += 1

            row_cost = pricing.cost_vnd(
                tokens_in=row.tokens_in,
                tokens_out=row.tokens_out,
                model=row.model,
                provider=row.provider,
            )
            bucket["cost_vnd"] += row_cost
            total_cost_vnd += row_cost
            if row.job_kind.startswith("content."):
                content_cost_vnd += row_cost

        event_count = len(rows)
        error_count = sum(1 for row in rows if row.error is not None)
        tokens_in = sum(row.tokens_in for row in rows)
        tokens_out = sum(row.tokens_out for row in rows)
        tokens_total = tokens_in + tokens_out

        job_count = len({row.job_id for row in rows if row.job_id is not None})

        return {
            "event_count": event_count,
            "error_count": error_count,
            "error_rate": round(error_count / event_count, 4) if event_count else 0,
            "avg_duration_ms": round(sum(durations) / event_count) if event_count else 0,
            "p95_duration_ms": p95_duration_ms,
            "content_generation_count": len(content_generation_durations),
            "slow_content_generation_count": sum(
                duration > SLOW_CONTENT_GENERATION_MS
                for duration in content_generation_durations
            ),
            "content_generation_p95_ms": content_generation_p95_ms,
            "slow_content_generation_threshold_ms": SLOW_CONTENT_GENERATION_MS,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tokens_total": tokens_total,
            "job_count": job_count,
            "avg_tokens_per_job": round(tokens_total / job_count) if job_count else 0,
            "est_cost_per_job_vnd": round(total_cost_vnd / job_count) if job_count else 0,
            "content_cost_vnd": round(content_cost_vnd),
            "providers": [
                {
                    "provider": provider,
                    "event_count": metrics["event_count"],
                    "error_count": metrics["error_count"],
                    "tokens_total": metrics["tokens_total"],
                    "cost_vnd": round(metrics["cost_vnd"]),
                }
                for provider, metrics in sorted(providers.items())
            ],
        }
