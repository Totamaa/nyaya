from app.core.config.logs import get_logger
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors.exceptions.db import SQLA_ERROR_MAP, DBGenericException
from app.core.errors.exceptions.base import DBException 

logger = get_logger()

async def handle_db_exceptions(request: Request, exc: SQLAlchemyError):
    request_id = getattr(request.state, "request_id", "null")

    exc_class = SQLA_ERROR_MAP.get(type(exc), DBGenericException)
    custom_exc: DBException = exc_class()

    logger.log(
        custom_exc.log_level,
        "EXCEPTION:Database",
        f"{custom_exc.message_log} | {request.method} {request.url.path}",
        extra=f"Req-ID: {request_id}",
        exc=exc
    )

    return JSONResponse(
        status_code=custom_exc.status_code,
        content={"detail": custom_exc.message_front}
    )
