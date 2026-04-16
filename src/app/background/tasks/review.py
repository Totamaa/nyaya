from datetime import datetime, timezone
from uuid import UUID

from app.core.config.broker import broker
from app.core.config.database import AsyncSessionLocal, UnitOfWork
from app.core.config.logs import get_logger
from app.modules.feedbacks.dependencies import get_feedback_repository
from app.modules.feedbacks.service import FeedbackService
from app.modules.messages.repository import MessageRepository
from app.modules.users.dependencies import get_user_repository, get_user_service
from app.modules.users.repository import UserRepository

logger = get_logger()


@broker.task(task_name="review:orchestrate")
async def orchestrate_periodic_reviews() -> None:
    """
    Récupère les user_ids éligibles et dispatch une tâche par user.
    """
    logger.info("TASK:orchestrate", "Starting periodic review orchestration")

    async with AsyncSessionLocal() as session:
        async with UnitOfWork(session):
            user_service = get_user_service(
                logger=logger,
                session=session,
                request_id="task:review:orchestrate",
                user_repository=get_user_repository(),
            )
            user_ids = await user_service.get_eligible_user_ids_for_periodic_review()

    logger.info("TASK:orchestrate", f"Found {len(user_ids)} eligible users")

    for user_id in user_ids:
        await review_single_user.kiq(user_id)

    logger.info("TASK:orchestrate", f"Dispatched {len(user_ids)} review tasks")


@broker.task(task_name="review:single_user")
async def review_single_user(user_id: UUID) -> None:
    """
    Génère le feedback mensuel pour UN user.
    Exécuté en parallèle par les workers.
    """
    now = datetime.now(timezone.utc)
    period_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 1:
        period_start = period_end.replace(year=now.year - 1, month=12)
    else:
        period_start = period_end.replace(month=now.month - 1)
    period_str = period_start.strftime("%Y-%m")

    logger.info("TASK:review_user", f"Generating feedback for user_id={user_id} period={period_str}")

    async with AsyncSessionLocal() as session:
        async with UnitOfWork(session):
            feedback_service = FeedbackService(
                logger=logger,
                session=session,
                request_id=f"task:review:{user_id}",
                feedback_repository=get_feedback_repository(),
                message_repository=MessageRepository(),
                user_repository=UserRepository(),
            )
            result = await feedback_service.generate(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
            )

    if result:
        logger.info("TASK:review_user", f"Feedback generated id={result.id} for user_id={user_id}")
    else:
        logger.warning("TASK:review_user", f"No feedback generated for user_id={user_id} (insufficient data)")
