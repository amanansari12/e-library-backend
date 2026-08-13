"""Shared SlowAPI configuration for externally metered endpoints."""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


limiter = Limiter(key_func=get_remote_address)


def rate_limit_error_handler(_: Request, __: RateLimitExceeded) -> JSONResponse:
    """Return rate-limit failures in the application's standard error shape."""
    response = JSONResponse(
        status_code=429,
        content={"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests"}},
    )
    from app.middleware.request_id import REQUEST_ID_HEADER, get_request_id

    if request_id := get_request_id():
        response.headers[REQUEST_ID_HEADER] = request_id
    return response
