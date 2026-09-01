"""Prometheus metrics — nguồn số duy nhất cho SLA P95/P99.

Trước file này Havi không đo được latency ở đâu cả, nên câu "SLA P95" không có
cơ sở nào để phát biểu. `event_log` có `duration_ms` nhưng nó chỉ ghi *job LLM*,
không ghi HTTP request, và query percentile trên bảng đang lớn dần thì không
dùng được cho alert.

Vì sao Histogram chứ không Summary hay Gauge:

- **Gauge** chỉ giữ giá trị cuối — mất phân bố, không ra được percentile.
- **Summary** tính quantile trong từng process. Havi chạy nhiều uvicorn worker,
  và quantile **không cộng được** giữa các process: trung bình của các P95 không
  phải P95. Với Summary thì P95 toàn hệ thống là con số không tồn tại.
- **Histogram** đếm theo bucket, mà bucket thì cộng được. `histogram_quantile()`
  của Prometheus gộp mọi worker rồi mới nội suy — nên P95/P99 là của cả service.

Đánh đổi: histogram chỉ *nội suy* trong bucket, nên độ chính xác phụ thuộc việc
chọn mép bucket. Đó là lý do `_LATENCY_BUCKETS` bên dưới được chọn tay theo hình
dạng traffic thật của Havi, không dùng default của thư viện.
"""

import time
from collections.abc import Awaitable, Callable

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)
from prometheus_client.core import CollectorRegistry as _Registry

#: Mép bucket tính bằng giây, chọn tay.
#:
#: Default của prometheus_client (`.005 … 10`) dồn quá nhiều độ phân giải vào
#: vùng dưới 100ms — chỗ Havi gần như không có request nào — rồi nhảy 2.5→5→10 ở
#: đúng vùng cần đo. Havi có hai nhóm traffic rất khác nhau:
#:
#: - CRUD + đọc DB: chục tới trăm ms.
#: - Đường gọi LLM/Graph API: nhiều giây, thỉnh thoảng chục giây.
#:
#: Có mép ở 30 và 60 để phân biệt "chậm" với "gần chạm timeout" — thiếu chúng thì
#: mọi thứ trên 10s rơi vào `+Inf` và P99 không còn nói được gì. Đổi danh sách
#: này là reset lịch sử histogram, nên đừng chỉnh nếu không có lý do từ dữ liệu.
_LATENCY_BUCKETS = (
    0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0,
)

#: Registry riêng, không dùng REGISTRY toàn cục.
#:
#: Global registry mang sẵn collector của chính process Python (GC, fd, RSS…) và
#: bị import ở nhiều chỗ, nên `pytest` chạy hai test cùng tạo app sẽ ném
#: "Duplicated timeseries" — lỗi ở tầng test, không phải tầng logic. Registry
#: tường minh cũng khiến việc reset trong test là một dòng.
REGISTRY: CollectorRegistry = _Registry()

http_requests_total = Counter(
    "havi_http_requests_total",
    "Số HTTP request đã xử lý.",
    # `path` là **route template** (`/content/{item_id}`), không phải URL thật.
    # Dùng URL thật thì mỗi UUID sinh một time series mới — cardinality bùng nổ
    # và Prometheus OOM. Đây là cách hỏng phổ biến nhất của metrics HTTP.
    labelnames=("method", "path", "status"),
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    "havi_http_request_duration_seconds",
    "Độ trễ HTTP request. Dùng histogram_quantile() để ra P95/P99.",
    labelnames=("method", "path"),
    buckets=_LATENCY_BUCKETS,
    registry=REGISTRY,
)

#: Không gắn label `status`: một request đang bay thì chưa có status code, và
#: gắn label rồi điền sau là cách chắc chắn để gauge lệch vĩnh viễn.
http_requests_in_progress = Gauge(
    "havi_http_requests_in_progress",
    "Số request đang xử lý. Tăng đều mà không giảm là dấu hiệu leak/deadlock.",
    registry=REGISTRY,
)

