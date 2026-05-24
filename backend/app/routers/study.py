"""Study tracker (M10) REST endpoints.

Mounted at /api/study. The router is intentionally thin: it converts
Pydantic models → repo calls and emits the audit event + gamify XP for
revise. All authorisation is via the existing ``Depends(get_user_id)``
session check; rows are filtered by user_id in the repo SQL.
"""
from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.deps import get_db, get_user_id
from app.models import (
    StudyGenerateRequest,
    StudyGenerateResponse,
    StudyGenerateTopicsRequest,
    StudyGenerateTopicsResponse,
    StudyPlan,
    StudyProgress,
    StudyReviseResponse,
    StudySectionCreate,
    StudySectionOut,
    StudySectionUpdate,
    StudySubsectionCreate,
    StudySubsectionOut,
    StudySubsectionUpdate,
    StudyTopicCreate,
    StudyTopicOut,
    StudyTopicUpdate,
)
from app.repositories import study as repo
from app.repositories.events import emit
from app.services import gamify
from app.services import study_ai

router = APIRouter()


def _merge(base: gamify.XpResult, extra: gamify.XpResult) -> None:
    """Accumulate extra's XP, achievements, and quests into base in-place."""
    if extra.duplicate:
        return
    base.xp_gained += extra.xp_gained
    base.unlocked.extend(extra.unlocked)
    base.quest_completed.extend(extra.quest_completed)
    base.quests_progressed.extend(extra.quests_progressed)
    if extra.new_level is not None:
        base.new_level = extra.new_level


# ────────────────────────  plan + progress  ─────────────────────────


