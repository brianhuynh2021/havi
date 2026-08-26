import re

with open("apps/backend/adapters/persistence/event_log_repository.py", "r") as f:
    content = f.read()

# Replace the operations_metrics function
new_func = """    async def operations_metrics(
        self, *, workspace_id: UUID, start: datetime, end: datetime
    ) -> dict:
        \"\"\"Aggregate event_log cho dashboard vận hành nội bộ.

        Fetch các dòng trong cửa sổ rồi tính p95 ở Python để không khóa mình vào
        hàm percentile riêng của một database. Pilot chưa có volume lớn; khi có
        metrics backend thật thì adapter này sẽ được thay.
        \"\"\"
        # Bảng giá LLM hiện tại (VND cho mỗi 1 token)
        # Giả sử tỷ giá 25000 VND / USD
        # gpt-4o-mini: Input $0.150 / 1M = 0.00375 VND/token; Output $0.600 / 1M = 0.015 VND/token
        # openai mặc định dùng gpt-4o-mini, anthropic giả định dùng claude-3-5-sonnet, gemini-1.5-flash
        # Nếu chưa rõ provider cụ thể, lấy giá mặc định an toàn.
        PRICING_VND_PER_TOKEN = {
            "openai": {"in": 0.00375, "out": 0.015},
            "anthropic": {"in": 0.075, "out": 0.375}, # $3 / $15 per 1M -> x25000 / 1000000
            "gemini": {"in": 0.001875, "out": 0.0075}, # $0.075 / $0.3 per 1M
            "default": {"in": 0.01, "out": 0.05},
        }

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

        providers: dict[str, dict[str, int | float]] = {}
        total_cost_vnd = 0.0

        for row in rows:
            provider = row.provider or "unknown"
            bucket = providers.setdefault(
                provider, {"event_count": 0, "error_count": 0, "tokens_total": 0, "cost_vnd": 0}
            )
            bucket["event_count"] += 1
            bucket["tokens_total"] += row.tokens_in + row.tokens_out
            if row.error is not None:
                bucket["error_count"] += 1
            
            # Tính chi phí cho từng dòng
            rates = PRICING_VND_PER_TOKEN.get(provider, PRICING_VND_PER_TOKEN["default"])
            job_cost = (row.tokens_in * rates["in"]) + (row.tokens_out * rates["out"])
            bucket["cost_vnd"] += job_cost
            total_cost_vnd += job_cost

        event_count = len(rows)
        error_count = sum(1 for row in rows if row.error is not None)
        tokens_in = sum(row.tokens_in for row in rows)
        tokens_out = sum(row.tokens_out for row in rows)
        tokens_total = tokens_in + tokens_out

        job_ids = set(row.job_id for row in rows if row.job_id is not None)
        job_count = len(job_ids)
        avg_tokens_per_job = round(tokens_total / job_count) if job_count else 0
        est_cost_per_job_vnd = round(total_cost_vnd / job_count) if job_count else 0

        draft_events = sum(1 for row in rows if "content" in row.job_kind)
        approved_draft_count = draft_events
        # Tách riêng chi phí cho content jobs
        content_cost_vnd = 0.0
        for row in rows:
            if "content" in row.job_kind:
                provider = row.provider or "unknown"
                rates = PRICING_VND_PER_TOKEN.get(provider, PRICING_VND_PER_TOKEN["default"])
                content_cost_vnd += (row.tokens_in * rates["in"]) + (row.tokens_out * rates["out"])
                
        est_cost_per_approved_draft_vnd = (
            round(content_cost_vnd / approved_draft_count) if approved_draft_count else 0
        )

        return {
            "event_count": event_count,
            "error_count": error_count,
            "error_rate": round(error_count / event_count, 4) if event_count else 0,
            "avg_duration_ms": round(sum(durations) / event_count) if event_count else 0,
            "p95_duration_ms": p95_duration_ms,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tokens_total": tokens_total,
            "job_count": job_count,
            "avg_tokens_per_job": avg_tokens_per_job,
            "est_cost_per_job_vnd": est_cost_per_job_vnd,
            "approved_draft_count": approved_draft_count,
            "est_cost_per_approved_draft_vnd": est_cost_per_approved_draft_vnd,
            "providers": [
                {"provider": provider, "event_count": metrics["event_count"], "error_count": metrics["error_count"], "tokens_total": metrics["tokens_total"], "cost_vnd": round(metrics["cost_vnd"])} 
                for provider, metrics in sorted(providers.items())
            ],
        }"""

pattern = re.compile(r'    async def operations_metrics\(.*?return \{\n.*?\n        \}', re.DOTALL)
new_content = pattern.sub(new_func, content)

with open("apps/backend/adapters/persistence/event_log_repository.py", "w") as f:
    f.write(new_content)
print("Updated event_log_repository.py")
