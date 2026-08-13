"""Favorite request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FavoriteCreate(BaseModel):
    """Request to save a book for the authenticated user."""

    book_id: int = Field(gt=0)


class FavoriteResponse(BaseModel):
    """A persisted favorite record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    book_id: int
    created_at: datetime


class FavoriteStatusResponse(BaseModel):
    """The authenticated user's favorite status for one book."""

    book_id: int
    is_favorited: bool
