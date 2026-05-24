"""Groq Whisper-large-v3 transcription client."""
from __future__ import annotations

import httpx
import structlog

from app.config import settings

log = structlog.get_logger("stt")

_GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


class SttUnavailable(Exception):
    """Raised when the STT provider is unconfigured or returns an error."""


async def transcribe(audio: bytes, *, filename: str = "speech.webm") -> str:
    """Send audio bytes to Groq Whisper and return the transcript text."""
    key = settings.groq_api_key.get_secret_value()
    if not key:
        raise SttUnavailable("GROQ_API_KEY not configured")

    files = {"file": (filename, audio, _guess_mime(filename))}
    data = {
        "model": settings.groq_stt_model,
        "response_format": "json",
        "temperature": "0",
    }
    headers = {"Authorization": f"Bearer {key}"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                _GROQ_TRANSCRIBE_URL, headers=headers, data=data, files=files,
            )
    except httpx.HTTPError as e:
        log.warning("stt.network_error", error=str(e))
        raise SttUnavailable(str(e)) from e

    if r.status_code == 429:
        log.warning("stt.rate_limited")
        raise SttUnavailable("rate limited")
    if r.status_code >= 400:
        log.warning("stt.http_error", status=r.status_code, body=r.text[:200])
        raise SttUnavailable(f"http {r.status_code}")

    payload = r.json()
    text = (payload.get("text") or "").strip()
    if not text:
        raise SttUnavailable("empty transcript")
    return text


def _guess_mime(filename: str) -> str:
    n = filename.lower()
    if n.endswith(".webm"):
        return "audio/webm"
    if n.endswith(".ogg"):
        return "audio/ogg"
    if n.endswith(".mp3"):
        return "audio/mpeg"
    if n.endswith(".m4a"):
        return "audio/mp4"
    if n.endswith(".wav"):
        return "audio/wav"
    return "application/octet-stream"
