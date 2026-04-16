from app.core.config.logs import get_logger
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.errors.exceptions.base import BusinessException

logger = get_logger()

async def handle_business_exceptions(request: Request, exc: BusinessException):
    request_id = getattr(request.state, "request_id", "null")

    logger.log(
        exc.log_level,
        f"EXCEPTION:{exc.tag}",
        f"{exc.message_log} | {request.method} {request.url.path}",
        extra=f"Req-ID: {request_id}",
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message_front}
    )
