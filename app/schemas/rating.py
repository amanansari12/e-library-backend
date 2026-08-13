"""Rating request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class RatingCreate(BaseModel):
    """Request to create or update the current user's rating."""

    book_id: int = Field(gt=0)
    score: StrictInt = Field(ge=1, le=5)


class RatingResponse(BaseModel):
    """A single user's rating record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    book_id: int
    score: int
    created_at: datetime
    updated_at: datetime


class BookRatingsResponse(BaseModel):
    """Ratings and SQL-computed aggregate data for one book."""

    book_id: int
    items: list[RatingResponse]
    average_rating: float | None
    rating_count: int
