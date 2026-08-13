"""Application service for administrator statistics and rankings."""

from sqlalchemy.orm import Session

from app.repositories.statistics import StatisticsRepository
from app.schemas.admin import (
    AIStatistics,
    AdminStatistics,
    BookStatistics,
    BorrowingStatistics,
    HighestRatedBookStatistic,
    PopularBookStatistic,
    PopularCategoryStatistic,
    RatingStatistics,
    ReservationStatistics,
    UserStatistics,
)
from app.services.summary import get_summary_failure_count


class AdminStatisticsService:
    """Coordinates database-backed statistics with lightweight AI process state."""

    def __init__(self, repository: StatisticsRepository | None = None) -> None:
        self.repository = repository or StatisticsRepository()

    def overview(self, db: Session) -> AdminStatistics:
        total_users, new_users, active_borrowers = self.repository.user_statistics(db)
        total_books, available_books, archived_books = self.repository.book_statistics(db)
        active_borrowings, overdue_borrowings, recent_borrowings, recent_returns = self.repository.borrowing_statistics(db)
        active_reservations, books_with_waiting_lists = self.repository.reservation_statistics(db)
        total_ratings, overall_average_rating = self.repository.rating_statistics(db)
        summaries_generated, unique_books_summarized = self.repository.ai_statistics(db)
        return AdminStatistics(
            users=UserStatistics(
                total_users=total_users,
                new_users_last_30_days=new_users,
                active_borrowers=active_borrowers,
            ),
            books=BookStatistics(
                total_books=total_books,
                available_books=available_books,
                archived_books=archived_books,
            ),
            borrowings=BorrowingStatistics(
                active_borrowings=active_borrowings,
                overdue_borrowings=overdue_borrowings,
                borrowings_last_30_days=recent_borrowings,
                returns_last_30_days=recent_returns,
            ),
            reservations=ReservationStatistics(
                active_reservations=active_reservations,
                books_with_waiting_lists=books_with_waiting_lists,
            ),
            ratings=RatingStatistics(
                total_ratings=total_ratings,
                overall_average_rating=overall_average_rating,
                highest_rated_books=self.highest_rated(db, limit=5),
            ),
            ai=AIStatistics(
                summaries_generated=summaries_generated,
                unique_books_summarized=unique_books_summarized,
                summary_failure_count=get_summary_failure_count(),
            ),
        )

    def popular_books(self, db: Session) -> list[PopularBookStatistic]:
        return [
            PopularBookStatistic(
                book_id=book_id, title=title, isbn=isbn, borrowing_count=borrowing_count
            )
            for book_id, title, isbn, borrowing_count in self.repository.popular_books(db)
        ]

    def popular_categories(self, db: Session) -> list[PopularCategoryStatistic]:
        return [
            PopularCategoryStatistic(
                category_id=category_id, name=name, borrowing_count=borrowing_count
            )
            for category_id, name, borrowing_count in self.repository.popular_categories(db)
        ]

    def highest_rated(self, db: Session, *, limit: int | None = None) -> list[HighestRatedBookStatistic]:
        return [
            HighestRatedBookStatistic(
                book_id=book_id,
                title=title,
                isbn=isbn,
                average_rating=average_rating,
                rating_count=rating_count,
            )
            for book_id, title, isbn, average_rating, rating_count in self.repository.highest_rated_books(
                db, limit=limit
            )
        ]
