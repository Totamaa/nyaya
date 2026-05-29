import time

import redis.asyncio as aioredis
from fastapi import Request, Response
from starlette.responses import JSONResponse

from app.core.config.logs import get_logger
from app.core.config.redis import REDIS_URL
from app.core.security.anonymize_lib import anonymize_ip


RATE_LIMIT = 600
WINDOW = 60  # secondes
_FALLBACK: dict[str, list[float]] = {}
logger = get_logger()

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def _check_redis(key: str, now: float) -> tuple[bool, int]:
    """
    Sliding window via sorted set.
    Returns (limit_exceeded, remaining).
    """
    client = get_redis()
    window_start = now - WINDOW
    pipe = client.pipeline()
    pipe.zremrangebyscore(key, "-inf", window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, WINDOW)
    results = await pipe.execute()
    count: int = results[2]
    exceeded = count > RATE_LIMIT
    remaining = max(0, RATE_LIMIT - count)
    return exceeded, remaining


async def _check_fallback(ip: str, now: float) -> tuple[bool, int]:
    """In-memory fallback — single process only."""
    _FALLBACK.setdefault(ip, [])
    _FALLBACK[ip] = [ts for ts in _FALLBACK[ip] if now - ts < WINDOW]
    count = len(_FALLBACK[ip])
    if count >= RATE_LIMIT:
        return True, 0
    _FALLBACK[ip].append(now)
    return False, RATE_LIMIT - count - 1


RATE_LIMITED_PATHS = {"/health"}


async def rate_limiter(request: Request, call_next):
    if request.url.path not in RATE_LIMITED_PATHS:
        return await call_next(request)

    ip = request.client.host
    anonymized_ip = anonymize_ip(ip)
    now = time.time()
    key = f"rate_limit:{ip}"

    try:
        exceeded, remaining = await _check_redis(key, now)
    except Exception as e:
        logger.warning("MIDDLEWARE:RateLimit", f"Redis unavailable, falling back to memory: {e}")
        exceeded, remaining = await _check_fallback(ip, now)

    if exceeded:
        retry_after = WINDOW
        logger.warning(
            "MIDDLEWARE:RateLimit",
            f"Rate limit exceeded for IP {anonymized_ip}",
            extra=f"Retry after {retry_after} seconds",
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
        extra=f"Remaining: {remaining}",
    )
    response: Response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response
