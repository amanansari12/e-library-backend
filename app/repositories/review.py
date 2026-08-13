"""Database queries and persistence helpers for written book reviews."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.book import Book
from app.models.book_review import BookReview
from app.models.borrowing import Borrowing


class ReviewRepository:
    """Review persistence and borrowing-history queries without policy decisions."""

    def get_book(self, db: Session, book_id: int) -> Book | None:
        return db.get(Book, book_id)

    def has_borrowed_book(self, db: Session, user_id: int, book_id: int) -> bool:
        """Check only the borrowings history for this exact user/book pair."""
        return db.scalar(
            select(Borrowing.id)
            .where(Borrowing.user_id == user_id, Borrowing.book_id == book_id)
            .limit(1)
        ) is not None

    def get_for_user_and_book(self, db: Session, user_id: int, book_id: int) -> BookReview | None:
        return db.scalar(
            select(BookReview).where(BookReview.user_id == user_id, BookReview.book_id == book_id)
        )

    def get(self, db: Session, review_id: int) -> BookReview | None:
        return db.get(BookReview, review_id)

    def create(self, db: Session, *, user_id: int, book_id: int, review_text: str) -> BookReview:
        review = BookReview(user_id=user_id, book_id=book_id, review_text=review_text)
        db.add(review)
        return review

    def delete(self, db: Session, review: BookReview) -> None:
        db.delete(review)

    def list_for_book(self, db: Session, book_id: int) -> list[BookReview]:
        return list(
            db.scalars(
                select(BookReview)
                .options(selectinload(BookReview.user))
                .where(BookReview.book_id == book_id)
                .order_by(BookReview.created_at.desc(), BookReview.id.desc())
            )
        )

    def list_for_user(self, db: Session, user_id: int) -> list[BookReview]:
        return list(
            db.scalars(
                select(BookReview)
                .options(selectinload(BookReview.user))
                .where(BookReview.user_id == user_id)
                .order_by(BookReview.created_at.desc(), BookReview.id.desc())
            )
        )