@router.get("/plan", response_model=StudyPlan)
async def get_plan(
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StudyPlan:
    return await repo.list_plan(conn, user_id)


@router.get("/progress", response_model=StudyProgress)
async def get_progress(
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StudyProgress:
    p = await repo.progress(conn, user_id)
    return StudyProgress(**p)


# ──────────────────────────  sections  ─────────────────────────────


@router.get("/sections", response_model=list[StudySectionOut])
async def list_sections(
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[StudySectionOut]:
    return await repo.list_sections(conn, user_id)


@router.post(
    "/sections",
    response_model=StudySectionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_section(
    data: StudySectionCreate,
    response: Response,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StudySectionOut:
    async with conn.transaction():
        sec = await repo.create_section(conn, user_id, data)
        await emit(conn, user_id, "study.section_added", {
            "section_id": sec.id, "name": sec.name,
        })
        # XP event is opt-in; the gamify registry can wire the achievement
        # ("syllabus_set") to this event in a later phase. Calling it here
        # so it lands today rather than as a follow-up.
        gam = await gamify.record_event(
            conn, user_id, "study.section_added",
            ref_type="study_section", ref_id=sec.id,
        )
    gamify.attach(response, gam)
    return sec


@router.patch("/sections/{section_id}", response_model=StudySectionOut)
async def update_section(
    section_id: int,
    patch: StudySectionUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StudySectionOut:
    return await repo.update_section(conn, section_id, user_id, patch)


@router.delete(
    "/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_section(
    section_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    await repo.soft_delete_section(conn, section_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ────────────────────────  subsections  ───────────────────────────


@router.post(
    "/sections/{section_id}/subsections",
    response_model=StudySubsectionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_subsection(
    section_id: int,
    data: StudySubsectionCreate,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StudySubsectionOut:
    return await repo.create_subsection(conn, section_id, user_id, data)


@router.patch(
    "/subsections/{subsection_id}", response_model=StudySubsectionOut,
)
async def update_subsection(
    subsection_id: int,
    patch: StudySubsectionUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StudySubsectionOut:
    return await repo.update_subsection(conn, subsection_id, user_id, patch)


@router.delete(
    "/subsections/{subsection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_subsection(
    subsection_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    await repo.soft_delete_subsection(conn, subsection_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ──────────────────────────  topics  ──────────────────────────────


@router.post(
    "/subsections/{subsection_id}/topics",
    response_model=StudyTopicOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_topic(
    subsection_id: int,
    data: StudyTopicCreate,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StudyTopicOut:
    return await repo.create_topic(conn, subsection_id, user_id, data)


@router.patch("/topics/{topic_id}", response_model=StudyTopicOut)
async def update_topic(
    topic_id: int,
    patch: StudyTopicUpdate,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StudyTopicOut:
    return await repo.update_topic(conn, topic_id, user_id, patch)


@router.delete(
    "/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_topic(
    topic_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> Response:
    await repo.soft_delete_topic(conn, topic_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/topics/{topic_id}/revise", response_model=StudyReviseResponse)
async def revise_topic(
    topic_id: int,
    response: Response,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StudyReviseResponse:
    async with conn.transaction():
        topic = await repo.revise_topic(conn, topic_id, user_id)
        await emit(conn, user_id, "study.topic_revised", {
            "topic_id": topic.id,
            "revision_count": topic.revision_count,
            "status": topic.status,
        })
        # First revision earns the bigger reward; subsequent revisions
        # award less to discourage farming. ref_id encodes (topic, count)
        # so each revision is idempotently distinct.
        event_key = (
            "study.topic_revised_first"
            if topic.revision_count == 1
            else "study.topic_revised_again"
        )
        ref_id = topic.id * 1000 + min(topic.revision_count, 999)
        gam = await gamify.record_event(
            conn, user_id, event_key,
            ref_type="study_topic", ref_id=ref_id,
        )
        if topic.status == "mastered":
            mastered = await gamify.record_event(
                conn, user_id, "study.topic_mastered",
                ref_type="study_topic", ref_id=topic.id,
            )
            _merge(gam, mastered)

        # Completion cascade: subsection → section.
        # Accumulate XP + achievements from all cascade events so the
        # frontend envelope sees everything that fired this request.
        subsection = await repo.get_subsection(conn, topic.subsection_id, user_id)
        if await repo.is_subsection_complete(conn, topic.subsection_id, user_id):
            sub_gam = await gamify.record_event(
                conn, user_id, "study.subsection_completed",
                ref_type="study_subsection", ref_id=topic.subsection_id,
            )
            _merge(gam, sub_gam)
            if await repo.is_section_complete(conn, subsection.section_id, user_id):
                sec_gam = await gamify.record_event(
                    conn, user_id, "study.section_completed",
                    ref_type="study_section", ref_id=subsection.section_id,
                )
                _merge(gam, sec_gam)
    gamify.attach(response, gam)
    return StudyReviseResponse(
        topic=topic,
        revision_count=topic.revision_count,
        new_status=topic.status,
    )


@router.post("/topics/{topic_id}/unmark", response_model=StudyTopicOut)
async def unmark_topic(
    topic_id: int,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StudyTopicOut:
    return await repo.unmark_topic(conn, topic_id, user_id)


# ── AI generation (Phase 4) ──────────────────────────────────────────


@router.post("/generate", response_model=StudyGenerateResponse)
async def generate_plan(
    data: StudyGenerateRequest,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StudyGenerateResponse:
    try:
        return await study_ai.generate_plan(
            data.role,
            data.target_companies,
            data.existing_sections,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/generate/apply", response_model=StudyPlan)
async def apply_generated_plan(
    data: StudyGenerateResponse,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StudyPlan:
    """Persist a generated plan preview. Returns the saved tree with real ids."""
    async with conn.transaction():
        for sec_data in data.sections:
            sec = await repo.create_section(
                conn, user_id, StudySectionCreate(name=sec_data.name)
            )
            for sub_data in sec_data.subsections:
                sub = await repo.create_subsection(
                    conn, sec.id, user_id, StudySubsectionCreate(name=sub_data.name)
                )
                for topic_data in sub_data.topics:
                    await repo.create_topic(
                        conn, sub.id, user_id,
                        StudyTopicCreate(
                            title=topic_data.title,
                            notes=topic_data.notes,
                        ),
                    )
    return await repo.list_plan(conn, user_id)


@router.post(
    "/subsections/{subsection_id}/generate-topics",
    response_model=StudyGenerateTopicsResponse,
)
async def generate_topics(
    subsection_id: int,
    data: StudyGenerateTopicsRequest,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> StudyGenerateTopicsResponse:
    subsection = await repo.get_subsection(conn, subsection_id, user_id)
    section = await repo.get_section(conn, subsection.section_id, user_id)
    try:
        return await study_ai.generate_topics(
            section.name,
            subsection.name,
            data.count,
            data.hint,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post(
    "/subsections/{subsection_id}/generate-topics/apply",
    response_model=list[StudyTopicOut],
    status_code=status.HTTP_201_CREATED,
)
async def apply_generated_topics(
    subsection_id: int,
    data: StudyGenerateTopicsResponse,
    conn: asyncpg.Connection = Depends(get_db),
    user_id: int = Depends(get_user_id),
) -> list[StudyTopicOut]:
    """Persist a topic preview. Returns the saved topics with real ids."""
    saved: list[StudyTopicOut] = []
    async with conn.transaction():
        for topic_data in data.topics:
            topic = await repo.create_topic(
                conn, subsection_id, user_id,
                StudyTopicCreate(
                    title=topic_data.title,
                    notes=topic_data.notes,
                ),
            )
            saved.append(topic)
    return saved
