import asyncio
import datetime as dt
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import pool
from app.services import gamify
from app.services.nudge_engine import run_all_checks
from app.services.email_digest import send_weekly_digest_for_all

log = logging.getLogger("scheduler")
_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _run_for_all_users_sync,
        CronTrigger(hour=settings.nudge_cron_hour, minute=0),
        id="daily_nudges",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    _scheduler.add_job(
        _rotate_quests_sync,
        CronTrigger(hour=0, minute=5),
        id="rotate_quests",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    _scheduler.add_job(
        _send_digest_sync,
        CronTrigger(day_of_week="sun", hour=8, minute=0),
        id="weekly_digest",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    _scheduler.add_job(
        _auto_ghost_sync,
        CronTrigger(hour=1, minute=0),
        id="auto_ghost",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    log.info("scheduler.started cron_hour=%s", settings.nudge_cron_hour)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None


def _run_for_all_users_sync() -> None:
    try:
        asyncio.run(_run_for_all_users_async())
    except Exception as e:  # noqa: BLE001
        log.exception("scheduler.run_failed: %s", e)


async def _run_for_all_users_async() -> None:
    today = dt.date.today()
    async with pool().acquire() as conn:
        user_rows = await conn.fetch(
            "SELECT id FROM users WHERE deleted_at IS NULL"
        )
        for row in user_rows:
            n = await run_all_checks(conn, user_id=row["id"], today=today)
            log.info("scheduler.run user_id=%s inserted=%s", row["id"], n)


def _rotate_quests_sync() -> None:
    try:
        asyncio.run(_rotate_quests_async())
    except Exception as e:  # noqa: BLE001
        log.exception("scheduler.rotate_quests_failed: %s", e)


async def _rotate_quests_async() -> None:
    async with pool().acquire() as conn:
        n = await gamify.rotate_quests_for_all(conn)
        log.info("scheduler.rotate_quests users=%s", n)


def _send_digest_sync() -> None:
    try:
        asyncio.run(send_weekly_digest_for_all())
    except Exception as e:  # noqa: BLE001
        log.exception("scheduler.digest_failed: %s", e)


def _auto_ghost_sync() -> None:
    try:
        asyncio.run(_auto_ghost_async())
    except Exception as e:  # noqa: BLE001
        log.exception("scheduler.auto_ghost_failed: %s", e)


async def _auto_ghost_async() -> None:
    async with pool().acquire() as conn:
        result = await conn.execute(
            """
            UPDATE applications
            SET status = 'Ghosted', last_updated = now()
            WHERE status = 'Applied'
              AND deleted_at IS NULL
              AND applied_date < now() - INTERVAL '7 days'
            """,
        )
        count = int(result.split()[-1]) if result else 0
        log.info("scheduler.auto_ghost updated=%s", count)
