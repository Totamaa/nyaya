import time
import uuid

from fastapi import Request, Response

from app.core.config.logs import get_logger
from app.core.security.anonymize_lib import anonymize_ip

async def add_global_headers(request: Request, call_next):
    
    logger = get_logger()
    start_time = time.perf_counter()
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    
    ip = anonymize_ip(request.client.host)
    method = request.method
    path = request.url.path
    logger.info(
        "MIDDLEWARE:GlobalHeaders", 
        f"Request received {method} {path}",
        extra= f"IP: {ip} | Req-ID: {request_id}"
    )
    
    response: Response = await call_next(request)
    
    process_time = time.perf_counter() - start_time
    status_code = response.status_code
    
    # general headers
    response.headers["X-Process-Time"] = str(round(process_time, 6))
    response.headers["X-Request-ID"] = request_id

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    logger.info(
        "MIDDLEWARE:GlobalHeaders", 
        f"Response sent {status_code} for {method} {path}",
        f"IP: {ip} | Req-ID: {request_id}"
    )

    return response
