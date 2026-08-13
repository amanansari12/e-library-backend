"""AI book-summary response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class BookSummaryResponse(BaseModel):
    """The single standard cached summary for a book content version."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    content_version: int
    model: str
    summary_text: str
    token_count: int | None
    created_at: datetime


class AIProviderResponse(BaseModel):
    """Safe provider metadata returned by health and usage endpoints."""

    data: dict[str, Any]
