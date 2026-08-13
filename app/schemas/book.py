"""Book catalog request and response schemas."""

from datetime import datetime
from math import ceil

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.catalog import AuthorResponse, CategoryResponse


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    isbn: str = Field(min_length=1, max_length=32)
    description: str | None = None
    publication_year: int | None = Field(default=None, ge=0, le=9999)
    max_concurrent_borrows: int = Field(default=3, gt=0)
    author_ids: list[int] = Field(default_factory=list)
    category_ids: list[int] = Field(default_factory=list)

    @field_validator("author_ids", "category_ids")
    @classmethod
    def ids_must_be_unique(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("IDs must not contain duplicates")
        return value


class BulkBookItem(BookCreate):
    """One multipart bulk-book entry with an explicit PDF mapping key."""

    file_key: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    isbn: str | None = Field(default=None, min_length=1, max_length=32)
    description: str | None = None
    publication_year: int | None = Field(default=None, ge=0, le=9999)
    max_concurrent_borrows: int | None = Field(default=None, gt=0)
    author_ids: list[int] | None = None
    category_ids: list[int] | None = None

    @field_validator("author_ids", "category_ids")
    @classmethod
    def ids_must_be_unique(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("IDs must not contain duplicates")
        return value


class BookFileMetadata(BaseModel):
    original_filename: str
    mime_type: str
    file_size: int
    file_format: str


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    isbn: str
    description: str | None
    publication_year: int | None
    max_concurrent_borrows: int
    current_borrows_count: int
    available_slots: int
    content_version: int
    is_archived: bool
    has_digital_copy: bool
    digital_file: BookFileMetadata | None
    authors: list[AuthorResponse]
    categories: list[CategoryResponse]
    average_rating: float | None = None
    rating_count: int = 0
    created_at: datetime
    updated_at: datetime


class BulkBookCreate(BaseModel):
    """A validated batch of individually valid book requests."""

    books: list[BulkBookItem] = Field(min_length=1)


class BulkBookResponse(BaseModel):
    created: list[BookResponse]
    count: int


class BookPageResponse(BaseModel):
    """Offset-paginated catalog response."""

    items: list[BookResponse]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(cls, items: list[BookResponse], total: int, page: int, page_size: int) -> "BookPageResponse":
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
        )
