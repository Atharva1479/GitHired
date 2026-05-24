"""ElevenLabs TTS client. Returns mp3 audio bytes."""
from __future__ import annotations

import httpx
import structlog

from app.config import settings

log = structlog.get_logger("tts")


class TtsUnavailable(Exception):
    """Raised when TTS is unconfigured, quota'd, or fails."""


async def synthesize(text: str) -> bytes:
    """Synthesize `text` to mp3 audio bytes."""
    key = settings.elevenlabs_api_key.get_secret_value()
    if not key:
        raise TtsUnavailable("ELEVENLABS_API_KEY not configured")
    text = (text or "").strip()
    if not text:
        raise TtsUnavailable("empty text")

    url = (
        f"https://api.elevenlabs.io/v1/text-to-speech/"
        f"{settings.elevenlabs_voice_id}"
    )
    headers = {
        "xi-api-key": key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "model_id": settings.elevenlabs_model,
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.75,
            "style": 0.2,
            "use_speaker_boost": True,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, headers=headers, json=body)
    except httpx.HTTPError as e:
        log.warning("tts.network_error", error=str(e))
        raise TtsUnavailable(str(e)) from e

    if r.status_code == 401:
        raise TtsUnavailable("invalid api key")
    if r.status_code == 402:
        # The free ElevenLabs plan blocks library / cloned voices via
        # the API — only the 9 built-in voices work. The configured
        # voice id is from the library; either pick a built-in (Bella,
        # Rachel, Domi, Elli, etc.) or upgrade the plan.
        log.warning(
            "tts.paid_plan_required",
            voice_id=settings.elevenlabs_voice_id,
            hint=(
                "ELEVENLABS_VOICE_ID points to a library voice — free "
                "tier API only supports built-in voices. Swap to one of "
                "ElevenLabs' built-in voice ids or upgrade the plan."
            ),
        )
        raise TtsUnavailable(
            "elevenlabs free tier doesn't support library voices; "
            f"voice_id={settings.elevenlabs_voice_id} is library-only"
        )
    if r.status_code == 429:
        log.warning("tts.rate_limited")
        raise TtsUnavailable("rate limited / quota exhausted")
    if r.status_code >= 400:
        log.warning("tts.http_error", status=r.status_code, body=r.text[:200])
        raise TtsUnavailable(f"http {r.status_code}")

    return r.content


async def synthesize_with_voice(text: str, voice_id: str) -> bytes:
    """Like synthesize() but uses the given voice_id instead of the global setting."""
    key = settings.elevenlabs_api_key.get_secret_value()
    if not key:
        raise TtsUnavailable("ELEVENLABS_API_KEY not configured")
    text = (text or "").strip()
    if not text:
        raise TtsUnavailable("empty text")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "model_id": settings.elevenlabs_model,
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.75,
            "style": 0.2,
            "use_speaker_boost": True,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, headers=headers, json=body)
    except httpx.HTTPError as e:
        log.warning("tts.network_error", error=str(e))
        raise TtsUnavailable(str(e)) from e

    if r.status_code == 401:
        raise TtsUnavailable("invalid api key")
    if r.status_code == 402:
        raise TtsUnavailable(
            f"elevenlabs free tier doesn't support this voice; voice_id={voice_id}"
        )
    if r.status_code == 429:
        raise TtsUnavailable("rate limited / quota exhausted")
    if r.status_code >= 400:
        raise TtsUnavailable(f"http {r.status_code}")
    return r.content
