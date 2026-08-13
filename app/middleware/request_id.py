"""Request correlation middleware without distributed tracing dependencies."""

import logging
import re
from contextvars import ContextVar, Token
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("elibrary")


def get_request_id() -> str | None:
    """Return the current request ID when called during request handling."""
    return _request_id.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Accept safe correlation IDs or generate a UUID, then return it in every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        provided_id = request.headers.get(REQUEST_ID_HEADER)
        request_id = provided_id if provided_id and _VALID_REQUEST_ID.fullmatch(provided_id) else uuid4().hex
        request.state.request_id = request_id
        token: Token[str | None] = _request_id.set(request_id)
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "event=unexpected_error request_id=%s path=%s",
                request_id,
                request.url.path,
            )
            response = JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected server error occurred",
                    }
                },
            )
        finally:
            _request_id.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "event=request_completed request_id=%s method=%s path=%s status_code=%s duration_ms=%d",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            int((perf_counter() - started_at) * 1000),
        )
        return response
