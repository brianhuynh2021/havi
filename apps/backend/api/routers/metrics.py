"""`/metrics` — endpoint Prometheus scrape.

Không cần JWT: Prometheus không mang token người dùng, và scrape config chuẩn
không có chỗ để cắm OAuth. Bảo vệ bằng **mạng**, không bằng auth ở tầng app —
`deploy/nginx/nginx.conf` chỉ cho private range vào đường này, còn container thì
không publish cổng backend ra ngoài.

Nếu sau này cần phơi ra Internet (Grafana Cloud chẳng hạn), thêm bearer token
riêng cho scrape ở nginx, đừng dùng JWT người dùng: token đó không hết hạn được
và sẽ nằm trong config của Prometheus dưới dạng plaintext.
"""

from fastapi import APIRouter, Response

from core.metrics import render_latest

router = APIRouter(tags=["health"])


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    payload, content_type = render_latest()
    return Response(content=payload, media_type=content_type)
