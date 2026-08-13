"""User profile schemas that never expose password data."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserResponse(BaseModel):
    """Safe representation of a user account."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    full_name: str
    role: str
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    """Fields a user may change on their own profile."""

    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    full_name: str | None = Field(default=None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def require_a_change(self) -> "UserUpdateRequest":
        """Reject empty PATCH payloads instead of silently accepting them."""
        if not self.model_fields_set:
            raise ValueError("At least one profile field must be provided")
        return self
