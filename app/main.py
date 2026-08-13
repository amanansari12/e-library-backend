"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from sqlalchemy.exc import IntegrityError
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.admin import router as admin_router
from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.authors import router as authors_router
from app.api.v1.books import router as books_router
from app.api.v1.borrowings import router as borrowings_router
from app.api.v1.categories import router as categories_router
from app.api.v1.favorites import router as favorites_router
from app.api.v1.health import router as health_router
from app.api.v1.reservations import router as reservations_router
from app.api.v1.ratings import router as ratings_router
from app.api.v1.reading_progress import router as reading_progress_router
from app.api.v1.reviews import router as reviews_router
from app.api.v1.summaries import router as summaries_router
from app.api.v1.users import router as users_router
from app.core.config import get_settings
from app.core.exceptions import (
    AppError,
    app_error_handler,
    http_error_handler,
    integrity_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from app.core.rate_limit import limiter, rate_limit_error_handler
from app.middleware.cors import configure_cors
from app.middleware.request_id import RequestIdMiddleware


def create_app() -> FastAPI:
    """Build the synchronous E-Library API application."""
    settings = get_settings()
    application = FastAPI(
        title="E-Library Backend",
        version="0.1.0",
        debug=settings.debug,
    )
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_error_handler)
    application.add_exception_handler(IntegrityError, integrity_error_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)
    configure_cors(application, settings)
    application.add_middleware(RequestIdMiddleware)
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(books_router)
    application.include_router(ai_router)
    application.include_router(summaries_router)
    application.include_router(borrowings_router)
    application.include_router(reservations_router)
    application.include_router(favorites_router)
    application.include_router(ratings_router)
    application.include_router(reading_progress_router)
    application.include_router(reviews_router)
    application.include_router(authors_router)
    application.include_router(categories_router)
    application.include_router(admin_router)

    def custom_openapi() -> dict:
        """Normalize the multipart bulk-file schema for Swagger UI file controls."""
        if application.openapi_schema is not None:
            return application.openapi_schema
        schema = get_openapi(
            title=application.title,
            version=application.version,
            routes=application.routes,
        )
        request_schema = schema["paths"]["/api/v1/books/bulk"]["post"]["requestBody"]["content"][
            "multipart/form-data"
        ]["schema"]
        component_name = request_schema["$ref"].rsplit("/", 1)[-1]
        file_items = schema["components"]["schemas"][component_name]["properties"]["files"]["items"]
        file_items.pop("contentMediaType", None)
        file_items["type"] = "string"
        file_items["format"] = "binary"
        application.openapi_schema = schema
        return schema

    application.openapi = custom_openapi
    return application


app = create_app()
