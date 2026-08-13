"""Authentication request and response schemas."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    """Public registration payload for a normal library user."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=255)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        """Avoid silently truncating passwords beyond bcrypt's byte limit."""
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value


class LoginRequest(BaseModel):
    """Credentials used to obtain access and refresh tokens."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        """Reject byte lengths bcrypt cannot safely verify."""
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value


class RefreshTokenRequest(BaseModel):
    """Refresh token submitted to issue a new access token."""

    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """Tokens returned after successful authentication."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse


class AccessTokenResponse(BaseModel):
    """A renewed access token returned by the refresh endpoint."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
