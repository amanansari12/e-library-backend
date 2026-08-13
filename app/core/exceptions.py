"""Application error types and HTTP response mapping."""

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """A safe, structured error raised by application services."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    """Serialize known application errors in the documented API shape."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
