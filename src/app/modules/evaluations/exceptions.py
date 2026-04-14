import logging
from uuid import UUID

from fastapi import status

from app.core.errors.exceptions.base import BusinessException


class EvaluationNotFoundException(BusinessException):
    def __init__(self, message_id: UUID):
        super().__init__(
            message_front="Evaluation not found.",
            message_log=f"Evaluation for message_id={message_id} not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            log_level=logging.WARNING,
            tag="SERVICE:Evaluation",
        )
