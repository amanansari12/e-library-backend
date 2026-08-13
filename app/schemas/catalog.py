"""Shared author and category response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuthorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    biography: str | None = None


class AuthorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    biography: str | None = None


class AuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    biography: str | None
    created_at: datetime


class BulkAuthorCreate(BaseModel):
    """A validated batch of individually valid author requests."""

    authors: list[AuthorCreate] = Field(min_length=1)


class BulkAuthorResponse(BaseModel):
    created: list[AuthorResponse]
    count: int


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime


class BulkCategoryCreate(BaseModel):
    """A validated batch of individually valid category requests."""

    categories: list[CategoryCreate] = Field(min_length=1)


class BulkCategoryResponse(BaseModel):
    created: list[CategoryResponse]
    count: int
