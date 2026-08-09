"""Kiểm tra app khởi động được và OpenAPI có đủ endpoint theo TECHNICAL_SPEC."""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


def test_health_khong_can_token(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Request-ID"]


def test_request_id_header_duoc_giu_lai(client: TestClient):
    response = client.get("/health", headers={"X-Request-ID": "req_test_123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req_test_123"


def test_http_request_log_la_json_va_khong_log_query(client: TestClient, caplog):
    caplog.set_level(logging.INFO, logger="havi.http")

    response = client.get(
        "/health?token=khong-duoc-log", headers={"X-Request-ID": "req_log_123"}
    )

    assert response.status_code == 200
    records = [record for record in caplog.records if record.name == "havi.http"]
    assert records
    payload = json.loads(records[-1].message)
    assert payload["event"] == "http.request"
    assert payload["request_id"] == "req_log_123"
    assert payload["method"] == "GET"
    assert payload["path"] == "/health"
    assert payload["status_code"] == 200
    assert isinstance(payload["duration_ms"], int)
    assert "khong-duoc-log" not in records[-1].message


@pytest.mark.parametrize(
    "path",
    [
        "/auth/sign-up",
        "/auth/login/email",
        "/workspaces",
        "/brand-profile",
        "/media",
        "/content",
        "/calendar",
        "/connections",
        "/inbox",
        "/leads",
        "/crm-messages",
        "/analytics/summary",
        "/analytics/operations",
        "/billing/subscription",
    ],
)
def test_openapi_co_du_domain(client: TestClient, path: str):
    assert path in client.get("/openapi.json").json()["paths"]


def test_endpoint_nghiep_vu_yeu_cau_bearer_token(client: TestClient):
    assert client.get("/content").status_code == 401
