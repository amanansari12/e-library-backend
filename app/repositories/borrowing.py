"""Database queries and persistence for borrowing workflows."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.borrowing import Borrowing
from app.models.user import User


class BorrowingRepository:
    """Persistence operations without borrowing business policy."""

    def lock_book(self, db: Session, book_id: int) -> Book | None:
        """Load a book while holding a row lock until the transaction completes."""
        return db.scalar(select(Book).where(Book.id == book_id).with_for_update())

    def lock_borrowing(self, db: Session, borrowing_id: int) -> Borrowing | None:
        """Load a borrowing while holding a row lock until the transaction completes."""
        return db.scalar(select(Borrowing).where(Borrowing.id == borrowing_id).with_for_update())

    def lock_user(self, db: Session, user_id: int) -> User | None:
        """Serialize one user's concurrent borrowing-limit checks."""
        return db.scalar(select(User).where(User.id == user_id).with_for_update())

    def count_active_for_user(self, db: Session, user_id: int) -> int:
        return int(
            db.scalar(
                select(func.count(Borrowing.id)).where(
                    Borrowing.user_id == user_id,
                    Borrowing.status == "ACTIVE",
                )
            )
            or 0
        )

    def get_active_for_user_and_book(
        self, db: Session, user_id: int, book_id: int
    ) -> Borrowing | None:
        return db.scalar(
            select(Borrowing).where(
                Borrowing.user_id == user_id,
                Borrowing.book_id == book_id,
                Borrowing.status == "ACTIVE",
            )
        )

    def create(
        self, db: Session, *, user_id: int, book_id: int, due_date: datetime
    ) -> Borrowing:
        borrowing = Borrowing(
            user_id=user_id,
            book_id=book_id,
            due_date=due_date,
            status="ACTIVE",
        )
        db.add(borrowing)
        return borrowing

    def list_for_user(self, db: Session, user_id: int, *, active_only: bool) -> list[Borrowing]:
        query = select(Borrowing).where(Borrowing.user_id == user_id)
        if active_only:
            query = query.where(Borrowing.status == "ACTIVE")
        return list(db.scalars(query.order_by(Borrowing.borrowed_at.desc(), Borrowing.id.desc())))
