"""Optional written-review routes for authenticated library users."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate
from app.services.review import ReviewService


router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])
review_service = ReviewService()


@router.post(
    "",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    description="Create an optional review after the current user has borrowed the book at least once. One review per user and book.",
)
@limiter.limit(get_settings().review_create_rate_limit)
def create_review(
    request: Request,
    payload: ReviewCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ReviewResponse:
    return review_service.create(db, current_user, payload)


@router.get(
    "/books/{book_id}",
    response_model=list[ReviewResponse],
    description="List written reviews for an existing book using safe reviewer display information.",
)
def list_book_reviews(book_id: int, db: Annotated[Session, Depends(get_db)]) -> list[ReviewResponse]:
    return review_service.list_for_book(db, book_id)


@router.get(
    "/me",
    response_model=list[ReviewResponse],
    description="List only the authenticated user's reviews.",
)
def list_my_reviews(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ReviewResponse]:
    return review_service.list_for_user(db, current_user)


@router.patch(
    "/{review_id}",
    response_model=ReviewResponse,
    description="Update the authenticated owner's review. Borrowing again is not required.",
)
def update_review(
    review_id: int,
    payload: ReviewUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ReviewResponse:
    return review_service.update(db, current_user, review_id, payload)


@router.delete(
    "/{review_id}", status_code=status.HTTP_204_NO_CONTENT,
    description="Delete the authenticated owner's review.",
)
def delete_review(
    review_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    review_service.remove(db, current_user, review_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
