"""Database queries and persistence helpers for the book-summary cache."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.book_summary import BookSummary


class SummaryRepository:
    """Summary cache persistence operations without AI HTTP concerns."""

    def get_book(self, db: Session, book_id: int) -> Book | None:
        return db.scalar(
            select(Book).where(Book.id == book_id).options()
        )

    def get_cached(self, db: Session, book_id: int, content_version: int) -> BookSummary | None:
        return db.scalar(
            select(BookSummary).where(
                BookSummary.book_id == book_id,
                BookSummary.content_version == content_version,
            )
        )

    def create(
        self,
        db: Session,
        *,
        book_id: int,
        content_version: int,
        model: str,
        summary_text: str,
        token_count: int | None,
    ) -> BookSummary:
        summary = BookSummary(
            book_id=book_id,
            content_version=content_version,
            model=model,
            summary_text=summary_text,
            token_count=token_count,
        )
        db.add(summary)
        return summary
