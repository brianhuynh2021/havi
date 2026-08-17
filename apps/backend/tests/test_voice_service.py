"""Test cho VoiceService và voice transcribers."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from adapters.voice.mock_transcriber import MockVoiceTranscriber
from application.services.voice_service import (
    AudioPayloadTooLargeError,
    InvalidAudioFormatError,
    VoiceService,
)
from domain.ports.voice_transcriber import VoiceTranscribeError

pytestmark = pytest.mark.anyio


def _mock_events():
    events = MagicMock()
    events.record = AsyncMock()
    return events


async def test_mock_voice_transcriber():
    transcriber = MockVoiceTranscriber()
    audio = b"fake-audio-bytes-123456"
    res = await transcriber.transcribe(audio, "audio/webm")

    assert "giảm 30%" in res.text
    assert res.detected_intent == "khuyen_mai"
    assert res.summary != ""


async def test_mock_voice_transcriber_empty_audio():
    transcriber = MockVoiceTranscriber()
    with pytest.raises(VoiceTranscribeError) as exc:
        await transcriber.transcribe(b"", "audio/webm")
    assert "rỗng" in str(exc.value)


async def test_voice_service_transcribe_success():
    transcriber = MockVoiceTranscriber(default_text="Khách quen ghé tiệm tặng voucher 50k")
    events = _mock_events()
    service = VoiceService(transcriber=transcriber, events=events)

    workspace_id = uuid4()
    audio = b"valid-audio-data"
    result = await service.transcribe_voice(
        workspace_id=workspace_id,
        audio_bytes=audio,
        mime_type="audio/mp4",
    )

    assert result.text == "Khách quen ghé tiệm tặng voucher 50k"
    assert events.record.called
    entry = events.record.call_args[0][0]
    assert entry.workspace_id == workspace_id
    assert entry.job_kind == "voice.transcribed"


async def test_voice_service_invalid_mime_rejected():
    transcriber = MockVoiceTranscriber()
    events = _mock_events()
    service = VoiceService(transcriber=transcriber, events=events)

    with pytest.raises(InvalidAudioFormatError) as exc:
        await service.transcribe_voice(
            workspace_id=uuid4(),
            audio_bytes=b"audio-data",
            mime_type="application/pdf",
        )
    assert "application/pdf" in str(exc.value)


async def test_voice_service_payload_too_large():
    transcriber = MockVoiceTranscriber()
    events = _mock_events()
    service = VoiceService(transcriber=transcriber, events=events)

    huge_audio = b"0" * (26 * 1024 * 1024)
    with pytest.raises(AudioPayloadTooLargeError) as exc:
        await service.transcribe_voice(
            workspace_id=uuid4(),
            audio_bytes=huge_audio,
            mime_type="audio/wav",
        )
    assert "25MB" in str(exc.value)


async def test_voice_to_content_pipeline():
    transcriber = MockVoiceTranscriber(default_text="Gội đầu thảo dược giảm 20k")
    events = _mock_events()
    service = VoiceService(transcriber=transcriber, events=events)

    mock_job = MagicMock()
    mock_job.id = uuid4()
    mock_job.status = MagicMock(value="queued")

    mock_content_service = MagicMock()
    mock_content_service.create_job = AsyncMock(return_value=MagicMock(job=mock_job))

    workspace_id = uuid4()
    transcribe_res, job = await service.voice_to_content(
        workspace_id=workspace_id,
        audio_bytes=b"audio-bytes",
        mime_type="audio/webm",
        content_service=mock_content_service,
    )

    assert transcribe_res.text == "Gội đầu thảo dược giảm 20k"
    assert job.id == mock_job.id
    assert mock_content_service.create_job.called
    raw_inputs = mock_content_service.create_job.call_args.kwargs["raw_inputs"]
    assert len(raw_inputs) == 1
    assert raw_inputs[0]["text"] == "Gội đầu thảo dược giảm 20k"
