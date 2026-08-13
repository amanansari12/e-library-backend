"""Borrowing business workflows and transactional availability control."""

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.borrowing import Borrowing
from app.models.user import User
from app.repositories.borrowing import BorrowingRepository
from app.schemas.borrowing import BorrowingCreate, BorrowingResponse
from app.services.reservation import ReservationService


class BorrowingService:
    """Coordinates borrowing rules while keeping each workflow transactional."""

    MAX_ACTIVE_BORROWINGS = 5

    def __init__(
        self,
        repository: BorrowingRepository | None = None,
        reservation_service: ReservationService | None = None,
    ) -> None:
        self.repository = repository or BorrowingRepository()
        self.reservation_service = reservation_service or ReservationService()

    def borrow(self, db: Session, user: User, payload: BorrowingCreate) -> BorrowingResponse:
        """Create a borrowing and consume one concurrent slot atomically."""
        try:
            book = self.repository.lock_book(db, payload.book_id)
            if book is None:
                raise AppError(404, "BOOK_NOT_FOUND", "Book not found")
            if book.is_archived:
                raise AppError(409, "BOOK_ARCHIVED", "Archived books cannot be borrowed")
            self.reservation_service.reconcile_locked_book(db, book, datetime.now(UTC))
            locked_user = self.repository.lock_user(db, user.id)
            if locked_user is None:
                raise AppError(401, "INVALID_TOKEN", "The authentication token is invalid or expired")
            if self.repository.count_active_for_user(db, locked_user.id) >= self.MAX_ACTIVE_BORROWINGS:
                raise AppError(409, "BORROW_LIMIT_EXCEEDED", "A user may have at most 5 active borrowings")
            if self.repository.get_active_for_user_and_book(db, locked_user.id, book.id) is not None:
                raise AppError(409, "ALREADY_BORROWING", "You already have an active borrowing for this book")
            if book.current_borrows_count >= book.max_concurrent_borrows:
                raise AppError(409, "BOOK_NOT_AVAILABLE", "This book has no available borrowing slots")
            if not self.reservation_service.can_borrow_locked_book(db, locked_user.id, book.id):
                raise AppError(409, "BOOK_NOT_AVAILABLE", "This book's available slot is reserved for another user")

            borrowing = self.repository.create(
                db, user_id=locked_user.id, book_id=book.id, due_date=payload.due_date
            )
            book.current_borrows_count += 1
            self.reservation_service.fulfill_ready_reservation(db, locked_user.id, book.id)
            db.commit()
            db.refresh(borrowing)
            return self._response(borrowing)
        except AppError:
            db.rollback()
            raise
        except IntegrityError as exc:
            db.rollback()
            raise AppError(409, "CONFLICT", "Unable to create borrowing") from exc

    def return_borrowing(
        self, db: Session, user: User, borrowing_id: int
    ) -> BorrowingResponse:
        """Return an owned active borrowing and release its slot atomically."""
        try:
            borrowing = self.repository.lock_borrowing(db, borrowing_id)
            if borrowing is None:
                raise AppError(404, "BORROWING_NOT_FOUND", "Borrowing not found")
            if borrowing.user_id != user.id:
                raise AppError(403, "FORBIDDEN", "You may only return your own borrowings")
            if borrowing.status != "ACTIVE":
                raise AppError(409, "BORROWING_ALREADY_RETURNED", "This borrowing has already been returned")

            book = self.repository.lock_book(db, borrowing.book_id)
            if book is None:
                raise AppError(404, "BOOK_NOT_FOUND", "Book not found")
            borrowing.status = "RETURNED"
            borrowing.returned_at = datetime.now(UTC)
            if book.current_borrows_count <= 0:
                raise AppError(409, "BORROW_COUNT_INVALID", "Book borrowing count is inconsistent")
            book.current_borrows_count -= 1
            self.reservation_service.reconcile_locked_book(db, book, datetime.now(UTC))
            db.commit()
            db.refresh(borrowing)
            return self._response(borrowing)
        except AppError:
            db.rollback()
            raise
        except IntegrityError as exc:
            db.rollback()
            raise AppError(409, "CONFLICT", "Unable to return borrowing") from exc

    def list_for_user(self, db: Session, user: User, *, active_only: bool) -> list[BorrowingResponse]:
        return [
            self._response(borrowing)
            for borrowing in self.repository.list_for_user(db, user.id, active_only=active_only)
        ]

    @staticmethod
    def _response(borrowing: Borrowing) -> BorrowingResponse:
        status = borrowing.status
        if status == "ACTIVE" and borrowing.due_date < datetime.now(UTC):
            status = "OVERDUE"
        return BorrowingResponse(
            id=borrowing.id,
            user_id=borrowing.user_id,
            book_id=borrowing.book_id,
            borrowed_at=borrowing.borrowed_at,
            due_date=borrowing.due_date,
            returned_at=borrowing.returned_at,
            status=status,
        )
