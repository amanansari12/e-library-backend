"""Reservation waiting-list workflows and promotion rules."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.book import Book
from app.models.reservation import Reservation
from app.models.user import User
from app.repositories.reservation import ReservationRepository
from app.schemas.reservation import ReservationCreate, ReservationResponse


class ReservationService:
    """Coordinates transactional reservation and queue lifecycle workflows."""

    MAX_ACTIVE_RESERVATIONS = 3
    READY_DURATION = timedelta(hours=48)

    def __init__(self, repository: ReservationRepository | None = None) -> None:
        self.repository = repository or ReservationRepository()

    def create(self, db: Session, user: User, payload: ReservationCreate) -> ReservationResponse:
        """Join an unavailable book's waiting list within one transaction."""
        try:
            book = self.repository.lock_book(db, payload.book_id)
            if book is None:
                raise AppError(404, "BOOK_NOT_FOUND", "Book not found")
            if book.is_archived:
                raise AppError(409, "BOOK_ARCHIVED", "Archived books cannot be reserved")

            now = datetime.now(UTC)
            self.reconcile_locked_book(db, book, now)
            locked_user = self.repository.lock_user(db, user.id)
            if locked_user is None:
                raise AppError(401, "INVALID_TOKEN", "The authentication token is invalid or expired")
            if self.repository.has_active_borrowing(db, locked_user.id, book.id):
                raise AppError(409, "ALREADY_BORROWING", "You already have an active borrowing for this book")
            if self.repository.get_active_for_user_and_book(db, locked_user.id, book.id) is not None:
                raise AppError(409, "DUPLICATE_RESERVATION", "You already have an active reservation for this book")
            if book.current_borrows_count < book.max_concurrent_borrows:
                raise AppError(409, "BOOK_AVAILABLE", "This book still has an available borrowing slot")
            if self.repository.count_active_for_user(db, locked_user.id) >= self.MAX_ACTIVE_RESERVATIONS:
                raise AppError(409, "RESERVATION_LIMIT_EXCEEDED", "A user may have at most 3 active reservations")

            reservation = self.repository.create(
                db,
                user_id=locked_user.id,
                book_id=book.id,
                position=self.repository.next_position(db, book.id),
            )
            db.commit()
            db.refresh(reservation)
            return ReservationResponse.model_validate(reservation)
        except AppError:
            db.rollback()
            raise
        except IntegrityError as exc:
            db.rollback()
            raise AppError(409, "DUPLICATE_RESERVATION", "You already have an active reservation for this book") from exc

    def cancel(self, db: Session, user: User, reservation_id: int) -> ReservationResponse:
        """Cancel an owned active reservation and reconcile any open slot."""
        try:
            reservation = self.repository.lock_reservation(db, reservation_id)
            if reservation is None:
                raise AppError(404, "RESERVATION_NOT_FOUND", "Reservation not found")
            if reservation.user_id != user.id:
                raise AppError(403, "FORBIDDEN", "You may only cancel your own reservations")
            book = self.repository.lock_book(db, reservation.book_id)
            if book is None:
                raise AppError(404, "BOOK_NOT_FOUND", "Book not found")

            self.reconcile_locked_book(db, book, datetime.now(UTC))
            if reservation.status not in {"PENDING", "READY"}:
                raise AppError(409, "RESERVATION_NOT_CANCELLABLE", "This reservation is no longer active")
            reservation.status = "CANCELLED"
            self.reconcile_locked_book(db, book, datetime.now(UTC))
            db.commit()
            db.refresh(reservation)
            return ReservationResponse.model_validate(reservation)
        except AppError:
            db.rollback()
            raise
        except IntegrityError as exc:
            db.rollback()
            raise AppError(409, "CONFLICT", "Unable to cancel reservation") from exc

    def list_for_user(self, db: Session, user: User) -> list[ReservationResponse]:
        """Return the current user's reservations after lazily expiring READY records."""
        now = datetime.now(UTC)
        expired_book_ids = self.repository.expired_ready_book_ids_for_user(db, user.id, now)
        if expired_book_ids:
            try:
                for book_id in expired_book_ids:
                    book = self.repository.lock_book(db, book_id)
                    if book is not None:
                        self.reconcile_locked_book(db, book, now)
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise AppError(409, "CONFLICT", "Unable to refresh reservations") from exc
        return [
            ReservationResponse.model_validate(reservation)
            for reservation in self.repository.list_for_user(db, user.id)
        ]

    def reconcile_locked_book(self, db: Session, book: Book, now: datetime) -> None:
        """Expire stale READY records and promote pending records for open slots.

        The caller must already hold the book row lock.  This lets return, cancellation,
        listing, and creation share the same queue transition rules transactionally.
        """
        self.repository.expire_ready_for_book(db, book.id, now)
        if book.is_archived:
            return
        available_slots = book.max_concurrent_borrows - book.current_borrows_count
        ready_count = self.repository.count_ready_for_book(db, book.id)
        while ready_count < available_slots:
            next_reservation = self.repository.earliest_pending_for_book(db, book.id)
            if next_reservation is None:
                break
            next_reservation.status = "READY"
            next_reservation.notified_at = now
            next_reservation.expires_at = now + self.READY_DURATION
            ready_count += 1

    def fulfill_ready_reservation(self, db: Session, user_id: int, book_id: int) -> None:
        """Mark a selected user's READY reservation fulfilled when they borrow."""
        reservation = self.repository.get_ready_for_user_and_book(db, user_id, book_id)
        if reservation is not None:
            reservation.status = "FULFILLED"

    def can_borrow_locked_book(self, db: Session, user_id: int, book_id: int) -> bool:
        """Ensure a READY reservation's promoted slot stays with its owner."""
        if not self.repository.has_ready_for_book(db, book_id):
            return True
        return self.repository.get_ready_for_user_and_book(db, user_id, book_id) is not None
