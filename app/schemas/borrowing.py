"""Borrowing request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class BorrowingCreate(BaseModel):
    """The selected book and its due date for a new borrowing."""

    book_id: int = Field(gt=0)
    due_date: datetime


class BorrowingResponse(BaseModel):
    """Borrowing data with an API-level, computed status."""

    id: int
    user_id: int
    book_id: int
    borrowed_at: datetime
    due_date: datetime
    returned_at: datetime | None
    status: str
