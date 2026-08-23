"""Mặt phẳng dữ liệu vào của Station 4.

Trước khi có `api/routers/webhooks.py`, `inbox_items` không có đường nhận dữ liệu
thật nào: `process_inquiry` không được router nào gọi. Test ở đây khoá lại ba
tính chất mà một endpoint public không JWT bắt buộc phải có — xác thực chữ ký,
chống trùng khi nền tảng gửi lại, và không rò dữ liệu qua biên workspace.
"""

import hashlib
import hmac
import json

import pytest
from httpx import AsyncClient

from api.routers.webhooks import _iter_inquiries, _signature_matches
from core.config import get_settings
from core.enums import InboxItemType

APP_SECRET = "test-app-secret"
VERIFY_TOKEN = "test-verify-token"
PAGE_ID = "page_123"


@pytest.fixture(autouse=True)
def meta_settings(monkeypatch):
    monkeypatch.setenv("HAVI_FACEBOOK_CLIENT_SECRET", APP_SECRET)
    monkeypatch.setenv("HAVI_META_WEBHOOK_VERIFY_TOKEN", VERIFY_TOKEN)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _signed(payload: dict) -> tuple[bytes, dict[str, str]]:
    raw = json.dumps(payload).encode("utf-8")
    digest = hmac.new(APP_SECRET.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return raw, {
        "X-Hub-Signature-256": f"sha256={digest}",
        "Content-Type": "application/json",
    }


def _message_payload(*, mid: str, text: str, page_id: str = PAGE_ID) -> dict:
    return {
        "object": "page",
        "entry": [
            {
                "id": page_id,
                "messaging": [
                    {
                        "sender": {"id": "user_98765"},
                        "message": {"mid": mid, "text": text},
                    }
                ],
            }
        ],
    }


class TestSignatureVerification:
    def test_rejects_missing_header(self):
        assert not _signature_matches(app_secret=APP_SECRET, raw_body=b"{}", header=None)

    def test_rejects_wrong_digest(self):
        assert not _signature_matches(
            app_secret=APP_SECRET, raw_body=b"{}", header="sha256=deadbeef"
        )

    def test_rejects_unprefixed_digest(self):
        digest = hmac.new(APP_SECRET.encode(), b"{}", hashlib.sha256).hexdigest()
        assert not _signature_matches(app_secret=APP_SECRET, raw_body=b"{}", header=digest)

    def test_accepts_correct_digest(self):
        digest = hmac.new(APP_SECRET.encode(), b"{}", hashlib.sha256).hexdigest()
        assert _signature_matches(app_secret=APP_SECRET, raw_body=b"{}", header=f"sha256={digest}")

    def test_body_tampering_invalidates_signature(self):
        raw, headers = _signed(_message_payload(mid="m1", text="Bao nhiêu tiền ạ"))
        tampered = raw.replace(b"Bao nhieu", b"Bao nhieu ") if b"Bao nhieu" in raw else raw + b" "
        assert not _signature_matches(
            app_secret=APP_SECRET,
            raw_body=tampered,
            header=headers["X-Hub-Signature-256"],
        )


class TestPayloadParsing:
    def test_extracts_message(self):
        events = list(_iter_inquiries(_message_payload(mid="m1", text="Giá bao nhiêu")))
        assert len(events) == 1
        assert events[0].page_id == PAGE_ID
        assert events[0].message_id == "m1"
        assert events[0].text == "Giá bao nhiêu"
        assert events[0].item_type == InboxItemType.MESSAGE

    def test_extracts_feed_comment(self):
        payload = {
            "entry": [
                {
                    "id": PAGE_ID,
                    "changes": [
                        {
                            "field": "feed",
                            "value": {
                                "item": "comment",
                                "verb": "add",
                                "comment_id": "c1",
                                "message": "Tiệm còn chỗ không chị",
                                "from": {"name": "Chị Lan"},
                            },
                        }
                    ],
                }
            ]
        }
        events = list(_iter_inquiries(payload))
        assert len(events) == 1
        assert events[0].message_id == "c1"
        assert events[0].author_name == "Chị Lan"
        assert events[0].item_type == InboxItemType.COMMENT

    def test_skips_echo_of_page_own_message(self):
        payload = _message_payload(mid="m1", text="Cảm ơn chị")
        payload["entry"][0]["messaging"][0]["message"]["is_echo"] = True
        assert list(_iter_inquiries(payload)) == []

    def test_skips_comment_edits_and_removals(self):
        payload = {
            "entry": [
                {
                    "id": PAGE_ID,
                    "changes": [
                        {
                            "field": "feed",
                            "value": {
                                "item": "comment",
                                "verb": "remove",
                                "comment_id": "c1",
                                "message": "xoá",
                            },
                        }
                    ],
                }
            ]
        }
        assert list(_iter_inquiries(payload)) == []

    def test_skips_empty_text_and_missing_ids(self):
        assert list(_iter_inquiries(_message_payload(mid="m1", text="   "))) == []
        payload = _message_payload(mid="m1", text="hi")
        del payload["entry"][0]["messaging"][0]["message"]["mid"]
        assert list(_iter_inquiries(payload)) == []

    def test_tolerates_empty_and_malformed_payloads(self):
        assert list(_iter_inquiries({})) == []
        assert list(_iter_inquiries({"entry": None})) == []
        assert list(_iter_inquiries({"entry": [{}]})) == []


class TestWebhookEndpoint:
    @pytest.mark.asyncio
    async def test_verification_handshake_returns_challenge(self, client: AsyncClient):
        resp = await client.get(
            "/webhooks/meta",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": VERIFY_TOKEN,
                "hub.challenge": "1158201444",
            },
        )
        assert resp.status_code == 200
        assert resp.text == "1158201444"

    @pytest.mark.asyncio
    async def test_verification_rejects_wrong_token(self, client: AsyncClient):
        resp = await client.get(
            "/webhooks/meta",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "sai",
                "hub.challenge": "x",
            },
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unsigned_post_is_rejected(self, client: AsyncClient):
        resp = await client.post("/webhooks/meta", json=_message_payload(mid="m1", text="hi"))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unknown_page_is_skipped_not_errored(self, client: AsyncClient):
        raw, headers = _signed(_message_payload(mid="m1", text="Giá bao nhiêu ạ"))
        resp = await client.post("/webhooks/meta", content=raw, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"accepted": 0, "skipped": 1}


