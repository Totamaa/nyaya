import logging

from fastapi import status

from app.core.errors.exceptions.base import BusinessException


class UserNotFoundException(BusinessException):
    def __init__(self, external_id: str):
        super().__init__(
            message_front="User not found.",
            message_log=f"User with external_id={external_id} not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            log_level=logging.WARNING,
            tag="SERVICE:User",
        )
