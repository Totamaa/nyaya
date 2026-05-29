import logging
from uuid import UUID

from fastapi import status

from app.core.errors.exceptions.base import BusinessException


class FeedbackNotFoundException(BusinessException):
    def __init__(self, user_external_id: str, year_month: str):
        super().__init__(
            message_front="Feedback not found.",
            message_log=f"Feedback for user external_id={user_external_id} month={year_month} not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            log_level=logging.WARNING,
            tag="SERVICE:Feedback",
        )


class InsufficientDataForFeedbackException(BusinessException):
    def __init__(self, user_id: UUID):
        super().__init__(
            message_front="Not enough evaluated messages to generate feedback.",
            message_log=f"No evaluated messages found for user_id={user_id} in the given period.",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            log_level=logging.WARNING,
            tag="SERVICE:Feedback",
        )


class InvalidYearMonthFormatException(BusinessException):
    def __init__(self, year_month: str):
        super().__init__(
            message_front="Invalid year_month format. Expected 'YYYY-MM'.",
            message_log=f"Invalid year_month format: '{year_month}'. Expected 'YYYY-MM'.",
            status_code=status.HTTP_400_BAD_REQUEST,
            log_level=logging.WARNING,
            tag="SERVICE:Feedback",
        )
