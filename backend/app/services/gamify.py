"""Gamification engine: XP, levels, streaks, quests, achievements.

All operations are idempotent at the event_key+ref granularity (see xp_events
unique index). Callers must invoke record_event() inside an open transaction.
"""
from __future__ import annotations

import bisect
import datetime as dt
import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable

import asyncpg
import structlog
from starlette.responses import Response

from app.services import metrics

log = structlog.get_logger("gamify")

# ---------------------------------------------------------------------------
# Reward & level configuration
# ---------------------------------------------------------------------------

STATUS_EVENT_KEY: dict[str, str] = {
    "Applied": "status.applied",
    "Screening": "status.phone_screen",
    "Interview": "status.onsite",
    "Offer": "status.offer",
    "Rejected": "status.rejected",
    # "Ghosted" intentionally awards no XP
}


XP_REWARDS: dict[str, int] = {
    "app.added": 10,
    "status.applied": 20,
    "status.phone_screen": 50,
    "status.onsite": 100,
    "status.offer": 500,
    "status.rejected": 5,
    "draft.sent": 15,
    "referral.added": 25,
    "daily.login": 5,
    "comeback": 30,
    # M10 — study tracker. First-time revision earns the full 5; repeats
    # earn 2 (diminishing returns discourage farming). Mastery is the
    # bigger reward because it requires repeated effort over ≥7 days.
    "study.section_added": 0,         # tracked for achievement, no XP itself
    "study.topic_revised_first": 5,
    "study.topic_revised_again": 2,
    "study.topic_mastered": 15,
    "study.subsection_completed": 25,
    "study.section_completed": 100,
    # DSA problem tracker
    "dsa.problem_logged": 25,
    "dsa.problem_analyzed": 15,
}

MAX_LEVEL = 50
_LEVEL_BASE = 100
_LEVEL_GROWTH = 1.6


def _build_thresholds() -> list[int]:
    out = [0]
    cum = 0
    for i in range(1, MAX_LEVEL):
        cum += round(_LEVEL_BASE * (_LEVEL_GROWTH ** (i - 1)))
        out.append(cum)
    return out


LEVEL_THRESHOLDS: list[int] = _build_thresholds()


def level_for_xp(xp: int) -> int:
    return min(MAX_LEVEL, bisect.bisect_right(LEVEL_THRESHOLDS, xp))


def xp_to_next_level(xp: int) -> tuple[int, int]:
    """Returns (xp_into_current_level, xp_span_of_current_level)."""
    lvl = level_for_xp(xp)
    if lvl >= MAX_LEVEL:
        return 0, 0
    base = LEVEL_THRESHOLDS[lvl - 1]
    nxt = LEVEL_THRESHOLDS[lvl]
    return xp - base, nxt - base


# ---------------------------------------------------------------------------
# Quest registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuestSpec:
    code: str
    period: str          # "daily" | "weekly"
    title: str
    target: int
    reward_xp: int
    matches: Callable[[str], bool]


_PIPELINE_KEYS = {"status.phone_screen", "status.onsite", "status.offer"}


