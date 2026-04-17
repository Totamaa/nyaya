import asyncio

from app.core.config.logs import get_logger
from app.background.tasks.review import orchestrate_monthly_reviews

logger = get_logger()


def monthly_review_job(loop: asyncio.AbstractEventLoop):
    """Appelé par APScheduler — enqueue dans Taskiq via le loop uvicorn."""
    logger.info("JOB:monthly_review", "Triggered by scheduler")
    future = asyncio.run_coroutine_threadsafe(orchestrate_monthly_reviews.kiq(), loop)
    future.result(timeout=30)
    logger.info("JOB:monthly_review", "Orchestrator task dispatched")
