"""Study tracker (M10) — sections, subsections, topics, revise().

Three levels, all soft-delete aware, all rows scoped by user_id. The
``list_plan`` helper assembles the full nested tree in three SELECTs
(one per level) and stitches in Python — keeps the SQL boring and the
shape obvious.

Revising a topic is a single transactional UPDATE that bumps
``revision_count``, sets ``last_revised_at = NOW()``, and may promote
``status`` to ``'mastered'``. The gamify XP event is dispatched by the
router layer (so this module stays repository-only and easy to test).
"""
from __future__ import annotations

import datetime as dt

import asyncpg

from app.exceptions import NotFound
from app.models import (
    StudyPlan,
    StudyPlanSection,
    StudyPlanSubsection,
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

# Auto-mastery thresholds (see M10_PLAN §4.4).
MASTERY_REVISION_THRESHOLD = 3
MASTERY_AGE_DAYS = 7
# A topic with status in ('done','mastered') is "stale" after this many days.
STALE_AFTER_DAYS = 14


_SECTION_COLS = "id, name, icon, position, created_at, last_updated"
_SUBSECTION_COLS = (
    "id, section_id, name, position, created_at, last_updated"
)
_TOPIC_COLS = (
    "id, subsection_id, title, notes, kind, status, tags, "
    "revision_count, last_revised_at, position, created_at, last_updated"
)


# ─────────────────────────  sections  ────────────────────────────────


async def list_sections(
    conn: asyncpg.Connection, user_id: int
) -> list[StudySectionOut]:
    rows = await conn.fetch(
        f"SELECT {_SECTION_COLS} FROM study_sections "
        "WHERE user_id = $1 AND deleted_at IS NULL "
        "ORDER BY position ASC, id ASC",
        user_id,
    )
    return [StudySectionOut.model_validate(dict(r)) for r in rows]


async def get_section(
    conn: asyncpg.Connection, section_id: int, user_id: int
) -> StudySectionOut:
    row = await conn.fetchrow(
        f"SELECT {_SECTION_COLS} FROM study_sections "
        "WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        section_id, user_id,
    )
    if not row:
        raise NotFound(f"section id={section_id}")
    return StudySectionOut.model_validate(dict(row))


async def create_section(
    conn: asyncpg.Connection, user_id: int, data: StudySectionCreate
) -> StudySectionOut:
    position = data.position
    if position is None:
        # Append: one more than the current max.
        position = await conn.fetchval(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM study_sections "
            "WHERE user_id = $1 AND deleted_at IS NULL",
            user_id,
        )
    row = await conn.fetchrow(
        f"""
        INSERT INTO study_sections (user_id, name, icon, position)
        VALUES ($1, $2, $3, $4)
        RETURNING {_SECTION_COLS}
        """,
        user_id, data.name, data.icon, position,
    )
    return StudySectionOut.model_validate(dict(row))


async def update_section(
    conn: asyncpg.Connection,
    section_id: int,
    user_id: int,
    patch: StudySectionUpdate,
) -> StudySectionOut:
    fields = patch.model_dump(exclude_unset=True)
    if not fields:
        return await get_section(conn, section_id, user_id)
    sets = [f"{k} = ${i + 1}" for i, k in enumerate(fields)]
    args = list(fields.values())
    sets.append("last_updated = NOW()")
    args.extend([section_id, user_id])
    row = await conn.fetchrow(
        f"UPDATE study_sections SET {', '.join(sets)} "
        f"WHERE id = ${len(args) - 1} AND user_id = ${len(args)} "
        f"AND deleted_at IS NULL RETURNING {_SECTION_COLS}",
        *args,
    )
    if not row:
        raise NotFound(f"section id={section_id}")
    return StudySectionOut.model_validate(dict(row))


async def soft_delete_section(
    conn: asyncpg.Connection, section_id: int, user_id: int
) -> None:
    """Soft-delete a section AND cascade to its subsections + topics.

    Cascading is explicit (not relying on FK behaviour) because we use
    soft delete: setting ``deleted_at`` on the section doesn't touch
    its children automatically. We do all three updates in one round
    trip for atomicity.
    """
    result = await conn.execute(
        """
        WITH cascaded_subsections AS (
            UPDATE study_subsections
            SET deleted_at = NOW()
            WHERE section_id = $1 AND user_id = $2 AND deleted_at IS NULL
            RETURNING id
        ),
        cascaded_topics AS (
            UPDATE study_topics
            SET deleted_at = NOW()
            WHERE subsection_id IN (SELECT id FROM cascaded_subsections)
              AND deleted_at IS NULL
            RETURNING id
        )
        UPDATE study_sections
        SET deleted_at = NOW()
        WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
        """,
        section_id, user_id,
    )
    if result.endswith(" 0"):
        raise NotFound(f"section id={section_id}")


# ─────────────────────────  subsections  ────────────────────────────


async def get_subsection(
    conn: asyncpg.Connection, subsection_id: int, user_id: int
) -> StudySubsectionOut:
    row = await conn.fetchrow(
        f"SELECT {_SUBSECTION_COLS} FROM study_subsections "
        "WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        subsection_id, user_id,
    )
    if not row:
        raise NotFound(f"subsection id={subsection_id}")
    return StudySubsectionOut.model_validate(dict(row))


async def create_subsection(
    conn: asyncpg.Connection,
    section_id: int,
    user_id: int,
    data: StudySubsectionCreate,
) -> StudySubsectionOut:
    # Verify the parent section belongs to the user; raises NotFound otherwise.
    await get_section(conn, section_id, user_id)
    position = data.position
    if position is None:
        position = await conn.fetchval(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM study_subsections "
            "WHERE section_id = $1 AND deleted_at IS NULL",
            section_id,
        )
    row = await conn.fetchrow(
        f"""
        INSERT INTO study_subsections (section_id, user_id, name, position)
        VALUES ($1, $2, $3, $4)
        RETURNING {_SUBSECTION_COLS}
        """,
        section_id, user_id, data.name, position,
    )
    return StudySubsectionOut.model_validate(dict(row))


async def update_subsection(
    conn: asyncpg.Connection,
    subsection_id: int,
    user_id: int,
    patch: StudySubsectionUpdate,
) -> StudySubsectionOut:
    fields = patch.model_dump(exclude_unset=True)
    if not fields:
        return await get_subsection(conn, subsection_id, user_id)
    # If moving to a different section, verify that section is the user's too.
    new_section_id = fields.get("section_id")
    if new_section_id is not None:
        await get_section(conn, new_section_id, user_id)
    sets = [f"{k} = ${i + 1}" for i, k in enumerate(fields)]
    args = list(fields.values())
    sets.append("last_updated = NOW()")
    args.extend([subsection_id, user_id])
    row = await conn.fetchrow(
        f"UPDATE study_subsections SET {', '.join(sets)} "
        f"WHERE id = ${len(args) - 1} AND user_id = ${len(args)} "
        f"AND deleted_at IS NULL RETURNING {_SUBSECTION_COLS}",
        *args,
    )
    if not row:
        raise NotFound(f"subsection id={subsection_id}")
    return StudySubsectionOut.model_validate(dict(row))


async def soft_delete_subsection(
    conn: asyncpg.Connection, subsection_id: int, user_id: int
) -> None:
    result = await conn.execute(
        """
        WITH cascaded_topics AS (
            UPDATE study_topics
            SET deleted_at = NOW()
            WHERE subsection_id = $1 AND user_id = $2 AND deleted_at IS NULL
            RETURNING id
        )
        UPDATE study_subsections
        SET deleted_at = NOW()
        WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
        """,
        subsection_id, user_id,
    )
    if result.endswith(" 0"):
        raise NotFound(f"subsection id={subsection_id}")


# ──────────────────────────  topics  ────────────────────────────────


async def get_topic(
    conn: asyncpg.Connection, topic_id: int, user_id: int
) -> StudyTopicOut:
    row = await conn.fetchrow(
        f"SELECT {_TOPIC_COLS} FROM study_topics "
        "WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        topic_id, user_id,
    )
    if not row:
        raise NotFound(f"topic id={topic_id}")
    return _topic_from_row(row)


async def create_topic(
    conn: asyncpg.Connection,
    subsection_id: int,
    user_id: int,
    data: StudyTopicCreate,
) -> StudyTopicOut:
    await get_subsection(conn, subsection_id, user_id)
    position = data.position
    if position is None:
        position = await conn.fetchval(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM study_topics "
            "WHERE subsection_id = $1 AND deleted_at IS NULL",
            subsection_id,
        )
    row = await conn.fetchrow(
        f"""
        INSERT INTO study_topics
            (subsection_id, user_id, title, notes, kind, tags, position)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING {_TOPIC_COLS}
        """,
        subsection_id, user_id, data.title, data.notes, data.kind,
        data.tags, position,
    )
    return _topic_from_row(row)


async def update_topic(
    conn: asyncpg.Connection,
    topic_id: int,
    user_id: int,
    patch: StudyTopicUpdate,
) -> StudyTopicOut:
    fields = patch.model_dump(exclude_unset=True)
    if not fields:
        return await get_topic(conn, topic_id, user_id)
    new_sub = fields.get("subsection_id")
    if new_sub is not None:
        await get_subsection(conn, new_sub, user_id)
    sets = [f"{k} = ${i + 1}" for i, k in enumerate(fields)]
    args = list(fields.values())
    sets.append("last_updated = NOW()")
    args.extend([topic_id, user_id])
    row = await conn.fetchrow(
        f"UPDATE study_topics SET {', '.join(sets)} "
        f"WHERE id = ${len(args) - 1} AND user_id = ${len(args)} "
        f"AND deleted_at IS NULL RETURNING {_TOPIC_COLS}",
        *args,
    )
    if not row:
        raise NotFound(f"topic id={topic_id}")
    return _topic_from_row(row)


async def soft_delete_topic(
    conn: asyncpg.Connection, topic_id: int, user_id: int
) -> None:
    result = await conn.execute(
        "UPDATE study_topics SET deleted_at = NOW() "
        "WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL",
        topic_id, user_id,
    )
    if result.endswith(" 0"):
        raise NotFound(f"topic id={topic_id}")


async def revise_topic(
    conn: asyncpg.Connection, topic_id: int, user_id: int
) -> StudyTopicOut:
    """Mark a topic as revised: status='done', counter++, ts=NOW().

    Auto-promotes to ``'mastered'`` once revision_count >=
    MASTERY_REVISION_THRESHOLD AND the topic is at least
    MASTERY_AGE_DAYS old. The router layer is responsible for
    dispatching the gamify XP event after this returns.
    """
    row = await conn.fetchrow(
        f"""
        UPDATE study_topics
        SET
          status = CASE
            WHEN revision_count + 1 >= $3
                 AND created_at <= NOW() - ($4::int * INTERVAL '1 day')
            THEN 'mastered'
            ELSE 'done'
          END,
          revision_count = revision_count + 1,
          last_revised_at = NOW(),
          last_updated = NOW()
        WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
        RETURNING {_TOPIC_COLS}
        """,
        topic_id, user_id, MASTERY_REVISION_THRESHOLD, MASTERY_AGE_DAYS,
    )
    if not row:
        raise NotFound(f"topic id={topic_id}")
    return _topic_from_row(row)


async def unmark_topic(
    conn: asyncpg.Connection, topic_id: int, user_id: int
) -> StudyTopicOut:
    """Reset status to 'todo'. Revision counter and history preserved."""
    row = await conn.fetchrow(
        f"""
        UPDATE study_topics
        SET status = 'todo', last_updated = NOW()
        WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
        RETURNING {_TOPIC_COLS}
        """,
        topic_id, user_id,
    )
    if not row:
        raise NotFound(f"topic id={topic_id}")
    return _topic_from_row(row)


# ──────────────────────  completion checks  ─────────────────────────


async def is_subsection_complete(
    conn: asyncpg.Connection, subsection_id: int, user_id: int
) -> bool:
    """True if every non-deleted topic in the subsection is done/mastered.

    Empty subsections (no topics) never count as complete so we don't
    fire spurious gamify events on freshly-created subsections.
    """
    row = await conn.fetchrow(
        """
        SELECT
            COUNT(*)                                              AS total,
            COUNT(*) FILTER (WHERE status IN ('done','mastered')) AS finished
        FROM study_topics
        WHERE subsection_id = $1 AND user_id = $2 AND deleted_at IS NULL
        """,
        subsection_id, user_id,
    )
    if not row or row["total"] == 0:
        return False
    return row["total"] == row["finished"]


async def is_section_complete(
    conn: asyncpg.Connection, section_id: int, user_id: int
) -> bool:
    """True if every non-deleted subsection in the section is complete.

    A subsection is complete when it has ≥1 topic and all are done/mastered.
    A section with no subsections is never complete.
    """
    row = await conn.fetchrow(
        """
        SELECT
            COUNT(DISTINCT ss.id) AS total_subs,
            COUNT(DISTINCT ss.id) FILTER (
                WHERE (
                    SELECT COUNT(*) FROM study_topics t
                    WHERE t.subsection_id = ss.id AND t.deleted_at IS NULL
                ) > 0
                AND NOT EXISTS (
                    SELECT 1 FROM study_topics t
                    WHERE t.subsection_id = ss.id AND t.deleted_at IS NULL
                      AND t.status NOT IN ('done','mastered')
                )
            ) AS completed_subs
        FROM study_subsections ss
        WHERE ss.section_id = $1 AND ss.user_id = $2 AND ss.deleted_at IS NULL
        """,
        section_id, user_id,
    )
    if not row or row["total_subs"] == 0:
        return False
    return row["total_subs"] == row["completed_subs"]


# ──────────────────────────  tree + stats  ──────────────────────────


async def list_plan(
    conn: asyncpg.Connection, user_id: int
) -> StudyPlan:
    """Return the full sections → subsections → topics tree.

    Three batched SELECTs, stitched in Python. We pull every row at every
    level filtered by ``user_id`` and group in a single pass — no N+1.
    """
    sec_rows = await conn.fetch(
        f"SELECT {_SECTION_COLS} FROM study_sections "
        "WHERE user_id = $1 AND deleted_at IS NULL "
        "ORDER BY position ASC, id ASC",
        user_id,
    )
    sub_rows = await conn.fetch(
        f"SELECT {_SUBSECTION_COLS} FROM study_subsections "
        "WHERE user_id = $1 AND deleted_at IS NULL "
        "ORDER BY position ASC, id ASC",
        user_id,
    )
    topic_rows = await conn.fetch(
        f"SELECT {_TOPIC_COLS} FROM study_topics "
        "WHERE user_id = $1 AND deleted_at IS NULL "
        "ORDER BY position ASC, id ASC",
        user_id,
    )

    # Group topics by subsection_id.
    topics_by_sub: dict[int, list[StudyTopicOut]] = {}
    for r in topic_rows:
        topics_by_sub.setdefault(int(r["subsection_id"]), []).append(
            _topic_from_row(r)
        )

    # Group subsections by section_id, attaching topics.
    subs_by_sec: dict[int, list[StudyPlanSubsection]] = {}
    for r in sub_rows:
        sub = StudyPlanSubsection.model_validate({
            **dict(r),
            "topics": topics_by_sub.get(int(r["id"]), []),
        })
        subs_by_sec.setdefault(int(r["section_id"]), []).append(sub)

    sections: list[StudyPlanSection] = []
    for r in sec_rows:
        sections.append(
            StudyPlanSection.model_validate({
                **dict(r),
                "subsections": subs_by_sec.get(int(r["id"]), []),
            })
        )
    return StudyPlan(sections=sections)


async def progress(
    conn: asyncpg.Connection, user_id: int
) -> dict[str, int]:
    """Aggregate counters used by the dashboard + voice's get_progress."""
    row = await conn.fetchrow(
        """
        SELECT
          COUNT(*)                                              AS total_topics,
          COUNT(*) FILTER (WHERE status = 'todo')               AS todo,
          COUNT(*) FILTER (WHERE status = 'in_progress')        AS in_progress,
          COUNT(*) FILTER (WHERE status = 'done')               AS done,
          COUNT(*) FILTER (WHERE status = 'mastered')           AS mastered,
          COUNT(*) FILTER (
              WHERE last_revised_at >= NOW() - INTERVAL '7 days'
          ) AS revisions_this_week,
          COUNT(*) FILTER (
              WHERE status IN ('done','mastered')
                AND (last_revised_at IS NULL
                     OR last_revised_at < NOW() - ($2::int * INTERVAL '1 day'))
          ) AS due_for_review
        FROM study_topics
        WHERE user_id = $1 AND deleted_at IS NULL
        """,
        user_id, STALE_AFTER_DAYS,
    )
    if not row:
        return {
            "total_topics": 0, "todo": 0, "in_progress": 0, "done": 0,
            "mastered": 0, "revisions_this_week": 0, "due_for_review": 0,
        }
    return {k: int(row[k]) for k in row.keys()}


# ──────────────────────────  helpers  ───────────────────────────────


def _topic_from_row(row: asyncpg.Record) -> StudyTopicOut:
    """asyncpg returns ``tags`` as a list already; normalise None → []."""
    d = dict(row)
    if d.get("tags") is None:
        d["tags"] = []
    return StudyTopicOut.model_validate(d)


__all__ = [
    "list_plan",
    "list_sections",
    "get_section",
    "create_section",
    "update_section",
    "soft_delete_section",
    "get_subsection",
    "create_subsection",
    "update_subsection",
    "soft_delete_subsection",
    "get_topic",
    "create_topic",
    "update_topic",
    "soft_delete_topic",
    "revise_topic",
    "unmark_topic",
    "is_subsection_complete",
    "is_section_complete",
    "progress",
    "MASTERY_REVISION_THRESHOLD",
    "MASTERY_AGE_DAYS",
    "STALE_AFTER_DAYS",
]


# Datetime import is used in the docstring's reference to NOW(); explicit
# import keeps linters honest in case future helpers want timezone-aware
# clocks for tests.
_ = dt
