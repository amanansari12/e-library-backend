"""Response schemas for administrator-only library statistics."""

from pydantic import BaseModel


class UserStatistics(BaseModel):
    total_users: int
    new_users_last_30_days: int
    active_borrowers: int


class BookStatistics(BaseModel):
    total_books: int
    available_books: int
    archived_books: int


class BorrowingStatistics(BaseModel):
    active_borrowings: int
    overdue_borrowings: int
    borrowings_last_30_days: int
    returns_last_30_days: int


class ReservationStatistics(BaseModel):
    active_reservations: int
    books_with_waiting_lists: int


class HighestRatedBookStatistic(BaseModel):
    book_id: int
    title: str
    isbn: str
    average_rating: float
    rating_count: int


class RatingStatistics(BaseModel):
    total_ratings: int
    overall_average_rating: float | None
    highest_rated_books: list[HighestRatedBookStatistic]


class AIStatistics(BaseModel):
    summaries_generated: int
    unique_books_summarized: int
    summary_failure_count: int


class AdminStatistics(BaseModel):
    users: UserStatistics
    books: BookStatistics
    borrowings: BorrowingStatistics
    reservations: ReservationStatistics
    ratings: RatingStatistics
    ai: AIStatistics


class PopularBookStatistic(BaseModel):
    book_id: int
    title: str
    isbn: str
    borrowing_count: int


class PopularCategoryStatistic(BaseModel):
    category_id: int
    name: str
    borrowing_count: int
