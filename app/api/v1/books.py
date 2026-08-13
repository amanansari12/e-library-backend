"""Book catalog routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.core.exceptions import AppError
from app.schemas.book import BookCreate, BookPageResponse, BookResponse, BookUpdate
from app.services.catalog import CatalogService


router = APIRouter(prefix="/api/v1/books", tags=["books"])
catalog_service = CatalogService()


@router.get("", response_model=BookPageResponse)
def list_books(
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(max_length=200)] = None,
    author_id: int | None = None,
    category_id: int | None = None,
    available: bool | None = None,
    year_from: Annotated[int | None, Query(ge=0, le=9999)] = None,
    year_to: Annotated[int | None, Query(ge=0, le=9999)] = None,
    sort_by: Annotated[str, Query(pattern="^(title|publication_year|created_at)$")] = "title",
    sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "asc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BookPageResponse:
    """Search and filter active catalog books with offset pagination."""
    if year_from is not None and year_to is not None and year_from > year_to:
        raise AppError(422, "INVALID_YEAR_RANGE", "year_from must be less than or equal to year_to")
    return catalog_service.list_books(
        db,
        q=q,
        author_id=author_id,
        category_id=category_id,
        available=available,
        year_from=year_from,
        year_to=year_to,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Annotated[Session, Depends(get_db)]) -> BookResponse:
    return catalog_service.get_book(db, book_id)


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(
    payload: BookCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> BookResponse:
    return catalog_service.create_book(db, payload)


@router.patch("/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    payload: BookUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> BookResponse:
    return catalog_service.update_book(db, book_id, payload)


@router.post("/{book_id}/archive", response_model=BookResponse)
def archive_book(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> BookResponse:
    return catalog_service.archive_book(db, book_id)


@router.post("/{book_id}/restore", response_model=BookResponse)
def restore_book(
    book_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> BookResponse:
    return catalog_service.restore_book(db, book_id)