#: Đo *đường publish*, tách khỏi HTTP: bài lên Facebook đi qua Celery worker nên
#: không có HTTP request nào đại diện cho nó. Đây là chỉ số sát tiền nhất của
#: Havi — publish lỗi là khách mất bài.
publish_attempts_total = Counter(
    "havi_publish_attempts_total",
    "Lượt publish lên nền tảng, theo kết quả.",
    labelnames=("platform", "outcome"),
    registry=REGISTRY,
)

publish_duration_seconds = Histogram(
    "havi_publish_duration_seconds",
    "Độ trễ một lượt publish lên nền tảng.",
    labelnames=("platform",),
    buckets=_LATENCY_BUCKETS,
    registry=REGISTRY,
)

#: Provider LLM nào đang phục vụ, và fallback có đang xảy ra không. Ghép với
#: circuit breaker bên dưới để trả lời "vì sao bài này chậm/đắt".
llm_requests_total = Counter(
    "havi_llm_requests_total",
    "Lượt gọi provider LLM, theo kết quả.",
    labelnames=("provider", "outcome"),
    registry=REGISTRY,
)

llm_duration_seconds = Histogram(
    "havi_llm_duration_seconds",
    "Độ trễ một lượt gọi provider LLM.",
    labelnames=("provider",),
    buckets=_LATENCY_BUCKETS,
    registry=REGISTRY,
)

#: 0=closed, 1=open, 2=half_open. Gauge chứ không Counter: đây là *trạng thái*
#: hiện tại, không phải số lần xảy ra.
circuit_breaker_state = Gauge(
    "havi_circuit_breaker_state",
    "Trạng thái circuit breaker (0=closed, 1=open, 2=half_open).",
    labelnames=("name",),
    registry=REGISTRY,
)

circuit_breaker_rejections_total = Counter(
    "havi_circuit_breaker_rejections_total",
    "Số lần breaker chặn sớm, không gọi upstream.",
    labelnames=("name",),
    registry=REGISTRY,
)

#: Outbox tồn đọng. Alert đặt trên chỉ số này: nó tăng nghĩa là job đã commit
#: nhưng không ai đẩy đi — đúng tình huống Outbox sinh ra để lộ diện.
outbox_pending = Gauge(
    "havi_outbox_pending",
    "Số bản ghi outbox chờ đẩy.",
    registry=REGISTRY,
)

outbox_dispatched_total = Counter(
    "havi_outbox_dispatched_total",
    "Số bản ghi outbox đã đẩy, theo kết quả.",
    labelnames=("outcome",),
    registry=REGISTRY,
)


def render_latest() -> tuple[bytes, str]:
    """Trả (payload, content_type) cho endpoint `/metrics`.

    Gunicorn/uvicorn nhiều worker: mỗi worker là một process với counter riêng,
    nên scrape một cổng chỉ thấy số của một worker. `PROMETHEUS_MULTIPROC_DIR`
    là cách chính thức để gộp — nếu biến đó được đặt thì đọc từ đấy.
    """
    import os

    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registry = _Registry()
        multiprocess.MultiProcessCollector(registry)
    else:
        registry = REGISTRY
    from prometheus_client import CONTENT_TYPE_LATEST

    return generate_latest(registry), CONTENT_TYPE_LATEST


async def observe_publish[T](
    platform: str, call: Callable[[], Awaitable[T]]
) -> T:
    """Bọc một lượt publish để ghi counter + histogram.

    Đặt ở đây chứ không rải `time.perf_counter()` trong từng publisher: 9
    publisher thì 9 chỗ có thể quên giảm gauge hoặc quên ghi nhánh lỗi, và một
    metric sai lặng lẽ còn tệ hơn không có metric.
    """
    started = time.perf_counter()
    try:
        result = await call()
    except Exception:
        publish_attempts_total.labels(platform=platform, outcome="error").inc()
        publish_duration_seconds.labels(platform=platform).observe(
            time.perf_counter() - started
        )
        raise
    publish_attempts_total.labels(platform=platform, outcome="ok").inc()
    publish_duration_seconds.labels(platform=platform).observe(
        time.perf_counter() - started
    )
    return result
