from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.logs import LoggerManager
from app.core.config.settings import get_settings
from app.modules.llm.connectors.factory import build_llm_client
from app.modules.llm.feedback.runner import generate_feedback
from app.core.utils.date_lib import month_range
from app.modules.evaluations.model import EvaluationModel
from app.modules.evaluations.schemas import CRITERIA
from app.modules.feedbacks.exceptions import (
    FeedbackNotFoundException,
    InsufficientDataForFeedbackException,
    InvalidYearMonthFormatException,
)
from app.modules.feedbacks.repository import FeedbackRepository
from app.modules.feedbacks.schemas import (
    LLMFeedbackInput,
    UserMonthlyFeedbackResponse,
    WorstCategoryEntry,
    WorstMessageEntry,
)
from app.modules.messages.model import MessageModel
from app.modules.messages.repository import MessageRepository
from app.modules.users.exceptions import UserNotFoundException
from app.modules.users.repository import UserRepository


def _build_llm_input(
    user_id: UUID,
    period_str: str,
    rows: list[tuple[MessageModel, EvaluationModel]],
    top_n_categories: int,
    n_messages_per_category: int,
) -> LLMFeedbackInput | None:
    category_data: dict[str, list[tuple[str, float]]] = {cat: [] for cat in CRITERIA}

    for message, evaluation in rows:
        for cat in CRITERIA:
            score = getattr(evaluation, cat)
            if score is not None:
                category_data[cat].append((message.text, score))

    category_means = {
        cat: sum(s for _, s in entries) / len(entries)
        for cat, entries in category_data.items()
        if entries
    }

    if not category_means:
        return None

    worst_cat_names = sorted(category_means, key=lambda c: category_means[c])[:top_n_categories]

    worst_categories = [
        WorstCategoryEntry(
            category=cat,
            mean_score=round(category_means[cat], 2),
            worst_messages=[
                WorstMessageEntry(text=text, score=score)
                for text, score in sorted(category_data[cat], key=lambda x: x[1])[:n_messages_per_category]
            ],
        )
        for cat in worst_cat_names
    ]

    return LLMFeedbackInput(
        user_id=user_id,
        period=period_str,
        worst_categories=worst_categories,
    )



class FeedbackService:

    def __init__(
        self,
        logger: LoggerManager,
        session: AsyncSession,
        request_id: str,
        feedback_repository: FeedbackRepository,
        message_repository: MessageRepository,
        user_repository: UserRepository,
    ):
        self.tag = "SERVICE:Feedback"
        self.logger = logger
        self.session = session
        self.request_id = request_id
        self.feedback_repository = feedback_repository
        self.message_repository = message_repository
        self.user_repository = user_repository

    async def generate(
        self,
        user_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> UserMonthlyFeedbackResponse:
        settings = get_settings()
        period_str = period_start.strftime("%Y-%m")
        month = date(period_start.year, period_start.month, 1)

        self.logger.info(
            tag=self.tag,
            message=f"Generating feedback for user_id={user_id} period={period_str}",
            extra=self.request_id,
        )

        user = await self.user_repository.get_by_id(user_id=user_id, db=self.session)
        if not user:
            raise UserNotFoundException(external_id=str(user_id))

        existing = await self.feedback_repository.get_by_user_and_month(
            user_id=user_id,
            month=month,
            db=self.session,
        )
        if existing:
            self.logger.info(
                tag=self.tag,
                message=f"Feedback already exists for user_id={user_id} period={period_str}, returning existing.",
                extra=self.request_id,
            )
            return UserMonthlyFeedbackResponse.from_model(existing)

        rows = await self.message_repository.get_messages_with_evaluations(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            db=self.session,
        )

        llm_input = _build_llm_input(
            user_id=user_id,
            period_str=period_str,
            rows=rows,
            top_n_categories=settings.REVIEW_TOP_WORST_CATEGORIES,
            n_messages_per_category=settings.REVIEW_WORST_MESSAGES_PER_CATEGORY,
        )

        if llm_input is None:
            raise InsufficientDataForFeedbackException(user_id=user_id)

        client = build_llm_client(
            base_url=settings.LLM_BASE_URL,
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            timeout_s=float(settings.LLM_TIMEOUT_SECONDS),
            use_mock=settings.LLM_USE_MOCK,
        )
        llm_result = generate_feedback(client, llm_input)

        feedback = llm_result.to_model(user_id=user_id, user_external_id=user.external_id, month=month)
        await self.feedback_repository.create(feedback=feedback, db=self.session)

        self.logger.info(
            tag=self.tag,
            message=f"Feedback created id={feedback.id} for user_id={user_id} period={period_str}",
            extra=self.request_id,
        )

        return UserMonthlyFeedbackResponse.from_model(feedback)

    async def get_history_by_user(
        self,
        user_external_id: str,
        limit: int,
        offset: int,
    ) -> list[UserMonthlyFeedbackResponse]:
        user = await self.user_repository.get_by_external_id(
            external_id=user_external_id,
            db=self.session,
        )
        if not user:
            raise UserNotFoundException(external_id=user_external_id)

        start_month, end_month = month_range(limit, offset)
        feedbacks = await self.feedback_repository.get_by_user_and_month_range(
            user_id=user.id,
            start_month=start_month,
            end_month=end_month,
            db=self.session,
        )
        return [UserMonthlyFeedbackResponse.from_model(f) for f in feedbacks]

    async def get_by_user_and_month(
        self,
        user_external_id: str,
        year_month: str,
    ) -> UserMonthlyFeedbackResponse:
        user = await self.user_repository.get_by_external_id(
            external_id=user_external_id,
            db=self.session,
        )
        if not user:
            raise UserNotFoundException(external_id=user_external_id)

        try:
            parsed = datetime.strptime(year_month, "%Y-%m")
            month = date(parsed.year, parsed.month, 1)
        except ValueError:
            raise InvalidYearMonthFormatException(year_month=year_month)

        feedback = await self.feedback_repository.get_by_user_and_month(
            user_id=user.id,
            month=month,
            db=self.session,
        )
        if not feedback:
            raise FeedbackNotFoundException(user_external_id=user_external_id, year_month=year_month)

        return UserMonthlyFeedbackResponse.from_model(feedback)
