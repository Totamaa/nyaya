import logging
from fastapi import status
from app.core.errors.exceptions.base import DBException
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
    MultipleResultsFound,
    NoResultFound,
    InvalidRequestError,
)

class DBIntegrityException(DBException):
    def __init__(self):
        super().__init__(
            message_front="A database integrity error occurred.",
            message_log="IntegrityError raised (constraint violation, duplicate key...).",
            status_code=status.HTTP_400_BAD_REQUEST,
            log_level=logging.ERROR,
        )

class DBOperationalException(DBException):
    def __init__(self):
        super().__init__(
            message_front="A database operational error occurred.",
            message_log="OperationalError raised (connection issues, locks...).",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            log_level=logging.CRITICAL,
        )

class DBGenericException(DBException):
    def __init__(self):
        super().__init__(
            message_front="A database error occurred.",
            message_log="Generic SQLAlchemyError raised.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            log_level=logging.ERROR,
        )

class DBNoResultException(DBException):
    def __init__(self):
        super().__init__(
            message_front="Resource not found.",
            message_log="NoResultFound raised (query returned nothing).",
            status_code=status.HTTP_404_NOT_FOUND,
            log_level=logging.WARNING,
        )

class DBMultipleResultsException(DBException):
    def __init__(self):
        super().__init__(
            message_front="Conflict: multiple resources found.",
            message_log="MultipleResultsFound raised (expected one, got many).",
            status_code=status.HTTP_409_CONFLICT,
            log_level=logging.ERROR,
        )
        
class DBInvalidRequestException(DBException):
    def __init__(self):
        super().__init__(
            message_front="An internal server error occurred while processing the request.",
            message_log="InvalidRequestError raised (Indicates a server-side code bug, e.g., lazy-load on a 'raiseload' attribute, or a closed session).",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            log_level=logging.ERROR,
        )


SQLA_ERROR_MAP = {
    IntegrityError: DBIntegrityException,
    OperationalError: DBOperationalException,
    NoResultFound: DBNoResultException,
    MultipleResultsFound: DBMultipleResultsException,
    SQLAlchemyError: DBGenericException,
    InvalidRequestError: DBInvalidRequestException,
}
