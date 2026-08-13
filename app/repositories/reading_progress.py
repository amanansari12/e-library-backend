"""Database queries and persistence helpers for private reading progress."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.book import Book
from app.models.borrowing import Borrowing
from app.models.reading_progress import ReadingProgress


class ReadingProgressRepository:
    """Reading-progress persistence without authorization or business policy."""

    def get_book(self, db: Session, book_id: int) -> Book | None:
        return db.get(Book, book_id)

    def has_active_borrowing(self, db: Session, user_id: int, book_id: int) -> bool:
        """Use only the exact ACTIVE borrowing record as mutation authorization."""
        return db.scalar(
            select(Borrowing.id)
            .where(
                Borrowing.user_id == user_id,
                Borrowing.book_id == book_id,
                Borrowing.status == "ACTIVE",
            )
            .limit(1)
        ) is not None

    def get_for_user_and_book(
        self, db: Session, user_id: int, book_id: int
    ) -> ReadingProgress | None:
        return db.scalar(
            select(ReadingProgress).where(
                ReadingProgress.user_id == user_id,
                ReadingProgress.book_id == book_id,
            )
        )

    def create(
        self,
        db: Session,
        *,
        user_id: int,
        book_id: int,
        content_version: int,
        current_page: int,
        total_pages: int,
    ) -> ReadingProgress:
        progress = ReadingProgress(
            user_id=user_id,
            book_id=book_id,
            content_version=content_version,
            current_page=current_page,
            total_pages=total_pages,
        )
        db.add(progress)
        return progress

    def list_for_user(self, db: Session, user_id: int) -> list[ReadingProgress]:
        return list(
            db.scalars(
                select(ReadingProgress)
                .options(selectinload(ReadingProgress.book))
                .where(ReadingProgress.user_id == user_id)
                .order_by(ReadingProgress.last_read_at.desc(), ReadingProgress.id.desc())
            )
        )
