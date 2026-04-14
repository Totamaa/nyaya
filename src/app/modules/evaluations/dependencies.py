from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api.dependencies.db import get_db
from app.core.api.dependencies.request_id import get_request_id
from app.core.config.logs import get_logger
from app.modules.evaluations.repository import EvaluationRepository
from app.modules.evaluations.service import EvaluationService


def get_evaluation_repository() -> EvaluationRepository:
    return EvaluationRepository()


def get_evaluation_service(
    logger=Depends(get_logger),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
    evaluation_repository: EvaluationRepository = Depends(get_evaluation_repository),
) -> EvaluationService:
    return EvaluationService(
        logger=logger,
        db=db,
        request_id=request_id,
        evaluation_repository=evaluation_repository,
    )
