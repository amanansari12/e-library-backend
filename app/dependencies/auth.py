"""Authentication and authorization dependencies."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import UserRepository


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Return the account represented by a valid access token."""
    if credentials is None:
        raise AppError(401, "NOT_AUTHENTICATED", "Authentication is required")

    payload = decode_token(credentials.credentials, ACCESS_TOKEN_TYPE)
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise AppError(401, "INVALID_TOKEN", "The authentication token is invalid or expired") from exc

    user = UserRepository().get_by_id(db, user_id)
    if user is None:
        raise AppError(401, "INVALID_TOKEN", "The authentication token is invalid or expired")
    return user


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require the ADMIN role for administrative endpoints."""
    if current_user.role != "ADMIN":
        raise AppError(403, "FORBIDDEN", "Administrator access is required")
    return current_user
