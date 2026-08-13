"""Reservation queue ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


class Reservation(Base):
    """A reservation in a deterministic book waiting list."""

    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'READY', 'FULFILLED', 'CANCELLED', 'EXPIRED')",
            name="ck_reservations_status",
        ),
        Index(
            "uq_active_reservation",
            "user_id",
            "book_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'READY')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="reservations")
    book: Mapped["Book"] = relationship(back_populates="reservations")
