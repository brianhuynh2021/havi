"""URL media giao cho nền tảng phải tải được **từ máy của nền tảng**.

Facebook, TikTok, YouTube và Google Business đều đăng ảnh/video theo cùng một
cách: ta đưa một đường link, **họ** đi tải về. Nghĩa là đường link đó được mở từ
máy chủ của Facebook ở nước ngoài, không phải từ máy đang chạy Havi.

Một URL `http://localhost:9000/...` là hợp lệ về mặt cú pháp và mở được hoàn hảo
trên máy lập trình viên. Đưa cho Facebook thì `localhost` trở thành *máy của
Facebook* — nơi không có gì cả. Đây là chuyện đã xảy ra thật, hai lần::

    [100] (#100) url should represent a valid URL
    [6000] There was a problem uploading your video file.

Hai thông báo đó không nói gì về nguyên nhân, nằm trong dead-letter dưới nhãn
"nội dung không hợp lệ", và khiến người đọc đi sửa bài đăng — trong khi bài đăng
không có lỗi gì, cấu hình mới có.

Vì vậy luật này chặn **trước khi gửi đi**: thà hỏng ở chỗ nói đúng nguyên nhân,
còn hơn hỏng ở chỗ nền tảng trả về một mã số khó hiểu.

Đây là chặn theo *cấu hình sai*, không phải chống SSRF. Một URL qua được hàm này
vẫn có thể trỏ tới nơi không tồn tại — chỉ có nền tảng mới biết chắc.
"""

from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import urlparse

__all__ = ["unreachable_reason"]

_PUBLIC_SCHEMES = frozenset({"http", "https"})

# Tên miền chỉ có nghĩa bên trong một máy hoặc một mạng nội bộ.
_LOCAL_HOSTS = frozenset({"localhost", "localhost.localdomain", "ip6-localhost"})

# Hậu tố dành riêng cho mạng nội bộ (RFC 6762, RFC 8375) và cho các bí danh mà
# Docker Compose tạo ra giữa các container.
_LOCAL_SUFFIXES = ("[.]local", ".localhost", ".internal", ".home.arpa")


def _host_is_local_name(host: str) -> bool:
    if host in _LOCAL_HOSTS:
        return True
    if any(host.endswith(suffix.replace("[.]", ".")) for suffix in _LOCAL_SUFFIXES):
        return True
    # `http://minio/...` hay `http://backend:8000/...` — tên service trong Docker
    # Compose. Không có dấu chấm nghĩa là không phải tên miền công khai.
    return "." not in host


def unreachable_reason(url: str) -> str | None:
    """Trả về lý do URL không tải được từ Internet, hoặc `None` nếu ổn.

    Trả chuỗi tiếng Việt đọc được, vì nó đi thẳng vào `failure_detail` mà người
    vận hành sẽ đọc — không phải mã lỗi để lập trình viên tra cứu.
    """
    parsed = urlparse(url)

    if parsed.scheme not in _PUBLIC_SCHEMES:
        # `blob:`, `data:`, `file:` — chỉ có nghĩa trong trình duyệt hoặc trên đĩa
        # của một máy cụ thể.
        return f"đường dẫn “{parsed.scheme or url[:24]}” không phải link tải được từ Internet"

    host = (parsed.hostname or "").lower()
    if not host:
        return "link media thiếu tên miền"

    if _host_is_local_name(host):
        return f"“{host}” chỉ có nghĩa trong mạng nội bộ — nền tảng ở nước ngoài không mở được"

    try:
        ip = ip_address(host)
    except ValueError:
        # Không phải địa chỉ IP thì là tên miền công khai. Tên miền đó có phân
        # giải ra IP nội bộ hay không thì phải hỏi DNS — ngoài phạm vi một luật
        # thuần tuý, và tra DNS trong domain policy là đem I/O vào chỗ không nên.
        return None

    if ip.is_loopback:
        return f"“{host}” là địa chỉ nội bộ của chính máy chủ — nền tảng không mở được"
    if ip.is_private or ip.is_link_local:
        return f"“{host}” là địa chỉ mạng nội bộ — nền tảng ở nước ngoài không mở được"
    if ip.is_unspecified:
        return f"“{host}” không trỏ tới máy nào"

    return None
