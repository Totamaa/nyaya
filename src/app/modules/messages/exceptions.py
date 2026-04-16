import logging

from fastapi import status

from app.core.errors.exceptions.base import BusinessException


class MessageAlreadyExistsException(BusinessException):
    def __init__(self):
        super().__init__(
            message_front="Message already exists.",
            message_log="Message with this external_id already exists.",
            status_code=status.HTTP_409_CONFLICT,
            log_level=logging.WARNING,
            tag="SERVICE:Message",
        )
