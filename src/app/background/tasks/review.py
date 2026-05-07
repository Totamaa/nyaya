from datetime import date, datetime, timezone
from uuid import UUID

from app.core.config.broker import broker
from app.core.config.database import AsyncSessionLocal, UnitOfWork
from app.core.config.logs import get_logger
from app.modules.evaluations.repository import EvaluationRepository
from app.modules.evaluations.service import EvaluationService
from app.modules.feedbacks.dependencies import get_feedback_repository
from app.modules.feedbacks.exceptions import InsufficientDataForFeedbackException, LLMTimeoutException
from app.modules.feedbacks.service import FeedbackService
from app.modules.messages.repository import MessageRepository
from app.modules.totems.dependencies import get_totem_repository
from app.modules.totems.schemas import TotemAssignment
from app.modules.totems.service import TotemService
from app.modules.totems.utils import CRITERIA, compute_totem_assignments
from app.modules.user_totems.dependencies import get_user_totem_repository
from app.modules.users.dependencies import get_user_repository, get_user_service
from app.modules.users.exceptions import UserNotFoundException
from app.modules.users.repository import UserRepository

logger = get_logger()


@broker.task(task_name="review:orchestrate")
async def orchestrate_monthly_reviews() -> None:
    """
    Récupère les user_ids éligibles, calcule les rankings une seule fois,
    puis dispatch une tâche par user avec ses assignments pré-calculés.
    """
    logger.info("TASK:orchestrate", "Starting monthly review orchestration")

    now = datetime.now(timezone.utc)
    period_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 1:
        period_start = period_end.replace(year=now.year - 1, month=12)
    else:
        period_start = period_end.replace(month=now.month - 1)
    month = date(period_start.year, period_start.month, 1)

    async with AsyncSessionLocal() as session:
        async with UnitOfWork(session):
            user_service = get_user_service(
                logger=logger,
                session=session,
                request_id="task:review:orchestrate",
                user_repository=get_user_repository(),
                message_repository=MessageRepository(),
            )
            user_ids = await user_service.get_eligible_user_ids_for_monthly_review()

            eval_service = EvaluationService(
                logger=logger,
                session=session,
                request_id="task:review:orchestrate",
                evaluation_repository=EvaluationRepository(),
            )
            criteria_rankings, global_ranking = await eval_service.get_all_rankings(CRITERIA)

    logger.info("TASK:orchestrate", f"Found {len(user_ids)} eligible users, rankings computed")

    for user_id in user_ids:
        assignments = compute_totem_assignments(user_id, criteria_rankings, global_ranking)
        await review_single_user.kiq(user_id, month, assignments)

    logger.info("TASK:orchestrate", f"Dispatched {len(user_ids)} review tasks")


@broker.task(task_name="review:single_user")
async def review_single_user(
    user_id: UUID,
    month: date,
    totem_assignments: list[TotemAssignment],
) -> None:
    """
    Génère le feedback mensuel et persiste les totems pré-calculés pour UN user.
    Exécuté en parallèle par les workers.
    """
    now = datetime.now(timezone.utc)
    period_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 1:
        period_start = period_end.replace(year=now.year - 1, month=12)
    else:
        period_start = period_end.replace(month=now.month - 1)
    period_str = period_start.strftime("%Y-%m")

    logger.info("TASK:review_user", f"Processing user_id={user_id} period={period_str}")

    # --- Étape 1 : feedback mensuel ---
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
            try:
                result = await feedback_service.generate(
                    user_id=user_id,
                    period_start=period_start,
                    period_end=period_end,
                )
                logger.info("TASK:review_user", f"Feedback generated id={result.id} for user_id={user_id}")
            except UserNotFoundException:
                return
            except (InsufficientDataForFeedbackException, LLMTimeoutException):
                pass

    # --- Étape 2 : assignation des totems ---
    async with AsyncSessionLocal() as session:
        async with UnitOfWork(session):
            totem_service = TotemService(
                logger=logger,
                session=session,
                request_id=f"task:review:{user_id}",
                totem_repository=get_totem_repository(),
                user_totem_repository=get_user_totem_repository(),
                user_repository=UserRepository(),
            )
            totems = await totem_service.assign_monthly_totems(
                user_id=user_id,
                month=month,
                assignments=totem_assignments,
            )

    if totems is None:
        logger.info("TASK:review_user", f"Skipped totem assignment (already assigned) for user_id={user_id}")
    else:
        logger.info("TASK:review_user", f"Assigned {len(totems)} totem(s) for user_id={user_id}")
