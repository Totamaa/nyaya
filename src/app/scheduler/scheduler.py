from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config.logs import get_logger
from app.jobs.scheduled.jobs.cleanup import cleanup_old_messages

logger = get_logger()
scheduler = BackgroundScheduler()


def start_scheduler():
    scheduler.add_job(
        cleanup_old_messages,
        trigger="cron",
        hour=3,
        minute=0,
        id="cleanup_old_messages",
    )

    scheduler.start()
    logger.info("SCHEDULER:Start", "Scheduler started with tasks.")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("SCHEDULER:Stop", "Scheduler stopped.")
