"""ORM model for metadata describing a stored digital book file."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.book import Book


class BookFile(Base):
    """A stored digital asset; only one file per book is active at a time."""

    __tablename__ = "book_files"
    __table_args__ = (
        CheckConstraint("file_size > 0", name="ck_book_files_file_size_positive"),
        CheckConstraint("file_format IN ('PDF')", name="ck_book_files_file_format"),
        Index("uq_active_book_file", "book_id", unique=True, postgresql_where=text("is_active = true")),
        Index("ix_book_files_book_id", "book_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    book: Mapped["Book"] = relationship(back_populates="files")
