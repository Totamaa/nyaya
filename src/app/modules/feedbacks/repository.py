from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.feedbacks.model import UserMonthlyFeedbackModel


class FeedbackRepository:

    async def create(
        self,
        feedback: UserMonthlyFeedbackModel,
        db: AsyncSession,
    ) -> UserMonthlyFeedbackModel:
        db.add(feedback)
        await db.flush()
        return feedback

    async def get_by_user_and_month(
        self,
        user_id: UUID,
        month: date,
        db: AsyncSession,
    ) -> UserMonthlyFeedbackModel | None:
        stmt = select(UserMonthlyFeedbackModel).where(
            UserMonthlyFeedbackModel.user_id == user_id,
            UserMonthlyFeedbackModel.month == month,
        )
        result = await db.execute(stmt)
        return result.scalars().one_or_none()
