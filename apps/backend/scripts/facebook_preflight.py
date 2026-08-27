"""Safe, offline readiness checks for Facebook-first development and pilot.

The command never prints credential values and never calls Meta. It catches the
configuration mistakes that otherwise appear halfway through OAuth or publish.
The default gate is deliberately local-only; public deployment requirements are
checked only when ``--mode pilot`` is requested explicitly.

Run from ``apps/backend`` with::

    .venv/bin/python scripts/facebook_preflight.py
    .venv/bin/python scripts/facebook_preflight.py --mode pilot
"""

import argparse
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from adapters.meta_graph import GRAPH_VERSION
from core.config import Settings
from domain.policies.media_reachability import unreachable_reason


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True


Mode = Literal["local", "pilot"]


def _local_checks(settings: Settings) -> list[Check]:
    credentials_set = bool(settings.facebook_client_id and settings.facebook_client_secret)
    return [
        Check(
            "Môi trường local",
            settings.env == "local",
            f"HAVI_ENV={settings.env}; gate mặc định chỉ dành cho máy local",
        ),
        Check(
            "An toàn side effect",
            settings.use_fake_publisher is True,
            (
                "Fake publisher đang bật; local không gọi Meta khi duyệt bài"
                if settings.use_fake_publisher
                else "Publisher thật đang bật; chỉ duyệt bài khi chủ động thử trên Page test"
            ),
            required=False,
        ),
        Check(
            "Facebook credentials local",
            credentials_set,
            (
                "App ID và App Secret đã được đặt (giá trị không được in)"
                if credentials_set
                else "Không bắt buộc cho test mocked; cần đặt khi chủ động thử OAuth thật"
            ),
            required=False,
        ),
        Check(
            "Meta Graph version",
            GRAPH_VERSION == "v26.0",
            f"OAuth, publish và reply đang dùng chung {GRAPH_VERSION}",
        ),
    ]


def _pilot_checks(settings: Settings) -> list[Check]:
    redirect = urlparse(settings.facebook_redirect_uri)
    web = urlparse(settings.web_base_url)
    return [
        Check(
            "Môi trường pilot",
            settings.env in {"staging", "production"},
            f"HAVI_ENV={settings.env}; pilot public không được chạy local",
        ),
        Check(
            "Publisher thật",
            settings.use_fake_publisher is False,
            "HAVI_USE_FAKE_PUBLISHER phải là false",
        ),
        Check(
            "Facebook App ID",
            bool(settings.facebook_client_id),
            "HAVI_FACEBOOK_CLIENT_ID đã được đặt",
        ),
        Check(
            "Facebook App Secret",
            bool(settings.facebook_client_secret),
            "HAVI_FACEBOOK_CLIENT_SECRET đã được đặt (giá trị không được in)",
        ),
        Check(
            "OAuth redirect HTTPS",
            redirect.scheme == "https" and bool(redirect.netloc),
            "HAVI_FACEBOOK_REDIRECT_URI phải là URL HTTPS công khai",
        ),
        Check(
            "Webhook verify token",
            bool(settings.meta_webhook_verify_token),
            "HAVI_META_WEBHOOK_VERIFY_TOKEN phải là secret riêng, khớp Meta Dashboard",
        ),
        Check(
            "Media công khai",
            unreachable_reason(settings.media_public_url) is None,
            "HAVI_MEDIA_PUBLIC_URL phải tải được từ Internet để Meta lấy ảnh/video",
        ),
        Check(
            "Web URL HTTPS",
            web.scheme == "https" and bool(web.netloc),
            "HAVI_WEB_BASE_URL phải là URL HTTPS công khai",
        ),
        Check(
            "Login for Business",
            bool(settings.facebook_config_id),
            (
                "HAVI_FACEBOOK_CONFIG_ID đã được đặt"
                if settings.facebook_config_id
                else "Không có config ID: chỉ hợp lệ nếu chủ động dùng classic Login"
            ),
            required=False,
        ),
        Check(
            "Meta Graph version",
            GRAPH_VERSION == "v26.0",
            f"OAuth, publish và reply đang dùng chung {GRAPH_VERSION}",
        ),
    ]


def evaluate(settings: Settings, *, mode: Mode = "local") -> list[Check]:
    """Evaluate one explicit release gate without mixing local and public needs."""
    if mode == "local":
        return _local_checks(settings)
    return _pilot_checks(settings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("local", "pilot"),
        default="local",
        help="local (mặc định) hoặc pilot trước khi deploy thử nghiệm",
    )
    args = parser.parse_args()
    checks = evaluate(Settings(), mode=args.mode)
    for check in checks:
        if check.ok:
            label = "PASS"
        elif check.required:
            label = "FAIL"
        else:
            label = "WARN"
        print(f"[{label}] {check.name}: {check.detail}")

    required = [check for check in checks if check.required]
    passed = sum(1 for check in required if check.ok)
    failed = len(required) - passed
    warnings = sum(1 for check in checks if not check.required and not check.ok)
    print(
        f"\nFacebook {args.mode} preflight: {passed}/{len(required)} kiểm tra bắt buộc đạt"
        f"; {warnings} cảnh báo"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
