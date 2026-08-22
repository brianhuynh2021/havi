"""Integration tests cho /voice API router."""

import base64

import pytest
from httpx import AsyncClient


async def _onboard(client: AsyncClient, *, email: str) -> dict:
    signup = await client.post(
        "/auth/sign-up", json={"name": "Chị Hương", "email": email, "password": "matkhau123"}
    )
    assert signup.status_code == 201, signup.text
    token_pair = signup.json()
    create = await client.post(
        "/workspaces",
        json={"name": "Spa An Nhiên", "industry": "spa"},
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert create.status_code == 201, create.text
    refreshed = await client.post(
        "/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    return refreshed.json()


def _headers(token_pair: dict) -> dict:
    return {"Authorization": f"Bearer {token_pair['access_token']}"}


@pytest.mark.asyncio
async def test_voice_transcribe_base64(client: AsyncClient):
    headers = _headers(await _onboard(client, email="voice.base64@havi.vn"))

    fake_audio_b64 = base64.b64encode(b"audio-data-test-voice").decode("utf-8")
    payload = {
        "audio_base64": fake_audio_b64,
        "mime_type": "audio/webm",
    }

    res = await client.post("/voice/transcribe", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "text" in data
    assert "summary" in data
    assert "detected_intent" in data
    assert len(data["text"]) > 0


@pytest.mark.asyncio
async def test_voice_transcribe_empty_audio_rejected(client: AsyncClient):
    headers = _headers(await _onboard(client, email="voice.empty@havi.vn"))

    payload = {
        "audio_base64": "",
        "mime_type": "audio/webm",
    }

    res = await client.post("/voice/transcribe", json=payload, headers=headers)
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_voice_transcribe_invalid_mime_rejected(client: AsyncClient):
    headers = _headers(await _onboard(client, email="voice.invalid@havi.vn"))

    payload = {
        "audio_base64": base64.b64encode(b"dummy-text").decode("utf-8"),
        "mime_type": "text/plain",
    }

    res = await client.post("/voice/transcribe", json=payload, headers=headers)
    assert res.status_code == 415


@pytest.mark.asyncio
async def test_voice_to_content_1tap(client: AsyncClient):
    headers = _headers(await _onboard(client, email="voice.1tap@havi.vn"))

    fake_audio_b64 = base64.b64encode(b"audio-idea-data-bytes").decode("utf-8")
    payload = {
        "audio_base64": fake_audio_b64,
        "mime_type": "audio/mp4",
    }

    res = await client.post("/voice/voice-to-content", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "job_id" in data
    assert data["job_status"] == "queued"
    assert "text" in data
    assert len(data["text"]) > 0


@pytest.mark.asyncio
async def test_voice_tts_generate_audio(client: AsyncClient):
    headers = _headers(await _onboard(client, email="voice.tts@havi.vn"))

    payload = {
        "text": "Chào mừng quý khách đến với dịch vụ của tiệm!",
        "voice": "vi-VN-HoaiMyNeural",
        "rate": "+0%",
    }

    res = await client.post("/voice/tts", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    assert res.headers["content-type"] == "audio/mpeg"
    assert len(res.content) > 1000
