"""Request and safe response schemas for optional written book reviews."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class _ReviewText(BaseModel):
    review_text: str = Field(min_length=1, max_length=2000)

    @field_validator("review_text")
    @classmethod
    def review_text_must_not_be_whitespace_only(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Review text must not be blank")
        return value


class ReviewCreate(_ReviewText):
    """Create one review for a book the current user has borrowed."""

    book_id: int = Field(gt=0)


class ReviewUpdate(_ReviewText):
    """Replace the text of the current user's existing review."""


class ReviewAuthorResponse(BaseModel):
    """Public display information that excludes account and security fields."""

    id: int
    username: str
    full_name: str


class ReviewResponse(BaseModel):
    """One review with a safe reviewer display profile."""

    id: int
    user_id: int
    book_id: int
    review_text: str
    created_at: datetime
    updated_at: datetime
    user: ReviewAuthorResponse
