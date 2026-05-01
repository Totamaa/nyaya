import asyncio
import functools

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config.logs import get_logger

logger = get_logger()
scheduler = BackgroundScheduler()


def start_scheduler():
    loop = asyncio.get_event_loop()
    scheduler.start()
    logger.info("SCHEDULER:Start", "Scheduler started with tasks.")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("SCHEDULER:Stop", "Scheduler stopped.")
