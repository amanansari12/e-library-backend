"""Business workflows for optional, borrowing-history-gated book reviews."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.book_review import BookReview
from app.models.user import User
from app.repositories.review import ReviewRepository
from app.schemas.review import ReviewAuthorResponse, ReviewCreate, ReviewResponse, ReviewUpdate


class ReviewService:
    """Coordinates eligibility, duplicate prevention, and owner-only review changes."""

    def __init__(self, repository: ReviewRepository | None = None) -> None:
        self.repository = repository or ReviewRepository()

    def create(self, db: Session, user: User, payload: ReviewCreate) -> ReviewResponse:
        """Create an optional review after any genuine borrowing of the book."""
        try:
            if self.repository.get_book(db, payload.book_id) is None:
                raise AppError(404, "BOOK_NOT_FOUND", "Book not found")
            if not self.repository.has_borrowed_book(db, user.id, payload.book_id):
                raise AppError(
                    403,
                    "REVIEW_NOT_ALLOWED",
                    "You can review a book only after borrowing it",
                )
            if self.repository.get_for_user_and_book(db, user.id, payload.book_id) is not None:
                raise AppError(409, "REVIEW_ALREADY_EXISTS", "You already reviewed this book")
            review = self.repository.create(
                db,
                user_id=user.id,
                book_id=payload.book_id,
                review_text=payload.review_text,
            )
            db.commit()
            db.refresh(review)
            return self._response(review, user)
        except AppError:
            db.rollback()
            raise
        except IntegrityError as exc:
            db.rollback()
            raise AppError(409, "REVIEW_ALREADY_EXISTS", "You already reviewed this book") from exc

    def update(self, db: Session, user: User, review_id: int, payload: ReviewUpdate) -> ReviewResponse:
        """Update only the current user's review without rechecking borrowing history."""
        review = self._require_owned_review(db, user, review_id)
        review.review_text = payload.review_text
        db.commit()
        db.refresh(review)
        return self._response(review, user)

    def remove(self, db: Session, user: User, review_id: int) -> None:
        """Delete only the current user's review."""
        review = self._require_owned_review(db, user, review_id)
        self.repository.delete(db, review)
        db.commit()

    def list_for_book(self, db: Session, book_id: int) -> list[ReviewResponse]:
        """Return reviews for one existing book without exposing private account data."""
        if self.repository.get_book(db, book_id) is None:
            raise AppError(404, "BOOK_NOT_FOUND", "Book not found")
        return [self._response(review, review.user) for review in self.repository.list_for_book(db, book_id)]

    def list_for_user(self, db: Session, user: User) -> list[ReviewResponse]:
        """Return only the current user's own reviews."""
        return [self._response(review, review.user) for review in self.repository.list_for_user(db, user.id)]

    def _require_owned_review(self, db: Session, user: User, review_id: int) -> BookReview:
        review = self.repository.get(db, review_id)
        if review is None:
            raise AppError(404, "REVIEW_NOT_FOUND", "Review not found")
        if review.user_id != user.id:
            raise AppError(403, "FORBIDDEN", "You do not own this review")
        return review

    @staticmethod
    def _response(review: BookReview, user: User) -> ReviewResponse:
        return ReviewResponse(
            id=review.id,
            user_id=review.user_id,
            book_id=review.book_id,
            review_text=review.review_text,
            created_at=review.created_at,
            updated_at=review.updated_at,
            user=ReviewAuthorResponse(id=user.id, username=user.username, full_name=user.full_name),
        )
