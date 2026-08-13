"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.v1.auth import router as auth_router
from app.api.v1.authors import router as authors_router
from app.api.v1.books import router as books_router
from app.api.v1.borrowings import router as borrowings_router
from app.api.v1.categories import router as categories_router
from app.api.v1.favorites import router as favorites_router
from app.api.v1.health import router as health_router
from app.api.v1.reservations import router as reservations_router
from app.api.v1.users import router as users_router
from app.core.config import get_settings
from app.core.exceptions import AppError, app_error_handler
from app.middleware.cors import configure_cors


def create_app() -> FastAPI:
    """Build the synchronous E-Library API application."""
    settings = get_settings()
    application = FastAPI(
        title="E-Library Backend",
        version="0.1.0",
        debug=settings.debug,
    )
    application.add_exception_handler(AppError, app_error_handler)
    configure_cors(application, settings)
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(books_router)
    application.include_router(borrowings_router)
    application.include_router(reservations_router)
    application.include_router(favorites_router)
    application.include_router(authors_router)
    application.include_router(categories_router)
    return application


app = create_app()
