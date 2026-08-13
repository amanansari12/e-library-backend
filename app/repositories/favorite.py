"""Database queries and persistence helpers for favorites."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.favorite import Favorite


class FavoriteRepository:
    """Favorite persistence operations without ownership policy."""

    def lock_book(self, db: Session, book_id: int) -> Book | None:
        return db.scalar(select(Book).where(Book.id == book_id).with_for_update())

    def get_book(self, db: Session, book_id: int) -> Book | None:
        return db.get(Book, book_id)

    def create(self, db: Session, *, user_id: int, book_id: int) -> Favorite:
        favorite = Favorite(user_id=user_id, book_id=book_id)
        db.add(favorite)
        return favorite

    def get_for_user_and_book(self, db: Session, user_id: int, book_id: int) -> Favorite | None:
        return db.scalar(
            select(Favorite).where(Favorite.user_id == user_id, Favorite.book_id == book_id)
        )

    def list_for_user(self, db: Session, user_id: int) -> list[Favorite]:
        return list(
            db.scalars(
                select(Favorite)
                .where(Favorite.user_id == user_id)
                .order_by(Favorite.created_at.desc(), Favorite.id.desc())
            )
        )

    def delete(self, db: Session, favorite: Favorite) -> None:
        db.delete(favorite)
