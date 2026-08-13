"""PostgreSQL aggregation queries for administrator statistics."""

from sqlalchemy import distinct, func, select, text
from sqlalchemy.orm import Session

from app.models.book import Book, book_categories
from app.models.book_summary import BookSummary
from app.models.borrowing import Borrowing
from app.models.category import Category
from app.models.rating import Rating
from app.models.reservation import Reservation
from app.models.user import User


class StatisticsRepository:
    """Database-side aggregate queries with no HTTP or authorization policy."""

    _last_30_days = func.now() - text("INTERVAL '30 days'")

    def user_statistics(self, db: Session) -> tuple[int, int, int]:
        total_users, new_users, active_borrowers = db.execute(
            select(
                func.count(distinct(User.id)),
                func.count(distinct(User.id)).filter(User.created_at >= self._last_30_days),
                func.count(distinct(Borrowing.user_id)).filter(Borrowing.status == "ACTIVE"),
            ).select_from(User).outerjoin(Borrowing, Borrowing.user_id == User.id)
        ).one()
        return int(total_users), int(new_users), int(active_borrowers)

    def book_statistics(self, db: Session) -> tuple[int, int, int]:
        total_books, available_books, archived_books = db.execute(
            select(
                func.count(Book.id),
                func.count(Book.id).filter(Book.max_concurrent_borrows > Book.current_borrows_count),
                func.count(Book.id).filter(Book.is_archived.is_(True)),
            )
        ).one()
        return int(total_books), int(available_books), int(archived_books)

    def borrowing_statistics(self, db: Session) -> tuple[int, int, int, int]:
        active, overdue, recent_borrowings, recent_returns = db.execute(
            select(
                func.count(Borrowing.id).filter(Borrowing.status == "ACTIVE"),
                func.count(Borrowing.id).filter(
                    Borrowing.status == "ACTIVE", Borrowing.due_date < func.now()
                ),
                func.count(Borrowing.id).filter(Borrowing.borrowed_at >= self._last_30_days),
                func.count(Borrowing.id).filter(Borrowing.returned_at >= self._last_30_days),
            )
        ).one()
        return int(active), int(overdue), int(recent_borrowings), int(recent_returns)

    def reservation_statistics(self, db: Session) -> tuple[int, int]:
        active_states = ("PENDING", "READY")
        active_reservations, books_with_waiting_lists = db.execute(
            select(
                func.count(Reservation.id).filter(Reservation.status.in_(active_states)),
                func.count(distinct(Reservation.book_id)).filter(Reservation.status.in_(active_states)),
            )
        ).one()
        return int(active_reservations), int(books_with_waiting_lists)

    def rating_statistics(self, db: Session) -> tuple[int, float | None]:
        total_ratings, average_rating = db.execute(
            select(func.count(Rating.id), func.avg(Rating.score))
        ).one()
        return int(total_ratings), float(average_rating) if average_rating is not None else None

    def ai_statistics(self, db: Session) -> tuple[int, int]:
        summaries_generated, unique_books_summarized = db.execute(
            select(func.count(BookSummary.id), func.count(distinct(BookSummary.book_id)))
        ).one()
        return int(summaries_generated), int(unique_books_summarized)

    def popular_books(self, db: Session) -> list[tuple[int, str, str, int]]:
        rows = db.execute(
            select(
                Book.id,
                Book.title,
                Book.isbn,
                func.count(Borrowing.id).label("borrowing_count"),
            )
            .join(Borrowing, Borrowing.book_id == Book.id)
            .group_by(Book.id, Book.title, Book.isbn)
            .order_by(func.count(Borrowing.id).desc(), Book.id.asc())
        ).all()
        return [(int(row.id), row.title, row.isbn, int(row.borrowing_count)) for row in rows]

    def popular_categories(self, db: Session) -> list[tuple[int, str, int]]:
        rows = db.execute(
            select(
                Category.id,
                Category.name,
                func.count(distinct(Borrowing.id)).label("borrowing_count"),
            )
            .join(book_categories, book_categories.c.category_id == Category.id)
            .join(Borrowing, Borrowing.book_id == book_categories.c.book_id)
            .group_by(Category.id, Category.name)
            .order_by(func.count(distinct(Borrowing.id)).desc(), Category.id.asc())
        ).all()
        return [(int(row.id), row.name, int(row.borrowing_count)) for row in rows]

    def highest_rated_books(self, db: Session, *, limit: int | None = None) -> list[tuple[int, str, str, float, int]]:
        statement = (
            select(
                Book.id,
                Book.title,
                Book.isbn,
                func.avg(Rating.score).label("average_rating"),
                func.count(Rating.id).label("rating_count"),
            )
            .join(Rating, Rating.book_id == Book.id)
            .group_by(Book.id, Book.title, Book.isbn)
            .order_by(func.avg(Rating.score).desc(), func.count(Rating.id).desc(), Book.id.asc())
        )
        if limit is not None:
            statement = statement.limit(limit)
        rows = db.execute(statement).all()
        return [
            (int(row.id), row.title, row.isbn, float(row.average_rating), int(row.rating_count))
            for row in rows
        ]
