"""Persistence queries for digital-book file metadata."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.book_file import BookFile


class BookFileRepository:
    """Data access helpers with no storage or authorization policy."""

    def get_active(self, db: Session, book_id: int) -> BookFile | None:
        return db.scalar(
            select(BookFile).where(BookFile.book_id == book_id, BookFile.is_active.is_(True))
        )

    def has_active(self, db: Session, book_id: int) -> bool:
        return self.get_active(db, book_id) is not None