QUESTS: dict[str, QuestSpec] = {
    q.code: q
    for q in (
        # ── Daily — application volume ────────────────────────────────
        QuestSpec(
            "daily_apply_1", "daily", "Apply to 1 job today", 1, 30,
            lambda k: k == "app.added",
        ),
        QuestSpec(
            "daily_apply_3", "daily", "Apply to 3 jobs today", 3, 100,
            lambda k: k == "app.added",
        ),
        QuestSpec(
            "daily_apply_5", "daily", "Apply to 5 jobs today", 5, 180,
            lambda k: k == "app.added",
        ),
        # ── Daily — pipeline hygiene ──────────────────────────────────
        QuestSpec(
            "daily_status_3", "daily", "Update the status of 3 applications", 3, 40,
            lambda k: k.startswith("status."),
        ),
        QuestSpec(
            "daily_status_5", "daily", "Update the status of 5 applications", 5, 70,
            lambda k: k.startswith("status."),
        ),
        QuestSpec(
            "daily_pipeline_1", "daily",
            "Move 1 application to Screening or later", 1, 120,
            lambda k: k in _PIPELINE_KEYS,
        ),
        # ── Daily — network ───────────────────────────────────────────
        QuestSpec(
            "daily_referral_1", "daily", "Add 1 referral contact", 1, 30,
            lambda k: k == "referral.added",
        ),
        QuestSpec(
            "daily_referral_2", "daily", "Add 2 referral contacts", 2, 70,
            lambda k: k == "referral.added",
        ),
        # ── Daily — outreach ──────────────────────────────────────────
        QuestSpec(
            "daily_followup_1", "daily", "Draft 1 follow-up message", 1, 40,
            lambda k: k == "draft.sent",
        ),
        QuestSpec(
            "daily_followup_2", "daily", "Draft 2 follow-up messages", 2, 90,
            lambda k: k == "draft.sent",
        ),
        # ── Daily — study revision ────────────────────────────────────
        QuestSpec(
            "daily_revise_3", "daily", "Revise 3 topics today", 3, 30,
            lambda k: k in (
                "study.topic_revised_first", "study.topic_revised_again"
            ),
        ),
        QuestSpec(
            "daily_revise_5", "daily", "Revise 5 topics today", 5, 60,
            lambda k: k in (
                "study.topic_revised_first", "study.topic_revised_again"
            ),
        ),

        # ── Weekly — volume tiers ─────────────────────────────────────
        QuestSpec(
            "weekly_apply_10", "weekly", "Apply to 10 jobs this week", 10, 180,
            lambda k: k == "app.added",
        ),
        QuestSpec(
            "weekly_apply_15", "weekly", "Apply to 15 jobs this week", 15, 280,
            lambda k: k == "app.added",
        ),
        QuestSpec(
            "weekly_apply_25", "weekly", "Apply to 25 jobs this week", 25, 500,
            lambda k: k == "app.added",
        ),
        # ── Weekly — pipeline + outcomes ─────────────────────────────
        QuestSpec(
            "weekly_pipeline_3", "weekly",
            "Move 3 applications to Screening or later", 3, 250,
            lambda k: k in _PIPELINE_KEYS,
        ),
        QuestSpec(
            "weekly_offer_1", "weekly", "Land 1 offer this week", 1, 750,
            lambda k: k == "status.offer",
        ),
        # ── Weekly — network + outreach ──────────────────────────────
        QuestSpec(
            "weekly_referrals_5", "weekly",
            "Add 5 referral contacts this week", 5, 220,
            lambda k: k == "referral.added",
        ),
        QuestSpec(
            "weekly_followups_7", "weekly",
            "Draft 7 follow-up messages this week", 7, 200,
            lambda k: k == "draft.sent",
        ),
        # ── Weekly — study revision + mastery ────────────────────────
        QuestSpec(
            "weekly_revise_15", "weekly", "Revise 15 topics this week", 15, 250,
            lambda k: k in (
                "study.topic_revised_first", "study.topic_revised_again"
            ),
        ),
        QuestSpec(
            "weekly_master_subsection", "weekly", "Complete a subsection", 1, 200,
            lambda k: k == "study.subsection_completed",
        ),
    )
}

DAILY_POOL: list[str] = [
    "daily_apply_1",
    "daily_apply_3",
    "daily_apply_5",
    "daily_status_3",
    "daily_status_5",
    "daily_pipeline_1",
    "daily_referral_1",
    "daily_referral_2",
    "daily_followup_1",
    "daily_followup_2",
    "daily_revise_3",
    "daily_revise_5",
]
WEEKLY_POOL: list[str] = [
    "weekly_apply_10",
    "weekly_apply_15",
    "weekly_apply_25",
    "weekly_pipeline_3",
    "weekly_offer_1",
    "weekly_referrals_5",
    "weekly_followups_7",
    "weekly_revise_15",
    "weekly_master_subsection",
]


# ---------------------------------------------------------------------------
# Achievement registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AchievementSpec:
    code: str
    title: str
    triggers: tuple[str, ...]
    check_sql: str  # parameterized SQL returning a single boolean column


_XP_EVENT_NOT_DELETED = "AND deleted_at IS NULL"
_UP_NOT_DELETED = "AND deleted_at IS NULL"


