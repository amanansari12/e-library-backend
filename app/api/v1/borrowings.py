"""Authenticated borrowing routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.borrowing import BorrowingCreate, BorrowingResponse
from app.services.borrowing import BorrowingService


router = APIRouter(prefix="/api/v1/borrowings", tags=["borrowings"])
borrowing_service = BorrowingService()


@router.post("", response_model=BorrowingResponse, status_code=status.HTTP_201_CREATED)
def create_borrowing(
    payload: BorrowingCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BorrowingResponse:
    return borrowing_service.borrow(db, current_user, payload)


@router.post("/{borrowing_id}/return", response_model=BorrowingResponse)
def return_borrowing(
    borrowing_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BorrowingResponse:
    return borrowing_service.return_borrowing(db, current_user, borrowing_id)


@router.get("/me", response_model=list[BorrowingResponse])
def list_my_borrowings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[BorrowingResponse]:
    return borrowing_service.list_for_user(db, current_user, active_only=False)


@router.get("/me/active", response_model=list[BorrowingResponse])
def list_my_active_borrowings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[BorrowingResponse]:
    return borrowing_service.list_for_user(db, current_user, active_only=True)
