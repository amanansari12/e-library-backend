"""CORS middleware configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings


def configure_cors(app: FastAPI, settings: Settings) -> None:
    """Install environment-configured browser CORS handling."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=settings.cors_method_list,
        allow_headers=settings.cors_header_list,
        expose_headers=["X-Request-ID"],
        max_age=600,
    )