ACHIEVEMENTS: list[AchievementSpec] = [
    # ── Applications ──────────────────────────────────────────────────
    AchievementSpec(
        "first_application", "First Application", ("app.added",),
        "SELECT COUNT(*) = 1 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'app.added' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "apps_10", "10 Applications Sent", ("app.added",),
        "SELECT COUNT(*) >= 10 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'app.added' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "apps_50", "Half Century (50)", ("app.added",),
        "SELECT COUNT(*) >= 50 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'app.added' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "apps_100", "Centurion (100)", ("app.added",),
        "SELECT COUNT(*) >= 100 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'app.added' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "apps_500", "Marathoner (500)", ("app.added",),
        "SELECT COUNT(*) >= 500 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'app.added' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "first_phone_screen", "First Phone Screen", ("status.phone_screen",),
        "SELECT COUNT(*) >= 1 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'status.phone_screen' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "first_onsite", "First Onsite", ("status.onsite",),
        "SELECT COUNT(*) >= 1 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'status.onsite' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "first_offer", "First Offer", ("status.offer",),
        "SELECT COUNT(*) >= 1 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'status.offer' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "networker_10", "Networker (10 referrals)", ("referral.added",),
        "SELECT COUNT(*) >= 10 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'referral.added' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "networker_50", "Super-Networker (50 referrals)", ("referral.added",),
        "SELECT COUNT(*) >= 50 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'referral.added' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "streak_3", "3-Day Streak", ("__streak__",),
        f"SELECT current_streak >= 3 FROM user_progress WHERE user_id = $1 {_UP_NOT_DELETED}",
    ),
    AchievementSpec(
        "streak_7", "Week-long Streak", ("__streak__",),
        f"SELECT current_streak >= 7 FROM user_progress WHERE user_id = $1 {_UP_NOT_DELETED}",
    ),
    AchievementSpec(
        "streak_14", "Fortnight Streak", ("__streak__",),
        f"SELECT current_streak >= 14 FROM user_progress WHERE user_id = $1 {_UP_NOT_DELETED}",
    ),
    AchievementSpec(
        "streak_30", "Iron Will (30 days)", ("__streak__",),
        f"SELECT current_streak >= 30 FROM user_progress WHERE user_id = $1 {_UP_NOT_DELETED}",
    ),
    AchievementSpec(
        "streak_100", "Centennial (100 days)", ("__streak__",),
        f"SELECT current_streak >= 100 FROM user_progress WHERE user_id = $1 {_UP_NOT_DELETED}",
    ),
    AchievementSpec(
        "comeback_kid", "Comeback Kid", ("comeback",),
        "SELECT COUNT(*) >= 1 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'comeback' {_XP_EVENT_NOT_DELETED}",
    ),
    # ── M10 Study tracker ────────────────────────────────────────────
    AchievementSpec(
        "syllabus_set", "Built a Study Plan",
        ("study.section_added",),
        "SELECT COUNT(*) >= 1 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'study.section_added' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "first_revision", "First Revision",
        ("study.topic_revised_first",),
        "SELECT COUNT(*) >= 1 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'study.topic_revised_first' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "revised_10", "10 Topics Revised",
        ("study.topic_revised_first",),
        "SELECT COUNT(*) >= 10 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'study.topic_revised_first' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "revised_50", "Half-Century of Revision",
        ("study.topic_revised_first",),
        "SELECT COUNT(*) >= 50 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'study.topic_revised_first' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "revised_100", "Centurion (100 revisions)",
        ("study.topic_revised_first",),
        "SELECT COUNT(*) >= 100 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'study.topic_revised_first' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "first_mastered", "First Topic Mastered",
        ("study.topic_mastered",),
        "SELECT COUNT(*) >= 1 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'study.topic_mastered' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "subsection_master", "Subsection Conquered",
        ("study.subsection_completed",),
        "SELECT COUNT(*) >= 1 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'study.subsection_completed' {_XP_EVENT_NOT_DELETED}",
    ),
    AchievementSpec(
        "section_master", "Section Conquered",
        ("study.section_completed",),
        "SELECT COUNT(*) >= 1 FROM xp_events "
        f"WHERE user_id = $1 AND event_key = 'study.section_completed' {_XP_EVENT_NOT_DELETED}",
    ),
]


_TRIGGER_INDEX: dict[str, list[AchievementSpec]] = {}
for spec in ACHIEVEMENTS:
    for trig in spec.triggers:
        _TRIGGER_INDEX.setdefault(trig, []).append(spec)


