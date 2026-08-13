"""Private Continue Reading routes for authenticated digital-book borrowers."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.reading_progress import ReadingProgressResponse
from app.services.reading_progress import ReadingProgressService


router = APIRouter(prefix="/api/v1/reading-progress", tags=["reading progress"])
reading_progress_service = ReadingProgressService()


@router.get(
    "/me",
    response_model=list[ReadingProgressResponse],
    description="List only the authenticated user's saved progress, newest last-read state first, for Continue Reading.",
)
def list_my_reading_progress(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ReadingProgressResponse]:
    return reading_progress_service.list_for_user(db, current_user)
