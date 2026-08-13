"""Book catalog routes."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.book import BulkBookItem, BulkBookResponse, BookCreate, BookPageResponse, BookResponse, BookUpdate
from app.schemas.reading_progress import ReadingProgressResponse, ReadingProgressUpdate
from app.services.book_file import BookFileService
from app.services.catalog import CatalogService
from app.services.reading_progress import ReadingProgressService


router = APIRouter(prefix="/api/v1/books", tags=["books"])
catalog_service = CatalogService()
book_file_service = BookFileService()
reading_progress_service = ReadingProgressService()


@router.post(
    "/bulk",
    response_model=BulkBookResponse,
    status_code=status.HTTP_201_CREATED,
    description="ADMIN-only atomic multipart creation. Each file_key maps one uploaded PDF to one book.",
)
@limiter.limit(get_settings().bulk_book_upload_rate_limit)
def create_books_bulk(
    request: Request,
    books: Annotated[str, Form(description="JSON array of book metadata with unique file_key values")],
    file_manifest: Annotated[str, Form(description="JSON object mapping each file_key to an uploaded filename")],
    files: Annotated[list[UploadFile], File(description="One PDF for each manifest entry")],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> BulkBookResponse:
    """Create an atomic multipart batch where every book has a mapped PDF."""
    try:
        payloads = TypeAdapter(list[BulkBookItem]).validate_python(json.loads(books))
        manifest = json.loads(file_manifest)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AppError(422, "INVALID_BULK_BOOK_PAYLOAD", "Bulk book metadata or file manifest is invalid") from exc
    if not isinstance(manifest, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in manifest.items()
    ):
        raise AppError(422, "INVALID_FILE_MAPPING", "file_manifest must map file keys to uploaded filenames")
    uploaded_by_name = {upload.filename: upload for upload in files}
    if len(uploaded_by_name) != len(files) or any(not upload.filename for upload in files):
        raise AppError(422, "INVALID_FILE_MAPPING", "Uploaded filenames must be present and unique within a batch")
    if len(set(manifest.values())) != len(manifest) or set(manifest.values()) != set(uploaded_by_name):
        raise AppError(422, "INVALID_FILE_MAPPING", "file_manifest must reference every uploaded PDF exactly once")
    uploads_by_key = {file_key: uploaded_by_name[filename] for file_key, filename in manifest.items()}
    return catalog_service.create_books_bulk_with_files(db, payloads, uploads_by_key, book_file_service)


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


@router.post(
    "",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    description="ADMIN-only multipart creation of a catalog record and its required validated PDF.",
)
@limiter.limit(get_settings().book_create_rate_limit)
def create_book(
    request: Request,
    title: Annotated[str, Form(min_length=1, max_length=500)],
    isbn: Annotated[str, Form(min_length=1, max_length=32)],
    file: Annotated[UploadFile, File()],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
    description: Annotated[str | None, Form()] = None,
    publication_year: Annotated[int | None, Form(ge=0, le=9999)] = None,
    max_concurrent_borrows: Annotated[int, Form(gt=0)] = 3,
    author_ids: Annotated[list[int], Form()] = [],
    category_ids: Annotated[list[int], Form()] = [],
) -> BookResponse:
    payload = BookCreate(
        title=title,
        isbn=isbn,
        description=description,
        publication_year=publication_year,
        max_concurrent_borrows=max_concurrent_borrows,
        author_ids=author_ids,
        category_ids=category_ids,
    )
    return catalog_service.create_book_with_file(db, payload, file, book_file_service)


@router.post(
    "/{book_id}/file",
    response_model=BookResponse,
    description="ADMIN-only replacement of an unarchived book's validated PDF.",
)
@limiter.limit(get_settings().book_file_replace_rate_limit)
def replace_book_file(
    request: Request,
    book_id: int,
    file: Annotated[UploadFile, File()],
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[object, Depends(require_admin)],
) -> BookResponse:
    book = catalog_service._require_book(db, book_id)
    book_file_service.replace(db, book, file)
    return catalog_service.get_book(db, book_id)


@router.get(
    "/{book_id}/file",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "The active PDF binary for an authenticated active borrower.",
            "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
def get_book_file(
    book_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    book_file, content = book_file_service.stream_for_active_borrower(db, current_user, book_id)
    return StreamingResponse(
        content,
        media_type=book_file.mime_type,
        headers={"Content-Disposition": f'inline; filename="{book_file.original_filename}"'},
    )


@router.get(
    "/{book_id}/progress",
    response_model=ReadingProgressResponse,
    description="Return only the authenticated user's stored progress, including historical progress after return.",
)
def get_reading_progress(
    book_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ReadingProgressResponse:
    return reading_progress_service.get_for_book(db, current_user, book_id)


@router.put(
    "/{book_id}/progress",
    response_model=ReadingProgressResponse,
    description="Set the authenticated user's page state for the current book version. An ACTIVE borrowing is required.",
)
def set_reading_progress(
    book_id: int,
    payload: ReadingProgressUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ReadingProgressResponse:
    return reading_progress_service.set_for_book(db, current_user, book_id, payload)


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Annotated[Session, Depends(get_db)]) -> BookResponse:
    return catalog_service.get_book(db, book_id)


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
