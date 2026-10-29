"""Speech-to-text for recorded calls: replay | sarvam.

`replay` returns the transcript already stored with the call. `sarvam` sends the call's audio to
Sarvam AI speech-to-text (Saaras, code-mixed Hinglish mode, with diarisation); on any error (no key,
no audio, HTTP failure, empty transcript) it falls back to replay. Responses are untrusted data:
only documented fields are read and numbers are coerced defensively.

The Sarvam client below is adapted from Kyun (MIT, Team Vulcan), src/kyun/kt/sarvam.py
(SarvamClient.transcribe_short, entries_from_response, split_wav_windows), trimmed to the
synchronous endpoint. Generic: no project imports.
"""
from __future__ import annotations

import io
import logging
import os
import time
import wave
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger("toolkit.asr")

PROVIDERS = ("replay", "sarvam")
SARVAM_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_MODEL = "saaras:v4"
SARVAM_MODE = "codemix"
SHORT_LIMIT_SECONDS = 30.0
WINDOW_SECONDS = 28.0
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=60.0, pool=10.0)


class SarvamError(RuntimeError):
    """Sarvam refused or failed a request."""


# ---------- audio + response helpers (adapted from Kyun) ----------


def wav_duration_seconds(audio: bytes) -> float | None:
    """Duration of a WAV container, or None when the bytes are not WAV."""
    try:
        with wave.open(io.BytesIO(audio), "rb") as src:
            return src.getnframes() / float(src.getframerate() or 1)
    except (wave.Error, EOFError, OSError):
        return None


def split_wav_windows(audio: bytes, seconds: float = WINDOW_SECONDS) -> list[tuple[int, bytes]]:
    """Cut a WAV into [(offset_ms, wav_bytes)] windows of at most `seconds`; non-WAV comes back whole."""
    try:
        with wave.open(io.BytesIO(audio), "rb") as src:
            params = src.getparams()
            total = src.getnframes()
            per_window = max(1, int(seconds * params.framerate))
            windows: list[tuple[int, bytes]] = []
            pos = 0
            while pos < total:
                src.setpos(pos)
                frames = src.readframes(min(per_window, total - pos))
                out = io.BytesIO()
                with wave.open(out, "wb") as dst:
                    dst.setnchannels(params.nchannels)
                    dst.setsampwidth(params.sampwidth)
                    dst.setframerate(params.framerate)
                    dst.writeframes(frames)
                windows.append((round(pos * 1000 / params.framerate), out.getvalue()))
                pos += per_window
            return windows or [(0, audio)]
    except (wave.Error, EOFError, OSError):
        return [(0, audio)]


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def entries_from_response(resp: Any, *, offset_ms: int = 0) -> list[dict[str, Any]]:
    """Diarised entries {speaker_id, start_time_seconds, end_time_seconds, transcript} shifted by
    `offset_ms`; falls back to the plain `transcript` as one entry when diarisation is absent."""
    if not isinstance(resp, dict):
        return []
    shift = offset_ms / 1000.0
    out: list[dict[str, Any]] = []
    diarized = resp.get("diarized_transcript")
    for e in (diarized.get("entries") if isinstance(diarized, dict) else None) or []:
        if not isinstance(e, dict):
            continue
        text = str(e.get("transcript") or "").strip()
        if not text:
            continue
        start = _num(e.get("start_time_seconds")) + shift
        end = max(start, _num(e.get("end_time_seconds"), _num(e.get("start_time_seconds"))) + shift)
        out.append({"speaker_id": str(e.get("speaker_id") or "0"), "start_time_seconds": start,
                    "end_time_seconds": end, "transcript": text})
    if not out:
        text = str(resp.get("transcript") or "").strip()
        if text:
            out.append({"speaker_id": "0", "start_time_seconds": shift, "end_time_seconds": shift, "transcript": text})
    return out


