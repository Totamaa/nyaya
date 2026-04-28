import logging
from fastapi import status

class AppException(Exception):
    def __init__(
        self,
        message_front: str = "An error occurred.",
        message_log: str | None = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        log_level: int = logging.ERROR,
    ):
        self.message_front = message_front
        self.message_log = message_log or message_front
        self.status_code = status_code
        self.log_level = log_level
        
class DBException(AppException):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
class BusinessException(AppException):
    def __init__(self, tag: str = "business", **kwargs):
        super().__init__(**kwargs)
        self.tag = tag
