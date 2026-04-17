import logging
from typing import Callable, Awaitable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def init_scheduler(refresh_fn: Callable[[], Awaitable[None]]) -> AsyncIOScheduler:
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="UTC")

    # Every 2 hours throughout the day
    _scheduler.add_job(
        refresh_fn, IntervalTrigger(hours=2),
        id="auto_refresh", replace_existing=True,
        max_instances=1,
    )

    # Dedicated refreshes at high-traffic windows (all UTC)
    for hour, label in ((11, "morning"), (17, "afternoon"), (22, "evening")):
        _scheduler.add_job(
            refresh_fn, CronTrigger(hour=hour, minute=0),
            id=f"{label}_refresh", replace_existing=True,
            max_instances=1,
        )

    _scheduler.start()
    logger.info("Scheduler started — refreshing at 11:00, 17:00, 22:00 UTC + every 2 h")
    return _scheduler


def shutdown_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
