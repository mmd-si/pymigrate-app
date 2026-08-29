from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.utils import EST
from app.jobs.cleanup import remove_expired_sessions

scheduler = AsyncIOScheduler(timezone='UTC')


def start_scheduler():
    scheduler.add_job(
        remove_expired_sessions,
        trigger=CronTrigger(hour=2, minute=0, timezone=EST),
        id='remove_expired_sessions',
        replace_existing=True,
    )
    scheduler.start()


def shutdown_scheduler():
    scheduler.shutdown()
