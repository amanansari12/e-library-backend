"""Authentication and profile business workflows."""

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserUpdateRequest


class AuthService:
    """Registration, token issuance, refresh, logout, and profile updates."""

    def __init__(self, user_repository: UserRepository | None = None) -> None:
        self.user_repository = user_repository or UserRepository()

    def register(self, db: Session, payload: RegisterRequest) -> User:
        email = str(payload.email).lower()
        if self.user_repository.get_by_email(db, email):
            raise AppError(409, "EMAIL_ALREADY_REGISTERED", "An account with this email already exists")
        if self.user_repository.get_by_username(db, payload.username):
            raise AppError(409, "USERNAME_ALREADY_REGISTERED", "This username is already in use")

        user = self.user_repository.create_user(
            db,
            email=email,
            username=payload.username,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name.strip(),
        )
        self._commit(db, "A user with this email or username already exists")
        db.refresh(user)
        return user

    def login(self, db: Session, payload: LoginRequest) -> tuple[User, str, str]:
        user = self.user_repository.get_by_email(db, str(payload.email).lower())
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise AppError(401, "INVALID_CREDENTIALS", "Invalid email or password")

        access_token = create_access_token(user.id, user.role)
        refresh_token, expires_at = create_refresh_token(user.id, user.role)
        self.user_repository.create_refresh_token(
            db, user_id=user.id, token=refresh_token, expires_at=expires_at
        )
        self._commit(db, "Unable to complete login")
        return user, access_token, refresh_token

    def refresh_access_token(self, db: Session, refresh_token: str) -> str:
        payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
        user = self._get_refresh_token_user(db, refresh_token, payload)
        return create_access_token(user.id, user.role)

    def logout(self, db: Session, refresh_token: str) -> None:
        payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
        self._get_refresh_token_user(db, refresh_token, payload)
        stored_token = self.user_repository.get_refresh_token(db, refresh_token)
        if stored_token is None:
            raise AppError(401, "INVALID_REFRESH_TOKEN", "The refresh token is invalid or revoked")
        stored_token.revoked = True
        self._commit(db, "Unable to log out")

    def update_profile(self, db: Session, user: User, payload: UserUpdateRequest) -> User:
        updates = payload.model_dump(exclude_unset=True)
        if "email" in updates:
            email = str(updates["email"]).lower()
            existing_user = self.user_repository.get_by_email(db, email)
            if existing_user is not None and existing_user.id != user.id:
                raise AppError(409, "EMAIL_ALREADY_REGISTERED", "An account with this email already exists")
            user.email = email
        if "username" in updates:
            username = updates["username"]
            existing_user = self.user_repository.get_by_username(db, username)
            if existing_user is not None and existing_user.id != user.id:
                raise AppError(409, "USERNAME_ALREADY_REGISTERED", "This username is already in use")
            user.username = username
        if "full_name" in updates:
            user.full_name = updates["full_name"].strip()

        self._commit(db, "A user with this email or username already exists")
        db.refresh(user)
        return user

    def _get_refresh_token_user(self, db: Session, token: str, payload: dict[str, object]) -> User:
        stored_token = self.user_repository.get_refresh_token(db, token)
        if stored_token is None or stored_token.revoked or stored_token.expires_at <= datetime.now(UTC):
            raise AppError(401, "INVALID_REFRESH_TOKEN", "The refresh token is invalid or revoked")

        try:
            user_id = int(payload["sub"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AppError(401, "INVALID_TOKEN", "The authentication token is invalid or expired") from exc

        if stored_token.user_id != user_id:
            raise AppError(401, "INVALID_REFRESH_TOKEN", "The refresh token is invalid or revoked")
        user = self.user_repository.get_by_id(db, user_id)
        if user is None:
            raise AppError(401, "INVALID_TOKEN", "The authentication token is invalid or expired")
        return user

    @staticmethod
    def _commit(db: Session, duplicate_message: str) -> None:
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise AppError(409, "DUPLICATE_USER", duplicate_message) from exc
