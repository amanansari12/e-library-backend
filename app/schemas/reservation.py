"""Reservation request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReservationCreate(BaseModel):
    """Request to join a book's waiting list."""

    book_id: int = Field(gt=0)


class ReservationResponse(BaseModel):
    """Reservation state exposed to its owner."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    book_id: int
    position: int
    status: str
    created_at: datetime
    notified_at: datetime | None
    expires_at: datetime | None
