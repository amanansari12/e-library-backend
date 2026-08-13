"""Favorite business workflows."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.user import User
from app.repositories.favorite import FavoriteRepository
from app.schemas.favorite import FavoriteCreate, FavoriteResponse, FavoriteStatusResponse


class FavoriteService:
    """Coordinates authenticated favorite creation, removal, and lookup."""

    def __init__(self, repository: FavoriteRepository | None = None) -> None:
        self.repository = repository or FavoriteRepository()

    def create(self, db: Session, user: User, payload: FavoriteCreate) -> FavoriteResponse:
        """Add a non-archived book to the current user's favorites."""
        try:
            book = self.repository.lock_book(db, payload.book_id)
            if book is None:
                raise AppError(404, "BOOK_NOT_FOUND", "Book not found")
            if book.is_archived:
                raise AppError(409, "BOOK_ARCHIVED", "Archived books cannot be favorited")
            favorite = self.repository.create(db, user_id=user.id, book_id=book.id)
            db.commit()
            db.refresh(favorite)
            return FavoriteResponse.model_validate(favorite)
        except AppError:
            db.rollback()
            raise
        except IntegrityError as exc:
            db.rollback()
            raise AppError(409, "DUPLICATE_FAVORITE", "This book is already in your favorites") from exc

    def remove(self, db: Session, user: User, book_id: int) -> None:
        """Remove only the current user's favorite for a book."""
        favorite = self.repository.get_for_user_and_book(db, user.id, book_id)
        if favorite is None:
            raise AppError(404, "FAVORITE_NOT_FOUND", "Favorite not found")
        self.repository.delete(db, favorite)
        db.commit()

    def list_for_user(self, db: Session, user: User) -> list[FavoriteResponse]:
        return [
            FavoriteResponse.model_validate(favorite)
            for favorite in self.repository.list_for_user(db, user.id)
        ]

    def status_for_user(self, db: Session, user: User, book_id: int) -> FavoriteStatusResponse:
        if self.repository.get_book(db, book_id) is None:
            raise AppError(404, "BOOK_NOT_FOUND", "Book not found")
        return FavoriteStatusResponse(
            book_id=book_id,
            is_favorited=self.repository.get_for_user_and_book(db, user.id, book_id) is not None,
        )