class SarvamClient:
    """Minimal retrying client for Sarvam's synchronous `POST /speech-to-text` (<= 30 s per request)."""

    def __init__(self, api_key: str, *, model: str = SARVAM_MODEL, mode: str = SARVAM_MODE,
                 transport: httpx.BaseTransport | None = None, retries: int = 2, backoff_s: float = 1.0):
        if not api_key or not api_key.strip():
            raise SarvamError("SARVAM_API_KEY is not configured")
        self._api_key = api_key.strip()
        self.model, self.mode = model, mode
        self.retries, self.backoff_s = max(0, retries), backoff_s
        self._http = httpx.Client(transport=transport, timeout=_TIMEOUT)

    def close(self) -> None:
        self._http.close()

    def transcribe_short(self, audio: bytes, filename: str, *, diarize: bool = True) -> dict[str, Any]:
        """One clip of at most 30 s; returns the raw response (transcript, diarized_transcript, ...)."""
        duration = wav_duration_seconds(audio)
        if duration is not None and duration > SHORT_LIMIT_SECONDS:
            raise SarvamError(f"clip is {duration:.1f} s; the synchronous endpoint takes at most 30 s")
        data = {"model": self.model, "mode": self.mode, "language_code": "unknown", "with_timestamps": "true"}
        if diarize:
            data["with_diarization"] = "true"
        files = {"file": (filename, audio, "audio/wav" if filename.lower().endswith(".wav") else "application/octet-stream")}
        headers = {"api-subscription-key": self._api_key}
        for attempt in range(self.retries + 1):
            try:
                response = self._http.post(SARVAM_URL, data=data, files=files, headers=headers)
            except httpx.HTTPError as exc:
                if attempt < self.retries:
                    time.sleep(self.backoff_s * 2 ** attempt)
                    continue
                raise SarvamError(f"Sarvam request failed: {type(exc).__name__}") from exc
            if response.status_code in _RETRY_STATUS and attempt < self.retries:
                time.sleep(self.backoff_s * 2 ** attempt)
                continue
            if response.status_code >= 400:
                raise SarvamError(f"Sarvam returned HTTP {response.status_code}")
            try:
                body = response.json()
            except ValueError as exc:
                raise SarvamError("Sarvam returned a non-JSON body") from exc
            if not isinstance(body, dict) or not isinstance(body.get("transcript"), str):
                raise SarvamError("speech-to-text response has no transcript")
            return body
        raise SarvamError("Sarvam request failed after retries")  # pragma: no cover - defensive

    def transcribe(self, audio: bytes, filename: str) -> list[dict[str, Any]]:
        """Whole recording via <= 28 s windows, timestamps shifted back onto the call timeline."""
        entries: list[dict[str, Any]] = []
        for offset_ms, chunk in split_wav_windows(audio):
            entries.extend(entries_from_response(self.transcribe_short(chunk, filename), offset_ms=offset_ms))
        return entries


# ---------- public API ----------


def _speaker_label(raw: str) -> str:
    """Sarvam numbers speakers per request ("0", "1" or "SPEAKER_00"); keep that, normalised."""
    digits = "".join(ch for ch in raw if ch.isdigit())
    return f"SPEAKER_{int(digits):02d}" if digits else (raw or "UNKNOWN")


def entries_to_utterances(call_id: str, entries: list[dict[str, Any]]) -> list[dict]:
    """Map Sarvam entries to utterance dicts with ids `<call_id>-uNN` (1-based)."""
    return [{"id": f"{call_id}-u{i:02d}", "speaker": _speaker_label(str(e.get("speaker_id") or "")),
             "start_ms": int(round(_num(e.get("start_time_seconds")) * 1000)),
             "end_ms": int(round(_num(e.get("end_time_seconds")) * 1000)),
             "text": str(e.get("transcript") or "")}
            for i, e in enumerate(entries, start=1)]


def _replay(call: dict) -> list[dict]:
    out = []
    for u in call.get("utterances") or []:
        if hasattr(u, "model_dump"):
            u = u.model_dump()
        out.append({"id": str(u.get("id")), "speaker": str(u.get("speaker") or "UNKNOWN"),
                    "start_ms": int(u.get("start_ms") or 0), "end_ms": int(u.get("end_ms") or 0),
                    "text": str(u.get("text") or "")})
    return out


def _audio_path(call: dict, data_dir: str) -> Path:
    rel = call.get("audio_file")
    if not rel:
        raise SarvamError("call has no audio_file")
    base = Path(data_dir).resolve()
    path = (base / str(rel)).resolve()
    if base != path and base not in path.parents:
        raise SarvamError("audio_file points outside the data directory")
    if not path.is_file():
        raise SarvamError("audio file not found")
    return path


def _make_client(api_key: str) -> SarvamClient:
    return SarvamClient(api_key, model=os.environ.get("DW_SARVAM_MODEL") or SARVAM_MODEL)


def _sarvam(call: dict, data_dir: str) -> list[dict]:
    api_key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not api_key:
        raise SarvamError("SARVAM_API_KEY is not set")
    path = _audio_path(call, data_dir)
    client = _make_client(api_key)
    try:
        entries = client.transcribe(path.read_bytes(), path.name)
    finally:
        client.close()
    if not entries:
        raise SarvamError("empty transcript")
    return entries_to_utterances(str(call.get("call_id") or path.stem), entries)


def transcribe(call: dict, data_dir: str, provider: str | None = None) -> tuple[list[dict], str]:
    """(utterances, provider_used). Provider from `provider` or env `DW_ASR` (default replay);
    sarvam falls back to replay on any error."""
    chosen = (provider or os.environ.get("DW_ASR") or "replay").strip().lower()
    if chosen == "sarvam":
        try:
            return _sarvam(call, data_dir), "sarvam"
        except Exception as exc:  # noqa: BLE001 - any ASR failure degrades to the stored transcript
            log.warning("Sarvam ASR fell back to replay for %s: %s", call.get("call_id"), exc)
    elif chosen != "replay":
        log.warning("unknown ASR provider %r; using replay", chosen)
    return _replay(call), "replay"
