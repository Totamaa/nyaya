import asyncio
import functools

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config.logs import get_logger
from app.scheduler.jobs.periodic_review import periodic_review_job

logger = get_logger()
scheduler = BackgroundScheduler()


def start_scheduler():
    loop = asyncio.get_event_loop()
    scheduler.add_job(
        functools.partial(periodic_review_job, loop),
        "cron",
        minute="*/2",
    )

    scheduler.start()
    logger.info("SCHEDULER:Start", "Scheduler started with tasks.")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("SCHEDULER:Stop", "Scheduler stopped.")
