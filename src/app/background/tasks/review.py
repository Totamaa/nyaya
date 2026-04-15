from uuid import UUID

from app.core.config.broker import broker
from app.core.config.database import AsyncSessionLocal, UnitOfWork
from app.core.config.logs import get_logger
from app.modules.users.dependencies import get_user_repository, get_user_service

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
    Génère la review pour UN user.
    Exécuté en parallèle par les workers.
    """
    logger.info("TASK:review_user", f"Reviewing user_id={user_id}")

    #TODO: implémenter la logique de review pour ce user_id

    logger.info("TASK:review_user", f"Review complete for user_id={user_id}")
