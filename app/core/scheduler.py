from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config.settings import get_settings
from app.core.utils import EST
from app.jobs.cleanup import remove_expired_sessions
from app.jobs.transfer import run_drain

scheduler = AsyncIOScheduler(timezone='UTC')


def start_scheduler():
    settings = get_settings()

    scheduler.add_job(
        remove_expired_sessions,
        trigger=CronTrigger(hour=2, minute=0, timezone=EST),
        id='remove_expired_sessions',
        replace_existing=True,
    )
    scheduler.add_job(
        run_drain,
        trigger=IntervalTrigger(seconds=settings.transfer_poll_interval),
        id='transfer_drain',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()


def shutdown_scheduler():
    scheduler.shutdown()
