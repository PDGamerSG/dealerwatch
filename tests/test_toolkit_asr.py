from __future__ import annotations

import wave

import httpx
import pytest

from toolkit import asr
from toolkit.asr import SarvamClient, entries_from_response, entries_to_utterances, transcribe

CALL = {
    "call_id": "C-004",
    "dealer_id": "D1",
    "counterparty_number": "+919800000001",
    "start_time": "2026-09-03T12:10:00",
    "duration_s": 40,
    "audio_file": "audio/C-004.wav",
    "utterances": [
        {"id": "C-004-u01", "speaker": "D1", "start_ms": 0, "end_ms": 2100, "text": "Haan bhai, sun."},
        {"id": "C-004-u02", "speaker": "P-001", "start_ms": 2200, "end_ms": 4000, "text": "Bol."},
    ],
}
SARVAM_REPLY = {
    "request_id": "r-1",
    "transcript": "Bhai, INFY mein bada order aa raha hai. Theek hai.",
    "language_code": "hi-IN",
    "diarized_transcript": {"entries": [
        {"speaker_id": "0", "start_time_seconds": 0.0, "end_time_seconds": 2.5, "transcript": "Bhai, INFY mein bada order aa raha hai."},
        {"speaker_id": "1", "start_time_seconds": 2.6, "end_time_seconds": 3.4, "transcript": "Theek hai."},
    ]},
}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("DW_ASR", "SARVAM_API_KEY", "DW_SARVAM_MODEL"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def data_dir(tmp_path):
    (tmp_path / "audio").mkdir()
    with wave.open(str(tmp_path / "audio" / "C-004.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 8000)  # 1 s of silence
    return str(tmp_path)


def use_transport(monkeypatch, handler) -> None:
    monkeypatch.setattr(asr, "_make_client",
                        lambda key: SarvamClient(key, transport=httpx.MockTransport(handler), backoff_s=0))


def test_replay_returns_stored_utterances(data_dir):
    utterances, used = transcribe(CALL, data_dir)
    assert used == "replay"
    assert utterances == CALL["utterances"]


def test_sarvam_without_key_falls_back_to_replay(monkeypatch, data_dir):
    monkeypatch.setenv("DW_ASR", "sarvam")
    utterances, used = transcribe(CALL, data_dir)
    assert used == "replay" and [u["id"] for u in utterances] == ["C-004-u01", "C-004-u02"]


def test_sarvam_without_audio_falls_back(monkeypatch, data_dir):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    call = {**CALL, "audio_file": None}
    assert transcribe(call, data_dir, provider="sarvam")[1] == "replay"


def test_sarvam_rejects_audio_outside_data_dir(monkeypatch, data_dir):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    use_transport(monkeypatch, lambda request: httpx.Response(200, json=SARVAM_REPLY))
    call = {**CALL, "audio_file": "../outside.wav"}
    assert transcribe(call, data_dir, provider="sarvam")[1] == "replay"


def test_sarvam_success_maps_entries(monkeypatch, data_dir):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=SARVAM_REPLY)

    use_transport(monkeypatch, handler)
    utterances, used = transcribe(CALL, data_dir, provider="sarvam")
    assert used == "sarvam"
    assert utterances == [
        {"id": "C-004-u01", "speaker": "SPEAKER_00", "start_ms": 0, "end_ms": 2500,
         "text": "Bhai, INFY mein bada order aa raha hai."},
        {"id": "C-004-u02", "speaker": "SPEAKER_01", "start_ms": 2600, "end_ms": 3400, "text": "Theek hai."},
    ]
    request = seen[0]
    assert request.headers["api-subscription-key"] == "test-key"
    body = request.content
    assert b"with_diarization" in body and b"saaras" in body and b"codemix" in body


def test_sarvam_http_error_falls_back(monkeypatch, data_dir):
    monkeypatch.setenv("SARVAM_API_KEY", "test-key")
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503, json={"error": {"message": "busy"}})

    use_transport(monkeypatch, handler)
    utterances, used = transcribe(CALL, data_dir, provider="sarvam")
    assert used == "replay" and utterances == CALL["utterances"]
    assert len(calls) == 3  # first try + 2 retries


def test_entries_from_response_plain_transcript_and_offset():
    entries = entries_from_response({"transcript": "sirf text"}, offset_ms=28000)
    assert entries == [{"speaker_id": "0", "start_time_seconds": 28.0, "end_time_seconds": 28.0, "transcript": "sirf text"}]
    assert entries_from_response("garbage") == []
    assert entries_to_utterances("C-009", entries)[0]["id"] == "C-009-u01"