# ---------------------------------------------------------------------------
# Result envelope
# ---------------------------------------------------------------------------


@dataclass
class XpResult:
    event_key: str
    xp_gained: int = 0
    duplicate: bool = False
    new_level: int | None = None
    streak: int = 0
    quests_progressed: list[str] = field(default_factory=list)
    quest_completed: list[str] = field(default_factory=list)
    unlocked: list[str] = field(default_factory=list)

    def to_envelope(self) -> dict:
        return {
            "xp_gained": self.xp_gained,
            "new_level": self.new_level,
            "streak": self.streak,
            "quests_progressed": self.quests_progressed,
            "quest_completed": self.quest_completed,
            "unlocked": self.unlocked,
            "duplicate": self.duplicate,
        }


def attach(response: Response, result: XpResult) -> None:
    """Attach the gamify envelope as an X-Gamify response header.

    The header is omitted for duplicate or no-op results so clients don't
    re-fire animations on retried requests.
    """
    if result.duplicate:
        return
    if (
        result.xp_gained == 0
        and result.new_level is None
        and not result.unlocked
        and not result.quest_completed
    ):
        return
    response.headers["X-Gamify"] = json.dumps(result.to_envelope())


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------


async def record_event(
    conn: asyncpg.Connection,
    user_id: int,
    event_key: str,
    *,
    ref_type: str = "",
    ref_id: int = 0,
    today: dt.date | None = None,
) -> XpResult:
    """Idempotently record a gamification event. Caller must hold a transaction."""
    if event_key not in XP_REWARDS:
        log.warning("gamify.unknown_event", event_key=event_key)
        return XpResult(event_key=event_key)

    xp = XP_REWARDS[event_key]
    today = today or dt.date.today()

    # 1. Idempotent insert. ON CONFLICT DO NOTHING returns no row.
    # The unique index xp_events_idem_uidx is partial (WHERE deleted_at
    # IS NULL) so the ON CONFLICT predicate must match.
    row = await conn.fetchrow(
        """
        INSERT INTO xp_events (user_id, event_key, xp_delta, ref_type, ref_id)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (user_id, event_key, ref_type, ref_id)
            WHERE deleted_at IS NULL DO NOTHING
        RETURNING id
        """,
        user_id, event_key, xp, ref_type, ref_id,
    )
    if row is None:
        return XpResult(event_key=event_key, duplicate=True)

    # 2. Ensure progress row exists.
    # ON CONFLICT resurrects a soft-deleted singleton row in place.
    await conn.execute(
        "INSERT INTO user_progress (user_id) VALUES ($1) "
        "ON CONFLICT (user_id) DO UPDATE SET deleted_at = NULL",
        user_id,
    )

    # 3. Compute streak transition + comeback.
    prog = await conn.fetchrow(
        "SELECT current_xp, current_level, current_streak, longest_streak, "
        "last_activity_at, freezes_remaining FROM user_progress "
        "WHERE user_id = $1 AND deleted_at IS NULL",
        user_id,
    )
    assert prog is not None
    streak, freezes, comeback_fired = _compute_streak(
        last=prog["last_activity_at"],
        today=today,
        current_streak=prog["current_streak"],
        freezes=prog["freezes_remaining"],
    )
    if streak > 0 and streak % 7 == 0 and prog["last_activity_at"] != today:
        freezes = min(3, freezes + 1)

    # 4. Apply XP, level, streak.
    new_xp = prog["current_xp"] + xp
    old_level = prog["current_level"]
    new_level = level_for_xp(new_xp)
    longest = max(prog["longest_streak"], streak)
    unseen_level_up = new_level if new_level > old_level else None

    await conn.execute(
        """
        UPDATE user_progress SET
            current_xp        = $2,
            current_level     = $3,
            current_streak    = $4,
            longest_streak    = $5,
            last_activity_at  = $6,
            freezes_remaining = $7,
            unseen_level_up   = COALESCE($8, unseen_level_up),
            updated_at        = NOW()
        WHERE user_id = $1 AND deleted_at IS NULL
        """,
        user_id, new_xp, new_level, streak, longest, today, freezes, unseen_level_up,
    )

    result = XpResult(
        event_key=event_key,
        xp_gained=xp,
        new_level=unseen_level_up,
        streak=streak,
    )

    # 5. Comeback bonus (recursive but bounded — comeback is not in QUESTS matchers).
    if comeback_fired:
        cb = await record_event(
            conn, user_id, "comeback",
            ref_type="day", ref_id=today.toordinal(),
            today=today,
        )
        if not cb.duplicate:
            result.xp_gained += cb.xp_gained
            result.unlocked.extend(cb.unlocked)

    # 6. Quest progress.
    quest_rows = await conn.fetch(
        "SELECT id, code, target, progress, reward_xp FROM quests "
        "WHERE user_id = $1 AND deleted_at IS NULL "
        "AND completed_at IS NULL AND expires_at > NOW()",
        user_id,
    )
    for q in quest_rows:
        spec = QUESTS.get(q["code"])
        if spec is None or not spec.matches(event_key):
            continue
        new_progress = q["progress"] + 1
        if new_progress >= q["target"]:
            # Wrap completion + XP award in one transaction so a crash between
            # the two statements can't leave the quest marked complete but XP unawarded.
            async with conn.transaction():
                await conn.execute(
                    "UPDATE quests SET progress = $1, completed_at = NOW() "
                    "WHERE id = $2 AND deleted_at IS NULL",
                    new_progress, q["id"],
                )
                # Award quest XP via a fresh xp_events row (idempotent by quest id).
                quest_reward = await conn.fetchrow(
                    """
                    INSERT INTO xp_events (user_id, event_key, xp_delta, ref_type, ref_id)
                    VALUES ($1, 'quest.complete', $2, 'quest', $3)
                    ON CONFLICT (user_id, event_key, ref_type, ref_id)
                        WHERE deleted_at IS NULL DO NOTHING
                    RETURNING id
                    """,
                    user_id, q["reward_xp"], q["id"],
                )
                if quest_reward is not None:
                    result.xp_gained += q["reward_xp"]
                    # Re-read progress to apply the quest reward to xp/level.
                    bumped = await conn.fetchrow(
                        "UPDATE user_progress SET current_xp = current_xp + $2, "
                        "current_level = $3, updated_at = NOW() "
                        "WHERE user_id = $1 AND deleted_at IS NULL "
                        "RETURNING current_xp, current_level",
                        user_id, q["reward_xp"], level_for_xp(new_xp + q["reward_xp"]),
                    )
                    if bumped and bumped["current_level"] > (result.new_level or old_level):
                        result.new_level = bumped["current_level"]
                        await conn.execute(
                            "UPDATE user_progress SET unseen_level_up = $2 "
                            "WHERE user_id = $1 AND deleted_at IS NULL",
                            user_id, bumped["current_level"],
                        )
                    new_xp += q["reward_xp"]
            result.quest_completed.append(q["code"])
        else:
            await conn.execute(
                "UPDATE quests SET progress = $1 "
                "WHERE id = $2 AND deleted_at IS NULL",
                new_progress, q["id"],
            )
            result.quests_progressed.append(q["code"])

    # 7. Achievements.
    triggers = list(_TRIGGER_INDEX.get(event_key, []))
    if streak > prog["current_streak"]:
        triggers.extend(_TRIGGER_INDEX.get("__streak__", []))
    for spec in triggers:
        already = await conn.fetchval(
            "SELECT 1 FROM achievements WHERE user_id = $1 AND code = $2 "
            "AND deleted_at IS NULL",
            user_id, spec.code,
        )
        if already:
            continue
        unlocked = await conn.fetchval(spec.check_sql, user_id)
        if unlocked:
            # On conflict resurrect: clear deleted_at, refresh unlocked_at,
            # mark unseen so the UI fires the unlock animation again.
            await conn.execute(
                """
                INSERT INTO achievements (user_id, code) VALUES ($1, $2)
                ON CONFLICT (user_id, code)
                DO UPDATE SET deleted_at = NULL,
                              unlocked_at = NOW(),
                              seen_at = NULL
                """,
                user_id, spec.code,
            )
            result.unlocked.append(spec.code)
            metrics.GAMIFY_ACHIEVEMENTS.labels(code=spec.code).inc()

    # 8. Metrics.
    metrics.GAMIFY_XP_AWARDED.labels(event_key=event_key).inc(xp)
    if unseen_level_up:
        metrics.GAMIFY_LEVEL_UPS.labels(new_level=str(unseen_level_up)).inc()

    return result


