"""ORM models imported here so Alembic can discover all metadata."""

from app.models.author import Author
from app.models.book import Book, book_authors, book_categories
from app.models.book_file import BookFile
from app.models.book_review import BookReview
from app.models.book_summary import BookSummary
from app.models.borrowing import Borrowing
from app.models.category import Category
from app.models.favorite import Favorite
from app.models.rating import Rating
from app.models.reading_progress import ReadingProgress
from app.models.refresh_token import RefreshToken
from app.models.reservation import Reservation
from app.models.user import User

__all__ = [
    "Author",
    "Book",
    "BookFile",
    "BookReview",
    "BookSummary",
    "Borrowing",
    "Category",
    "Favorite",
    "Rating",
    "ReadingProgress",
    "RefreshToken",
    "Reservation",
    "User",
    "book_authors",
    "book_categories",
]
