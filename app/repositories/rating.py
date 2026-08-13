"""Database queries and persistence helpers for ratings."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.rating import Rating


class RatingRepository:
    """Rating persistence operations without ownership policy."""

    def get_book(self, db: Session, book_id: int) -> Book | None:
        return db.get(Book, book_id)

    def get_for_user_and_book(self, db: Session, user_id: int, book_id: int) -> Rating | None:
        return db.scalar(
            select(Rating).where(Rating.user_id == user_id, Rating.book_id == book_id)
        )

    def create(self, db: Session, *, user_id: int, book_id: int, score: int) -> Rating:
        rating = Rating(user_id=user_id, book_id=book_id, score=score)
        db.add(rating)
        return rating

    def delete(self, db: Session, rating: Rating) -> None:
        db.delete(rating)

    def list_for_book(self, db: Session, book_id: int) -> list[Rating]:
        return list(
            db.scalars(
                select(Rating)
                .where(Rating.book_id == book_id)
                .order_by(Rating.created_at.desc(), Rating.id.desc())
            )
        )

    def list_for_user(self, db: Session, user_id: int) -> list[Rating]:
        return list(
            db.scalars(
                select(Rating)
                .where(Rating.user_id == user_id)
                .order_by(Rating.created_at.desc(), Rating.id.desc())
            )
        )

    def stats_for_book(self, db: Session, book_id: int) -> tuple[float | None, int]:
        average, count = db.execute(
            select(func.avg(Rating.score), func.count(Rating.id)).where(Rating.book_id == book_id)
        ).one()
        return (float(average) if average is not None else None, int(count))
