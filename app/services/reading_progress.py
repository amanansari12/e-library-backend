"""Private, active-borrowing-gated reading-progress workflows."""

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.book import Book
from app.models.reading_progress import ReadingProgress
from app.models.user import User
from app.repositories.reading_progress import ReadingProgressRepository
from app.schemas.reading_progress import ReadingProgressResponse, ReadingProgressUpdate


class ReadingProgressService:
    """Coordinates owner-scoped retrieval and version-aware, idempotent progress updates."""

    def __init__(self, repository: ReadingProgressRepository | None = None) -> None:
        self.repository = repository or ReadingProgressRepository()

    def get_for_book(self, db: Session, user: User, book_id: int) -> ReadingProgressResponse:
        """Return only the current user's historical state, including after return."""
        book = self._require_book(db, book_id)
        progress = self.repository.get_for_user_and_book(db, user.id, book.id)
        if progress is None:
            raise AppError(404, "READING_PROGRESS_NOT_FOUND", "Reading progress not found")
        return self._response(progress, book)

    def set_for_book(
        self, db: Session, user: User, book_id: int, payload: ReadingProgressUpdate
    ) -> ReadingProgressResponse:
        """Set one current state only when the exact user has an ACTIVE borrowing."""
        book = self._require_book(db, book_id)
        self._validate_page_state(payload)
        if book.is_archived:
            raise AppError(409, "BOOK_ARCHIVED", "Archived books cannot have reading progress updated")
        if not self.repository.has_active_borrowing(db, user.id, book.id):
            raise AppError(
                403,
                "ACTIVE_BORROWING_REQUIRED",
                "An active borrowing is required to update reading progress",
            )

        progress = self.repository.get_for_user_and_book(db, user.id, book.id)
        now = datetime.now(UTC)
        if progress is not None:
            progress.content_version = book.content_version
            progress.current_page = payload.current_page
            progress.total_pages = payload.total_pages
            progress.last_read_at = now
            db.commit()
            db.refresh(progress)
            return self._response(progress, book)

        try:
            progress = self.repository.create(
                db,
                user_id=user.id,
                book_id=book.id,
                content_version=book.content_version,
                current_page=payload.current_page,
                total_pages=payload.total_pages,
            )
            progress.last_read_at = now
            db.commit()
            db.refresh(progress)
            return self._response(progress, book)
        except IntegrityError:
            # The unique constraint remains authoritative under simultaneous first PUTs.
            db.rollback()
            progress = self.repository.get_for_user_and_book(db, user.id, book.id)
            if progress is None:
                raise AppError(409, "CONFLICT", "Unable to set reading progress")
            progress.content_version = book.content_version
            progress.current_page = payload.current_page
            progress.total_pages = payload.total_pages
            progress.last_read_at = now
            try:
                db.commit()
                db.refresh(progress)
            except IntegrityError as exc:
                db.rollback()
                raise AppError(409, "CONFLICT", "Unable to set reading progress") from exc
            return self._response(progress, book)

    def list_for_user(self, db: Session, user: User) -> list[ReadingProgressResponse]:
        """Return private Continue Reading state in deterministic recent-read order."""
        return [
            self._response(progress, progress.book)
            for progress in self.repository.list_for_user(db, user.id)
        ]

    def _require_book(self, db: Session, book_id: int) -> Book:
        book = self.repository.get_book(db, book_id)
        if book is None:
            raise AppError(404, "BOOK_NOT_FOUND", "Book not found")
        return book

    @staticmethod
    def _validate_page_state(payload: ReadingProgressUpdate) -> None:
        """Defend the domain boundary if schemas are bypassed in service-level calls."""
        if payload.current_page < 1 or payload.total_pages <= 0 or payload.current_page > payload.total_pages:
            raise AppError(422, "INVALID_READING_PROGRESS", "Page values are invalid")

    @staticmethod
    def _response(progress: ReadingProgress, book: Book) -> ReadingProgressResponse:
        return ReadingProgressResponse(
            book_id=progress.book_id,
            current_page=progress.current_page,
            total_pages=progress.total_pages,
            progress_percent=round((progress.current_page / progress.total_pages) * 100, 2),
            last_read_at=progress.last_read_at,
            content_version=progress.content_version,
            is_stale=progress.content_version != book.content_version,
        )
