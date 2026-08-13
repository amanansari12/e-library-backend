"""Rating business workflows."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.user import User
from app.repositories.rating import RatingRepository
from app.schemas.rating import BookRatingsResponse, RatingCreate, RatingResponse


class RatingService:
    """Coordinates rating upserts, ownership-aware deletion, and aggregation."""

    def __init__(self, repository: RatingRepository | None = None) -> None:
        self.repository = repository or RatingRepository()

    def create_or_update(self, db: Session, user: User, payload: RatingCreate) -> RatingResponse:
        """Create the user's rating or update their existing rating for the book."""
        if self.repository.get_book(db, payload.book_id) is None:
            raise AppError(404, "BOOK_NOT_FOUND", "Book not found")
        try:
            rating = self.repository.get_for_user_and_book(db, user.id, payload.book_id)
            if rating is None:
                rating = self.repository.create(
                    db, user_id=user.id, book_id=payload.book_id, score=payload.score
                )
            else:
                rating.score = payload.score
            db.commit()
            db.refresh(rating)
            return RatingResponse.model_validate(rating)
        except IntegrityError as exc:
            db.rollback()
            raise AppError(409, "DUPLICATE_RATING", "Unable to create a duplicate rating") from exc

    def remove(self, db: Session, user: User, book_id: int) -> None:
        """Remove only the current user's rating for a book."""
        rating = self.repository.get_for_user_and_book(db, user.id, book_id)
        if rating is None:
            raise AppError(404, "RATING_NOT_FOUND", "Rating not found")
        self.repository.delete(db, rating)
        db.commit()

    def list_for_book(self, db: Session, book_id: int) -> BookRatingsResponse:
        """Return book ratings with SQL-computed average and count."""
        if self.repository.get_book(db, book_id) is None:
            raise AppError(404, "BOOK_NOT_FOUND", "Book not found")
        average_rating, rating_count = self.repository.stats_for_book(db, book_id)
        return BookRatingsResponse(
            book_id=book_id,
            items=[
                RatingResponse.model_validate(rating)
                for rating in self.repository.list_for_book(db, book_id)
            ],
            average_rating=average_rating,
            rating_count=rating_count,
        )

    def list_for_user(self, db: Session, user: User) -> list[RatingResponse]:
        return [
            RatingResponse.model_validate(rating)
            for rating in self.repository.list_for_user(db, user.id)
        ]
