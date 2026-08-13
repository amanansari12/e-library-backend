"""Authenticated standard AI book-summary routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.summary import BookSummaryResponse
from app.services.summary import SummaryService


router = APIRouter(prefix="/api/v1/books", tags=["summaries"])
summary_service = SummaryService()


@router.post("/{book_id}/summary", response_model=BookSummaryResponse)
@limiter.limit(get_settings().ai_summary_rate_limit)
def generate_summary(
    request: Request,
    book_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    force_regenerate: bool = Query(default=False),
) -> BookSummaryResponse:
    """Generate or reuse the one standard summary for a book version."""
    return summary_service.generate(db, book_id, force_regenerate=force_regenerate)


@router.get("/{book_id}/summary", response_model=BookSummaryResponse)
def get_summary(
    book_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BookSummaryResponse:
    """Return the cached summary for the book's current content version."""
    return summary_service.get_cached(db, book_id)
