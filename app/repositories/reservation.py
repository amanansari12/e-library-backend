"""Database queries and persistence helpers for reservation workflows."""

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.borrowing import Borrowing
from app.models.reservation import Reservation
from app.models.user import User


class ReservationRepository:
    """Reservation persistence operations without business policy."""

    def lock_book(self, db: Session, book_id: int) -> Book | None:
        return db.scalar(select(Book).where(Book.id == book_id).with_for_update())

    def lock_user(self, db: Session, user_id: int) -> User | None:
        return db.scalar(select(User).where(User.id == user_id).with_for_update())

    def lock_reservation(self, db: Session, reservation_id: int) -> Reservation | None:
        return db.scalar(
            select(Reservation).where(Reservation.id == reservation_id).with_for_update()
        )

    def count_active_for_user(self, db: Session, user_id: int) -> int:
        return int(
            db.scalar(
                select(func.count(Reservation.id)).where(
                    Reservation.user_id == user_id,
                    Reservation.status.in_(("PENDING", "READY")),
                )
            )
            or 0
        )

    def get_active_for_user_and_book(
        self, db: Session, user_id: int, book_id: int
    ) -> Reservation | None:
        return db.scalar(
            select(Reservation).where(
                Reservation.user_id == user_id,
                Reservation.book_id == book_id,
                Reservation.status.in_(("PENDING", "READY")),
            )
        )

    def has_active_borrowing(self, db: Session, user_id: int, book_id: int) -> bool:
        return db.scalar(
            select(Borrowing.id).where(
                Borrowing.user_id == user_id,
                Borrowing.book_id == book_id,
                Borrowing.status == "ACTIVE",
            )
        ) is not None

    def next_position(self, db: Session, book_id: int) -> int:
        return int(
            db.scalar(select(func.coalesce(func.max(Reservation.position), 0)).where(Reservation.book_id == book_id))
            or 0
        ) + 1

    def create(self, db: Session, *, user_id: int, book_id: int, position: int) -> Reservation:
        reservation = Reservation(
            user_id=user_id,
            book_id=book_id,
            position=position,
            status="PENDING",
        )
        db.add(reservation)
        return reservation

    def list_for_user(self, db: Session, user_id: int) -> list[Reservation]:
        return list(
            db.scalars(
                select(Reservation)
                .where(Reservation.user_id == user_id)
                .order_by(Reservation.created_at.desc(), Reservation.id.desc())
            )
        )

    def expired_ready_book_ids_for_user(self, db: Session, user_id: int, now: datetime) -> list[int]:
        return list(
            db.scalars(
                select(Reservation.book_id)
                .where(
                    Reservation.user_id == user_id,
                    Reservation.status == "READY",
                    Reservation.expires_at < now,
                )
                .distinct()
                .order_by(Reservation.book_id)
            )
        )

    def expire_ready_for_book(self, db: Session, book_id: int, now: datetime) -> None:
        db.execute(
            update(Reservation)
            .where(
                Reservation.book_id == book_id,
                Reservation.status == "READY",
                Reservation.expires_at < now,
            )
            .values(status="EXPIRED")
        )

    def count_ready_for_book(self, db: Session, book_id: int) -> int:
        return int(
            db.scalar(
                select(func.count(Reservation.id)).where(
                    Reservation.book_id == book_id,
                    Reservation.status == "READY",
                )
            )
            or 0
        )

    def earliest_pending_for_book(self, db: Session, book_id: int) -> Reservation | None:
        return db.scalar(
            select(Reservation)
            .where(Reservation.book_id == book_id, Reservation.status == "PENDING")
            .order_by(Reservation.position.asc(), Reservation.created_at.asc(), Reservation.id.asc())
            .with_for_update()
        )

    def get_ready_for_user_and_book(
        self, db: Session, user_id: int, book_id: int
    ) -> Reservation | None:
        return db.scalar(
            select(Reservation).where(
                Reservation.user_id == user_id,
                Reservation.book_id == book_id,
                Reservation.status == "READY",
            )
        )

    def has_ready_for_book(self, db: Session, book_id: int) -> bool:
        return db.scalar(
            select(Reservation.id).where(
                Reservation.book_id == book_id,
                Reservation.status == "READY",
            )
        ) is not None
