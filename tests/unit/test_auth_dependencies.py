import pytest

from app.core.exceptions import AppError
from app.dependencies.auth import require_admin
from app.models.user import User


def test_require_admin_rejects_regular_user() -> None:
    with pytest.raises(AppError) as exc_info:
        require_admin(User(role="USER"))

    assert exc_info.value.status_code == 403


def test_require_admin_accepts_admin_user() -> None:
    admin = User(role="ADMIN")

    assert require_admin(admin) is admin
