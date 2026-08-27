from core.config import Settings
from scripts.facebook_preflight import evaluate


def _settings(**overrides) -> Settings:
    base = {
        "env": "local",
        "use_fake_publisher": False,
        "facebook_client_id": "app-id",
        "facebook_client_secret": "app-secret",
        "facebook_redirect_uri": "https://api.havi.test/connections/facebook/callback",
        "facebook_config_id": "config-id",
        "meta_webhook_verify_token": "webhook-token",
        "media_public_url": "https://media.havi.test/havi-media",
        "web_base_url": "https://app.havi.test",
    }
    return Settings(**{**base, **overrides})


def test_preflight_does_not_expose_secret_values():
    settings = _settings(
        facebook_client_secret="never-print-this",
        meta_webhook_verify_token="never-print-this-either",
    )

    output = "\n".join(check.detail for check in evaluate(settings, mode="pilot"))

    assert "never-print-this" not in output
    assert "never-print-this-either" not in output


def test_local_gate_does_not_require_public_urls_or_webhook():
    checks = evaluate(
        _settings(
            facebook_redirect_uri="http://localhost:8000/connections/facebook/callback",
            meta_webhook_verify_token="",
            media_public_url="http://localhost:9000/havi-media",
            web_base_url="http://localhost:3000",
        )
    )

    assert all(check.ok for check in checks if check.required)
    assert all(check.name != "Webhook verify token" for check in checks)


def test_missing_webhook_token_is_a_required_pilot_failure():
    checks = evaluate(_settings(meta_webhook_verify_token=""), mode="pilot")
    webhook = next(check for check in checks if check.name == "Webhook verify token")

    assert webhook.required is True
    assert webhook.ok is False


def test_classic_login_is_warning_not_blocker():
    checks = evaluate(_settings(facebook_config_id=""), mode="pilot")
    login = next(check for check in checks if check.name == "Login for Business")

    assert login.required is False
    assert login.ok is False