def _compute_streak(
    *,
    last: dt.date | None,
    today: dt.date,
    current_streak: int,
    freezes: int,
) -> tuple[int, int, bool]:
    """Returns (new_streak, new_freezes, comeback_fired)."""
    if last is None:
        return 1, freezes, False
    if last == today:
        return current_streak, freezes, False
    gap = (today - last).days
    if gap == 1:
        return current_streak + 1, freezes, False
    # gap >= 2: use a freeze (one freeze covers exactly one missed day at a time).
    if gap == 2 and freezes > 0:
        return current_streak + 1, freezes - 1, False
    comeback = gap >= 7
    return 1, freezes, comeback


# ---------------------------------------------------------------------------
# State + read API
# ---------------------------------------------------------------------------


@dataclass
class StateDTO:
    xp: int
    level: int
    xp_into_level: int
    xp_for_level: int
    streak: int
    longest_streak: int
    freezes: int
    unseen_level_up: int | None
    daily_quests: list[dict]
    weekly_quests: list[dict]
    recent_unlocks: list[dict]

    def to_dict(self) -> dict:
        return {
            "xp": self.xp,
            "level": self.level,
            "xp_into_level": self.xp_into_level,
            "xp_for_level": self.xp_for_level,
            "streak": self.streak,
            "longest_streak": self.longest_streak,
            "freezes": self.freezes,
            "unseen_level_up": self.unseen_level_up,
            "daily_quests": self.daily_quests,
            "weekly_quests": self.weekly_quests,
            "recent_unlocks": self.recent_unlocks,
        }


