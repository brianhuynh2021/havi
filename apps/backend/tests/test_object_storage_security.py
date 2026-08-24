from unittest.mock import MagicMock

from adapters.storage.object_storage import ObjectStorage
from core.config import Settings


def test_nonlocal_media_urls_are_short_lived_and_use_external_endpoint(monkeypatch):
    internal = MagicMock()
    external = MagicMock()
    external.generate_presigned_post.return_value = {
        "url": "https://media.havi.vn/havi-media",
        "fields": {"policy": "signed"},
    }
    external.generate_presigned_url.return_value = (
        "https://media.havi.vn/havi-media/w1/a.jpg?X-Amz-Signature=signed"
    )
    clients = iter([internal, external])
    monkeypatch.setattr(
        "adapters.storage.object_storage.boto3.client", lambda *a, **k: next(clients)
    )

    settings = Settings(
        env="staging",
        use_mock_llm=False,
        use_fake_publisher=False,
        disable_rate_limit=False,
        email_provider="smtp",
        email_from="no-reply@havi.vn",
        smtp_host="smtp.havi.vn",
        media_endpoint_url="http://minio:9000",
        media_external_endpoint_url="https://media.havi.vn",
    )
    storage = ObjectStorage(settings)

    ticket = storage.create_upload_ticket(object_key="w1/a.jpg", content_type="image/jpeg")
    assert ticket.upload_url.startswith("https://media.havi.vn/")
    assert "X-Amz-Signature=" in storage.public_url("w1/a.jpg")
    external.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": "havi-media", "Key": "w1/a.jpg"},
        ExpiresIn=900,
    )
    internal.generate_presigned_url.assert_not_called()
