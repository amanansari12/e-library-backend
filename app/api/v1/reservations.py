"""Authenticated reservation waiting-list routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.reservation import ReservationCreate, ReservationResponse
from app.services.reservation import ReservationService


router = APIRouter(prefix="/api/v1/reservations", tags=["reservations"])
reservation_service = ReservationService()


@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: ReservationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ReservationResponse:
    return reservation_service.create(db, current_user, payload)


@router.delete("/{reservation_id}", response_model=ReservationResponse)
def cancel_reservation(
    reservation_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ReservationResponse:
    return reservation_service.cancel(db, current_user, reservation_id)


@router.get("/me", response_model=list[ReservationResponse])
def list_my_reservations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ReservationResponse]:
    return reservation_service.list_for_user(db, current_user)