async def get_state(conn: asyncpg.Connection, user_id: int) -> StateDTO:
    # ON CONFLICT resurrects a soft-deleted singleton row in place.
    await conn.execute(
        "INSERT INTO user_progress (user_id) VALUES ($1) "
        "ON CONFLICT (user_id) DO UPDATE SET deleted_at = NULL",
        user_id,
    )
    prog = await conn.fetchrow(
        "SELECT current_xp, current_level, current_streak, longest_streak, "
        "freezes_remaining, unseen_level_up "
        "FROM user_progress WHERE user_id = $1 AND deleted_at IS NULL",
        user_id,
    )
    assert prog is not None

    quest_rows = await conn.fetch(
        "SELECT code, period, target, progress, reward_xp, "
        "completed_at, expires_at FROM quests "
        "WHERE user_id = $1 AND deleted_at IS NULL AND expires_at > NOW() "
        "ORDER BY period, code",
        user_id,
    )
    dailies, weeklies = [], []
    for q in quest_rows:
        spec = QUESTS.get(q["code"])
        item = {
            "code": q["code"],
            "title": spec.title if spec else q["code"],
            "target": q["target"],
            "progress": q["progress"],
            "reward_xp": q["reward_xp"],
            "completed": q["completed_at"] is not None,
            "expires_at": q["expires_at"].isoformat(),
        }
        (dailies if q["period"] == "daily" else weeklies).append(item)

    unlock_rows = await conn.fetch(
        "SELECT code, unlocked_at, seen_at FROM achievements "
        "WHERE user_id = $1 AND deleted_at IS NULL "
        "ORDER BY unlocked_at DESC LIMIT 10",
        user_id,
    )
    recent = [
        {
            "code": u["code"],
            "title": next((a.title for a in ACHIEVEMENTS if a.code == u["code"]), u["code"]),
            "unlocked_at": u["unlocked_at"].isoformat(),
            "seen": u["seen_at"] is not None,
        }
        for u in unlock_rows
    ]

    xp = prog["current_xp"]
    into, span = xp_to_next_level(xp)
    return StateDTO(
        xp=xp,
        level=prog["current_level"],
        xp_into_level=into,
        xp_for_level=span,
        streak=prog["current_streak"],
        longest_streak=prog["longest_streak"],
        freezes=prog["freezes_remaining"],
        unseen_level_up=prog["unseen_level_up"],
        daily_quests=dailies,
        weekly_quests=weeklies,
        recent_unlocks=recent,
    )


