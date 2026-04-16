import time

from fastapi import Request, Response
from starlette.responses import JSONResponse

from app.core.config.logs import get_logger
from app.core.security.anonymize_lib import anonymize_ip


RATE_LIMIT = 600
WINDOW = 60  # secondes
VISITS = {}
logger = get_logger()

async def rate_limiter(request: Request, call_next):
    ip = request.client.host
    anonymized_ip = anonymize_ip(ip)
    now = time.time()

    # Nettoyer les vieux timestamps
    VISITS.setdefault(ip, [])
    VISITS[ip] = [ts for ts in VISITS[ip] if now - ts < WINDOW]

    if len(VISITS[ip]) >= RATE_LIMIT:
        retry_after = int(WINDOW - (now - VISITS[ip][0]))
        logger.warning(
            "MIDDLEWARE:RateLimit",
            f"Rate limit exceeded for IP {anonymized_ip} | ",
            extra=f"Retry after {retry_after} seconds"
        )
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(RATE_LIMIT),
                "X-RateLimit-Remaining": "0",
            },
        )
        
    logger.info(
        "MIDDLEWARE:RateLimit",
        f"Request allowed for IP {anonymized_ip}",
        extra=f"Remaining: {RATE_LIMIT - len(VISITS[ip])}"
    )
    VISITS[ip].append(now)
    response: Response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
    response.headers["X-RateLimit-Remaining"] = str(RATE_LIMIT - len(VISITS[ip]))
    
    return response
