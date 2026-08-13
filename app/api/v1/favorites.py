"""Authenticated favorite routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.favorite import FavoriteCreate, FavoriteResponse, FavoriteStatusResponse
from app.services.favorite import FavoriteService


router = APIRouter(prefix="/api/v1/favorites", tags=["favorites"])
favorite_service = FavoriteService()


@router.post("", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
def create_favorite(
    payload: FavoriteCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FavoriteResponse:
    return favorite_service.create(db, current_user, payload)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    book_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    favorite_service.remove(db, current_user, book_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=list[FavoriteResponse])
def list_my_favorites(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[FavoriteResponse]:
    return favorite_service.list_for_user(db, current_user)


@router.get("/check/{book_id}", response_model=FavoriteStatusResponse)
def check_favorite_status(
    book_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FavoriteStatusResponse:
    return favorite_service.status_for_user(db, current_user, book_id)