async def acknowledge(conn: asyncpg.Connection, user_id: int) -> None:
    """Clear unseen level-up flag + mark all achievements as seen."""
    await conn.execute(
        "UPDATE user_progress SET unseen_level_up = NULL "
        "WHERE user_id = $1 AND deleted_at IS NULL",
        user_id,
    )
    await conn.execute(
        "UPDATE achievements SET seen_at = NOW() "
        "WHERE user_id = $1 AND deleted_at IS NULL AND seen_at IS NULL",
        user_id,
    )


async def list_achievements(conn: asyncpg.Connection, user_id: int) -> list[dict]:
    unlocked_rows = await conn.fetch(
        "SELECT code, unlocked_at FROM achievements "
        "WHERE user_id = $1 AND deleted_at IS NULL",
        user_id,
    )
    unlocked = {r["code"]: r["unlocked_at"].isoformat() for r in unlocked_rows}
    return [
        {
            "code": spec.code,
            "title": spec.title,
            "unlocked_at": unlocked.get(spec.code),
        }
        for spec in ACHIEVEMENTS
    ]


# ---------------------------------------------------------------------------
# Quest rotation
# ---------------------------------------------------------------------------


def _seeded_pick(pool: list[str], date_key: str, n: int) -> list[str]:
    """Deterministic per-day pick — same day = same quests for same user."""
    digest = hashlib.sha256(date_key.encode()).hexdigest()
    seed = int(digest[:16], 16)
    indices = sorted(range(len(pool)), key=lambda i: (seed >> i) & 0xFFFF)
    return [pool[i] for i in indices[:n]]


async def rotate_quests_for_user(
    conn: asyncpg.Connection, user_id: int, today: dt.date | None = None
) -> None:
    today = today or dt.date.today()
    midnight = dt.datetime.combine(today + dt.timedelta(days=1), dt.time.min)

    # Daily — 3 from pool, only if user has no daily quests yet today.
    # Skipping when any exist prevents pool-size changes from over-stuffing
    # the active set (each new code would otherwise bypass the unique index).
    existing_daily = await conn.fetchval(
        "SELECT COUNT(*) FROM quests "
        "WHERE user_id = $1 AND deleted_at IS NULL "
        "AND period = 'daily' AND expires_at = $2",
        user_id, midnight,
    ) or 0
    if existing_daily == 0:
        daily_codes = _seeded_pick(
            DAILY_POOL, f"{user_id}:{today.isoformat()}", 3
        )
        for code in daily_codes:
            spec = QUESTS[code]
            await conn.execute(
                """
                INSERT INTO quests (user_id, code, period, target, reward_xp, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (user_id, code, expires_at)
                    WHERE deleted_at IS NULL DO NOTHING
                """,
                user_id, spec.code, spec.period, spec.target, spec.reward_xp, midnight,
            )

    # Weekly — 1 from pool, anchored to start-of-week; same anti-stuffing rule.
    monday = today - dt.timedelta(days=today.weekday())
    week_end = dt.datetime.combine(monday + dt.timedelta(days=7), dt.time.min)
    existing_weekly = await conn.fetchval(
        "SELECT COUNT(*) FROM quests "
        "WHERE user_id = $1 AND deleted_at IS NULL "
        "AND period = 'weekly' AND expires_at = $2",
        user_id, week_end,
    ) or 0
    if existing_weekly == 0:
        weekly_codes = _seeded_pick(
            WEEKLY_POOL, f"{user_id}:{monday.isoformat()}", 1
        )
        for code in weekly_codes:
            spec = QUESTS[code]
            await conn.execute(
                """
                INSERT INTO quests (user_id, code, period, target, reward_xp, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (user_id, code, expires_at)
                    WHERE deleted_at IS NULL DO NOTHING
                """,
                user_id, spec.code, spec.period, spec.target, spec.reward_xp, week_end,
            )


async def rotate_quests_for_all(conn: asyncpg.Connection) -> int:
    rows = await conn.fetch(
        "SELECT id FROM users WHERE deleted_at IS NULL"
    )
    today = dt.date.today()
    for row in rows:
        await rotate_quests_for_user(conn, row["id"], today=today)
    return len(rows)
