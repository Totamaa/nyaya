import logging

from fastapi import status

from app.core.errors.exceptions.base import BusinessException


class InvalidYearMonthFormatException(BusinessException):
    def __init__(self, year_month: str):
        super().__init__(
            message_front="Invalid year_month format. Expected 'YYYY-MM'.",
            message_log=f"Invalid year_month format: '{year_month}'. Expected 'YYYY-MM'.",
            status_code=status.HTTP_400_BAD_REQUEST,
            log_level=logging.WARNING,
            tag="SERVICE:Totem",
        )
