"""Book ORM model and catalog association tables."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.author import Author
    from app.models.book_summary import BookSummary
    from app.models.book_file import BookFile
    from app.models.borrowing import Borrowing
    from app.models.category import Category
    from app.models.favorite import Favorite
    from app.models.rating import Rating
    from app.models.reservation import Reservation


book_authors = Table(
    "book_authors",
    Base.metadata,
    Column("book_id", ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)

book_categories = Table(
    "book_categories",
    Base.metadata,
    Column("book_id", ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class Book(Base):
    """Digital-library book with configurable concurrent borrow capacity."""

    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("max_concurrent_borrows > 0", name="ck_books_max_concurrent_borrows_positive"),
        CheckConstraint("current_borrows_count >= 0", name="ck_books_current_borrows_count_nonnegative"),
        CheckConstraint("content_version >= 1", name="ck_books_content_version_positive"),
        UniqueConstraint("isbn", name="uq_books_isbn"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    isbn: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    max_concurrent_borrows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3"
    )
    current_borrows_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    content_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    authors: Mapped[list["Author"]] = relationship(secondary=book_authors, back_populates="books")
    categories: Mapped[list["Category"]] = relationship(secondary=book_categories, back_populates="books")
    borrowings: Mapped[list["Borrowing"]] = relationship(back_populates="book")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="book")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="book")
    ratings: Mapped[list["Rating"]] = relationship(back_populates="book")
    summaries: Mapped[list["BookSummary"]] = relationship(back_populates="book")
    files: Mapped[list["BookFile"]] = relationship(back_populates="book", cascade="all, delete-orphan")
