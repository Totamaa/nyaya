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

    async def get_by_user_and_month_range(
        self,
        user_id: UUID,
        start_month: date,
        end_month: date,
        db: AsyncSession,
    ) -> list[UserMonthlyFeedbackModel]:
        stmt = (
            select(UserMonthlyFeedbackModel)
            .where(
                UserMonthlyFeedbackModel.user_id == user_id,
                UserMonthlyFeedbackModel.month >= start_month,
                UserMonthlyFeedbackModel.month <= end_month,
            )
            .order_by(UserMonthlyFeedbackModel.month.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
