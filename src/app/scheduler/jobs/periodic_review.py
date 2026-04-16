import asyncio

from app.core.config.logs import get_logger
from app.background.tasks.review import orchestrate_periodic_reviews

logger = get_logger()


def periodic_review_job(loop: asyncio.AbstractEventLoop):
    """Appelé par APScheduler — enqueue dans Taskiq via le loop uvicorn."""
    logger.info("JOB:periodic_review", "Triggered by scheduler")
    future = asyncio.run_coroutine_threadsafe(orchestrate_periodic_reviews.kiq(), loop)
    future.result(timeout=30)
    logger.info("JOB:periodic_review", "Orchestrator task dispatched")
