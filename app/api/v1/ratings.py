"""Authenticated rating routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.rating import BookRatingsResponse, RatingCreate, RatingResponse
from app.services.rating import RatingService


router = APIRouter(prefix="/api/v1/ratings", tags=["ratings"])
rating_service = RatingService()


@router.post("", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_rating(
    payload: RatingCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RatingResponse:
    return rating_service.create_or_update(db, current_user, payload)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_rating(
    book_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    rating_service.remove(db, current_user, book_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/books/{book_id}", response_model=BookRatingsResponse)
def list_book_ratings(book_id: int, db: Annotated[Session, Depends(get_db)]) -> BookRatingsResponse:
    return rating_service.list_for_book(db, book_id)


@router.get("/me", response_model=list[RatingResponse])
def list_my_ratings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[RatingResponse]:
    return rating_service.list_for_user(db, current_user)
