"""Database queries for users and refresh tokens."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken
from app.models.user import User


class UserRepository:
    """Persistence operations with no authentication business policy."""

    def get_by_id(self, db: Session, user_id: int) -> User | None:
        return db.get(User, user_id)

    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.scalar(select(User).where(User.email == email))

    def get_by_username(self, db: Session, username: str) -> User | None:
        return db.scalar(select(User).where(User.username == username))

    def create_user(
        self,
        db: Session,
        *,
        email: str,
        username: str,
        hashed_password: str,
        full_name: str,
    ) -> User:
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            role="USER",
        )
        db.add(user)
        return user

    def create_refresh_token(
        self, db: Session, *, user_id: int, token: str, expires_at: datetime
    ) -> RefreshToken:
        refresh_token = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
        db.add(refresh_token)
        return refresh_token

    def get_refresh_token(self, db: Session, token: str) -> RefreshToken | None:
        return db.scalar(select(RefreshToken).where(RefreshToken.token == token))
