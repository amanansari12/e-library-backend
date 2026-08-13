"""Request and response schemas for private reading-progress state."""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class ReadingProgressUpdate(BaseModel):
    """Set the authenticated user's page state for the current book version."""

    current_page: int = Field(ge=1)
    total_pages: int = Field(gt=0)

    @model_validator(mode="after")
    def current_page_must_be_within_total(self) -> "ReadingProgressUpdate":
        if self.current_page > self.total_pages:
            raise ValueError("current_page must not exceed total_pages")
        return self


class ReadingProgressResponse(BaseModel):
    """Safe, derived reading state returned only to its owner."""

    book_id: int
    current_page: int
    total_pages: int
    progress_percent: float
    last_read_at: datetime
    content_version: int
    is_stale: bool
