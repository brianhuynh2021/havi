"""Circuit breaker — ngừng gọi upstream đang chết, thay vì gọi rồi chờ timeout.

Vì sao cần, khi `ProviderRouter` đã có fallback: fallback xử lý *một* request
lỗi rất tốt, nhưng nó không **ghi nhớ**. Gemini sập 10 phút thì mỗi request vẫn
gọi Gemini trước, chờ hết timeout, rồi mới rơi xuống Anthropic. Với timeout 30s
thì mỗi bài viết chậm thêm 30 giây và Havi vẫn trả tiền cho những kết nối chắc
chắn thất bại. Breaker biến "thử rồi chờ" thành "biết mà bỏ qua".

Ba trạng thái:

    closed ──(đủ lỗi liên tiếp)──▶ open ──(hết reset_timeout)──▶ half_open
       ▲                                                            │
       └────────────(đủ lần thành công liên tiếp)───────────────────┘
                              (một lỗi ở half_open → open lại)

Vài quyết định có chủ ý:

- **Đếm lỗi liên tiếp, không đếm tỷ lệ.** Tỷ lệ cần cửa sổ trượt và số mẫu tối
  thiểu; ở lưu lượng thấp của Havi (vài chục bài/ngày) cửa sổ đó gần như luôn
  dưới ngưỡng mẫu, nên breaker sẽ không bao giờ mở. Lỗi liên tiếp là tín hiệu
  đúng ở quy mô này.

- **Half-open cho đúng `half_open_max_calls` request đi qua.** Không mở van hoàn
  toàn: nếu upstream vẫn chết thì cả một đợt request lại treo — đúng cái vừa
  tránh được.

- **Chỉ transient mới tính là lỗi.** Prompt bị từ chối vì policy (permanent) là
  lỗi của *input*, không phải của upstream; đếm nó sẽ mở breaker trên một
  provider hoàn toàn khoẻ mạnh. Caller quyết định lỗi nào đáng đếm qua
  `record_failure`.

- **Trạng thái trong process, không ở Redis.** Cố ý: mỗi worker học độc lập, và
  đánh đổi ở đây nghiêng về sự đơn giản — một breaker chia sẻ qua Redis thì
  chính Redis thành điểm chết mới, và một worker gặp lỗi mạng cục bộ sẽ chặn
  luôn provider của mọi worker khác. Thời gian hội tụ chậm hơn là giá phải trả
  và ở lưu lượng này nó không đáng kể.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum

from core.metrics import circuit_breaker_rejections_total, circuit_breaker_state

logger = logging.getLogger("havi.circuit_breaker")


class BreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


_STATE_METRIC_VALUE = {
    BreakerState.CLOSED: 0,
    BreakerState.OPEN: 1,
    BreakerState.HALF_OPEN: 2,
}


class CircuitOpenError(Exception):
    """Breaker đang mở — không gọi upstream.

    Caller (ví dụ `ProviderRouter`) bắt lỗi này và coi như một lần thất bại
    *tức thì* của provider đó, rồi chuyển sang provider kế tiếp.
    """

    def __init__(self, name: str, retry_after_seconds: float) -> None:
        super().__init__(
            f"circuit '{name}' đang mở, thử lại sau ~{retry_after_seconds:.0f}s"
        )
        self.name = name
        self.retry_after_seconds = retry_after_seconds


@dataclass
class CircuitBreaker:
    """Một breaker cho một upstream. Không thread-safe theo thiết kế.

    Havi chạy asyncio một luồng mỗi process, nên các thao tác ở đây không bị cắt
    ngang giữa dòng. Thêm `asyncio.Lock` sẽ tạo cảm giác an toàn cho trường hợp
    (multi-thread) vốn không tồn tại, và tự nó thành điểm tranh chấp.
    """

    name: str
    #: 5 lỗi liên tiếp: đủ cao để một lần chớp nhoáng không mở breaker, đủ thấp
    #: để một outage thật bị chặn trong vòng vài request.
    failure_threshold: int = 5
    #: 60s — cân giữa "phục hồi nhanh khi upstream sống lại" và "không dồn dập
    #: thử lại vào một hệ thống đang gượng dậy".
    reset_timeout_seconds: float = 60.0
    #: Cần 2 lần thành công liên tiếp mới đóng hẳn. Một lần có thể là may.
    success_threshold: int = 2
    half_open_max_calls: int = 1

    _state: BreakerState = field(default=BreakerState.CLOSED, init=False)
    _consecutive_failures: int = field(default=0, init=False)
    _consecutive_successes: int = field(default=0, init=False)
    _opened_at: float = field(default=0.0, init=False)
    _half_open_calls: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self._publish_state()

    # -- trạng thái ----------------------------------------------------------

    @property
    def state(self) -> BreakerState:
        """Trạng thái *hiệu lực*, đã tính tới việc hết `reset_timeout`.

        Tính lười ở đây thay vì chạy timer nền: không có task nào phải quản lý
        vòng đời, và không có breaker nào bị bỏ quên ở trạng thái mở vì timer đã
        chết cùng một exception ở chỗ khác.
        """
        if self._state is BreakerState.OPEN and self._elapsed_since_open() >= (
            self.reset_timeout_seconds
        ):
            self._transition(BreakerState.HALF_OPEN)
            self._half_open_calls = 0
            self._consecutive_successes = 0
        return self._state

    def _elapsed_since_open(self) -> float:
        return time.monotonic() - self._opened_at

    def _transition(self, new_state: BreakerState) -> None:
        if new_state is self._state:
            return
        logger.warning("circuit '%s': %s → %s", self.name, self._state, new_state)
        self._state = new_state
        self._publish_state()

    def _publish_state(self) -> None:
        circuit_breaker_state.labels(name=self.name).set(_STATE_METRIC_VALUE[self._state])

    # -- cửa vào -------------------------------------------------------------

    def allows_request(self) -> bool:
        """Có nên gọi upstream không. Gọi `record_*` sau đó để báo kết quả."""
        state = self.state
        if state is BreakerState.CLOSED:
            return True
        if state is BreakerState.OPEN:
            circuit_breaker_rejections_total.labels(name=self.name).inc()
            return False
        # HALF_OPEN: nhỏ giọt vài request để thăm dò.
        if self._half_open_calls < self.half_open_max_calls:
            self._half_open_calls += 1
            return True
        circuit_breaker_rejections_total.labels(name=self.name).inc()
        return False

    def raise_if_open(self) -> None:
        """Như `allows_request` nhưng ném lỗi — tiện cho caller dùng try/except."""
        if not self.allows_request():
            remaining = max(0.0, self.reset_timeout_seconds - self._elapsed_since_open())
            raise CircuitOpenError(self.name, remaining)

    # -- phản hồi kết quả ----------------------------------------------------

    def record_success(self) -> None:
        self._consecutive_failures = 0
        if self._state is BreakerState.HALF_OPEN:
            self._consecutive_successes += 1
            if self._consecutive_successes >= self.success_threshold:
                self._transition(BreakerState.CLOSED)
                self._consecutive_successes = 0
                self._half_open_calls = 0

    def record_failure(self) -> None:
        """Chỉ gọi cho lỗi *của upstream* (transient). Xem docstring module."""
        self._consecutive_successes = 0
        if self._state is BreakerState.HALF_OPEN:
            # Thăm dò thất bại: mở lại ngay và tính lại thời gian chờ từ đầu.
            self._open()
            return
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._open()

    def _open(self) -> None:
        self._transition(BreakerState.OPEN)
        self._opened_at = time.monotonic()
        self._half_open_calls = 0
        self._consecutive_failures = 0

    def reset(self) -> None:
        """Về closed. Dùng cho test và cho endpoint vận hành thủ công."""
        self._transition(BreakerState.CLOSED)
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._half_open_calls = 0
        self._opened_at = 0.0


class CircuitBreakerRegistry:
    """Giữ một breaker cho mỗi upstream, tạo khi cần.

    Registry thay vì biến module-level cho từng provider: tên upstream là dữ
    liệu runtime (`facebook`, `gemini`…), và test cần dọn sạch giữa các case mà
    không phải biết trước có những breaker nào.
    """

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, name: str, **kwargs: object) -> CircuitBreaker:
        breaker = self._breakers.get(name)
        if breaker is None:
            breaker = CircuitBreaker(name=name, **kwargs)  # type: ignore[arg-type]
            self._breakers[name] = breaker
        return breaker

    def all(self) -> dict[str, CircuitBreaker]:
        return dict(self._breakers)

    def reset_all(self) -> None:
        for breaker in self._breakers.values():
            breaker.reset()


#: Registry dùng chung trong process.
registry = CircuitBreakerRegistry()