class TestLocalSimulator:
    @pytest.mark.asyncio
    async def test_simulated_inquiry_lands_in_inbox(self, client: AsyncClient):
        headers = await _onboard(client, "webhook.sim@havi.vn")

        resp = await client.post(
            "/webhooks/dev/simulate",
            json={"content": "Tiệm còn chỗ chiều nay không ạ", "author_name": "Chị Lan"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "drafted"

        listing = await client.get("/inbox", headers=headers)
        assert listing.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_same_external_id_does_not_duplicate(self, client: AsyncClient):
        headers = await _onboard(client, "webhook.dedupe@havi.vn")
        body = {
            "content": "Bao nhiêu tiền một buổi ạ",
            "author_name": "Chị Lan",
            "external_message_id": "mid_abc",
        }

        first = await client.post("/webhooks/dev/simulate", json=body, headers=headers)
        second = await client.post("/webhooks/dev/simulate", json=body, headers=headers)

        assert first.json()["id"] == second.json()["id"]
        listing = await client.get("/inbox", headers=headers)
        assert listing.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_exact_faq_auto_replies_but_substring_does_not(self, client: AsyncClient):
        headers = await _onboard(client, "webhook.faq@havi.vn")
        await client.put(
            "/brand-profile",
            json={
                "faq": [
                    {
                        "question": "Giờ mở cửa",
                        "answer": "Tiệm mở 8:00-21:00 ạ!",
                        "approved": True,
                    }
                ]
            },
            headers=headers,
        )

        exact = await client.post(
            "/webhooks/dev/simulate",
            json={"content": "giờ mở cửa?", "external_message_id": "m_exact"},
            headers=headers,
        )
        assert exact.json()["status"] == "sent"

        # Câu dài chỉ *chứa* câu FAQ thì không được tự gửi — đó là cách bản cũ
        # sai, và nó gửi nhầm câu trả lời cho khách.
        loose = await client.post(
            "/webhooks/dev/simulate",
            json={
                "content": "Chị ơi giờ mở cửa chi nhánh Quận 7 có khác không ạ",
                "external_message_id": "m_loose",
            },
            headers=headers,
        )
        assert loose.json()["status"] == "drafted"

    @pytest.mark.asyncio
    async def test_unapproved_faq_is_never_auto_sent(self, client: AsyncClient):
        headers = await _onboard(client, "webhook.unapproved@havi.vn")
        await client.put(
            "/brand-profile",
            json={
                "faq": [
                    {
                        "question": "Giá gội đầu",
                        "answer": "150k ạ",
                        "approved": False,
                    }
                ]
            },
            headers=headers,
        )

        resp = await client.post(
            "/webhooks/dev/simulate",
            json={"content": "giá gội đầu"},
            headers=headers,
        )
        assert resp.json()["status"] == "drafted"

    @pytest.mark.asyncio
    async def test_simulator_blocked_outside_local(self, client: AsyncClient):
        """Ngoài local thì endpoint mô phỏng phải biến mất.

        Kiểm ở tầng handler bằng cách thay `settings.env`: bật hẳn
        `HAVI_ENV=staging` thì `Settings` từ chối khởi tạo vì mock LLM / fake
        publisher / email debug của test suite cũng bị chặn theo — chính guardrail
        đó đã được `test_config_guardrails` phủ riêng.
        """
        headers = await _onboard(client, "webhook.staging@havi.vn")
        settings = get_settings()
        object.__setattr__(settings, "env", "staging")
        try:
            resp = await client.post(
                "/webhooks/dev/simulate",
                json={"content": "test"},
                headers=headers,
            )
        finally:
            object.__setattr__(settings, "env", "local")

        assert resp.status_code == 404


async def _onboard(client: AsyncClient, email: str) -> dict:
    signup = await client.post(
        "/auth/sign-up",
        json={"name": "Chị Mai", "email": email, "password": "matkhau123"},
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()

    headers = {"Authorization": f"Bearer {token_pair['access_token']}"}
    create = await client.post(
        "/workspaces",
        json={"name": "Tiệm Mai Q7", "industry": "spa"},
        headers=headers,
    )
    assert create.status_code == 201, create.text

    refreshed = await client.post(
        "/auth/refresh",
        headers={"Authorization": f"Bearer {token_pair['refresh_token']}"},
    )
    assert refreshed.status_code == 200, refreshed.text
    return {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
