"""Application error types and safe, consistent HTTP response mapping."""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.middleware.request_id import REQUEST_ID_HEADER, get_request_id


logger = logging.getLogger("elibrary")
from fastapi.responses import JSONResponse


class AppError(Exception):
    """A safe, structured error raised by application services."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    response = JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )
    if request_id := get_request_id():
        response.headers[REQUEST_ID_HEADER] = request_id
    return response


def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Serialize known application errors in the documented API shape."""
    logger.warning(
        "event=application_error request_id=%s path=%s status_code=%s code=%s",
        get_request_id() or "-", request.url.path, exc.status_code, exc.code,
    )
    return _error_response(exc.status_code, exc.code, exc.message)


def validation_error_handler(request: Request, _: RequestValidationError) -> JSONResponse:
    """Keep malformed input responses stable without echoing sensitive submitted values."""
    logger.info("event=validation_error request_id=%s path=%s", get_request_id() or "-", request.url.path)
    return _error_response(422, "VALIDATION_ERROR", "Request validation failed")


def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Normalize framework 404/405 errors without exposing framework details."""
    code, message = (
        ("NOT_FOUND", "Resource not found")
        if exc.status_code == 404
        else ("METHOD_NOT_ALLOWED", "Method not allowed")
        if exc.status_code == 405
        else ("HTTP_ERROR", "Request could not be completed")
    )
    logger.info(
        "event=http_error request_id=%s path=%s status_code=%s code=%s",
        get_request_id() or "-", request.url.path, exc.status_code, code,
    )
    return _error_response(exc.status_code, code, message)


def integrity_error_handler(request: Request, _: IntegrityError) -> JSONResponse:
    """Avoid leaking database constraint names or SQL through uncaught persistence errors."""
    logger.error("event=database_integrity_error request_id=%s path=%s", get_request_id() or "-", request.url.path)
    return _error_response(409, "CONFLICT", "Request conflicts with current data")


def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a safe 500 response while preserving traceback details only in server logs."""
    logger.exception(
        "event=unexpected_error request_id=%s path=%s",
        get_request_id() or "-", request.url.path, exc_info=exc,
    )
    return _error_response(500, "INTERNAL_SERVER_ERROR", "An unexpected server error occurred")
