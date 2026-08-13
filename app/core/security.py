"""Password hashing and JWT helpers."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import AppError


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(password: str) -> str:
    """Hash a user password with bcrypt."""
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password without exposing hash details."""
    return password_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, role: str) -> str:
    """Create a short-lived JWT used to access protected endpoints."""
    settings = get_settings()
    return _create_token(
        user_id=user_id,
        role=role,
        token_type=ACCESS_TOKEN_TYPE,
        expires_at=datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(user_id: int, role: str) -> tuple[str, datetime]:
    """Create a long-lived refresh JWT and return its expiration time."""
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    return (
        _create_token(
            user_id=user_id,
            role=role,
            token_type=REFRESH_TOKEN_TYPE,
            expires_at=expires_at,
        ),
        expires_at,
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    """Validate a JWT and require the expected token type."""
    try:
        payload = jwt.decode(token, get_settings().jwt_secret_key, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise AppError(401, "INVALID_TOKEN", "The authentication token is invalid or expired") from exc

    if payload.get("type") != expected_type:
        raise AppError(401, "INVALID_TOKEN", "The authentication token is invalid or expired")

    return payload


def _create_token(user_id: int, role: str, token_type: str, expires_at: datetime) -> str:
    issued_at = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": token_type,
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(payload, get_settings().jwt_secret_key, algorithm=JWT_ALGORITHM)
