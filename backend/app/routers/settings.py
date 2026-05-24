from typing import Annotated, Literal

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.deps import get_db, get_user_id
from app.repositories import users as users_repo
from app.services.tts import TtsUnavailable, synthesize_with_voice

router = APIRouter()

_FREE_VOICE_IDS = {
    "EXAVITQu4vr4xnSDxMaL",  # Bella   (app default)
    "XrExE9yKIg1WjnnlVkGX",  # Matilda
    "pNInz6obpgDQGcFmaJgB",  # Adam
    "ErXwobaYiN019PkySvjV",  # Antoni
}

_AI_PROVIDERS = Literal["auto", "gemini", "ollama"]


class UserSettings(BaseModel):
    ai_provider: str = "auto"
    ollama_model: str | None = None
    elevenlabs_voice_id: str | None = None
    digest_opt_in: bool = True
    nudge_hour: int | None = None
    weekly_apps_goal: int = 5
    wake_word_enabled: bool = True
    auto_brief_enabled: bool = False


class SettingsPatch(BaseModel):
    ai_provider: _AI_PROVIDERS | None = None
    ollama_model: str | None = Field(default=None, max_length=100)
    elevenlabs_voice_id: str | None = None
    digest_opt_in: bool | None = None
    nudge_hour: int | None = Field(default=None, ge=0, le=23)
    weekly_apps_goal: int | None = Field(default=None, ge=1, le=50)
    wake_word_enabled: bool | None = None
    auto_brief_enabled: bool | None = None


@router.get("/", response_model=UserSettings)
async def get_settings(
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> UserSettings:
    row = await users_repo.get_user_settings(conn, user_id)
    if not row:
        return UserSettings()
    return UserSettings(
        ai_provider=row.get("ai_provider") or "auto",
        ollama_model=row.get("ollama_model"),
        elevenlabs_voice_id=row.get("elevenlabs_voice_id"),
        digest_opt_in=bool(row.get("digest_opt_in", True)),
        nudge_hour=row.get("nudge_hour"),
        weekly_apps_goal=int(row.get("weekly_apps_goal") or 5),
        wake_word_enabled=bool(row.get("wake_word_enabled", True)),
        auto_brief_enabled=bool(row.get("auto_brief_enabled", False)),
    )


@router.patch("/", response_model=UserSettings)
async def patch_settings(
    body: SettingsPatch,
    conn: Annotated[asyncpg.Connection, Depends(get_db)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> UserSettings:
    if (
        body.elevenlabs_voice_id is not None
        and body.elevenlabs_voice_id not in _FREE_VOICE_IDS
    ):
        raise HTTPException(
            status_code=422,
            detail="Unknown voice_id. Must be one of the free-tier ElevenLabs voices.",
        )
    row = await users_repo.update_user_settings(
        conn,
        user_id,
        ai_provider=body.ai_provider,
        ollama_model=body.ollama_model,
        elevenlabs_voice_id=body.elevenlabs_voice_id,
        digest_opt_in=body.digest_opt_in,
        nudge_hour=body.nudge_hour,
        weekly_apps_goal=body.weekly_apps_goal,
        wake_word_enabled=body.wake_word_enabled,
        auto_brief_enabled=body.auto_brief_enabled,
    )
    return UserSettings(
        ai_provider=row.get("ai_provider") or "auto",
        ollama_model=row.get("ollama_model"),
        elevenlabs_voice_id=row.get("elevenlabs_voice_id"),
        digest_opt_in=bool(row.get("digest_opt_in", True)),
        nudge_hour=row.get("nudge_hour"),
        weekly_apps_goal=int(row.get("weekly_apps_goal") or 5),
        wake_word_enabled=bool(row.get("wake_word_enabled", True)),
        auto_brief_enabled=bool(row.get("auto_brief_enabled", False)),
    )


_PREVIEW_TEXT = "Hi! This is how I sound. Let me help you land your next role."


@router.get("/voice-preview/{voice_id}")
async def voice_preview(
    voice_id: str,
    user_id: Annotated[int, Depends(get_user_id)],
) -> Response:
    if voice_id not in _FREE_VOICE_IDS:
        raise HTTPException(status_code=422, detail="Unknown voice_id")
    try:
        audio = await synthesize_with_voice(_PREVIEW_TEXT, voice_id)
    except TtsUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return Response(content=audio, media_type="audio/mpeg")
