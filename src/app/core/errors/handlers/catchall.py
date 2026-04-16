from app.core.config.logs import get_logger
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = get_logger()

async def handle_generic_exceptions(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "null")

    logger.critical(
        tag="EXCEPTION:generic",
        message=f"Unexpected exception | {request.method} {request.url.path}",
        extra=f"Req-ID: {request_id}",
        exc=exc
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )
