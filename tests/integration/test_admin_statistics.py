"""Integration coverage for administrator-only PostgreSQL statistics."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.security import create_access_token
from app.models.book import Book
from app.models.book_summary import BookSummary
from app.models.borrowing import Borrowing
from app.models.category import Category
from app.models.rating import Rating
from app.models.reservation import Reservation
from app.models.user import User
from app.services import summary as summary_service_module
from tests.integration.test_borrowings import _create_book, _create_user, _headers


def _create_admin(session_factory) -> User:
    identifier = uuid4().hex
    with session_factory() as session:
        admin = User(
            email=f"admin-{identifier}@example.com",
            username=f"admin-{identifier}",
            hashed_password="not-used-in-this-test",
            full_name="Library Administrator",
            role="ADMIN",
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        session.expunge(admin)
        return admin


def _admin_headers(admin: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(admin.id, admin.role)}"}


def _seed_statistics_data(session_factory) -> tuple[User, dict[str, int]]:
    now = datetime.now(UTC)
    with session_factory() as session:
        identifier = uuid4().hex[:12]
        admin = User(
            email=f"admin-{identifier}@example.com",
            username=f"admin-{identifier}",
            hashed_password="not-used-in-this-test",
            full_name="Library Administrator",
            role="ADMIN",
            created_at=now - timedelta(days=2),
        )
        active_user = User(
            email=f"active-{identifier}@example.com",
            username=f"active-{identifier}",
            hashed_password="not-used-in-this-test",
            full_name="Active Borrower",
            role="USER",
            created_at=now - timedelta(days=5),
        )
        old_user = User(
            email=f"old-{identifier}@example.com",
            username=f"old-{identifier}",
            hashed_password="not-used-in-this-test",
            full_name="Older User",
            role="USER",
            created_at=now - timedelta(days=31),
        )
        returned_user = User(
            email=f"returned-{identifier}@example.com",
            username=f"returned-{identifier}",
            hashed_password="not-used-in-this-test",
            full_name="Returned Borrower",
            role="USER",
            created_at=now - timedelta(days=40),
        )
        rating_user = User(
            email=f"rating-{identifier}@example.com",
            username=f"rating-{identifier}",
            hashed_password="not-used-in-this-test",
            full_name="Rating User",
            role="USER",
            created_at=now - timedelta(days=40),
        )
        book_one = Book(title="Popular Book", isbn=f"stats-book-one-{identifier}", max_concurrent_borrows=2, current_borrows_count=1)
        book_two = Book(title="Archived Book", isbn=f"stats-book-two-{identifier}", max_concurrent_borrows=1, current_borrows_count=1, is_archived=True)
        book_three = Book(title="Available Archived Book", isbn=f"stats-book-three-{identifier}", max_concurrent_borrows=1, current_borrows_count=0, is_archived=True)
        category_one = Category(name=f"History {identifier}")
        category_two = Category(name=f"Science {identifier}")
        book_one.categories = [category_one, category_two]
        book_two.categories = [category_two]
        session.add_all([admin, active_user, old_user, returned_user, rating_user, book_one, book_two, book_three])
        session.flush()
        session.add_all(
            [
                Borrowing(user_id=active_user.id, book_id=book_two.id, borrowed_at=now - timedelta(days=2), due_date=now - timedelta(days=1), status="ACTIVE"),
                Borrowing(user_id=active_user.id, book_id=book_one.id, borrowed_at=now - timedelta(days=3), due_date=now + timedelta(days=7), status="ACTIVE"),
                Borrowing(user_id=returned_user.id, book_id=book_one.id, borrowed_at=now - timedelta(days=40), due_date=now - timedelta(days=30), returned_at=now - timedelta(days=1), status="RETURNED"),
                Reservation(user_id=active_user.id, book_id=book_one.id, position=1, status="PENDING"),
                Reservation(user_id=old_user.id, book_id=book_one.id, position=2, status="READY"),
                Reservation(user_id=returned_user.id, book_id=book_two.id, position=1, status="CANCELLED"),
                Rating(user_id=active_user.id, book_id=book_one.id, score=5),
                Rating(user_id=old_user.id, book_id=book_one.id, score=3),
                Rating(user_id=returned_user.id, book_id=book_two.id, score=4),
                BookSummary(book_id=book_one.id, content_version=1, model="test", summary_text="one"),
                BookSummary(book_id=book_one.id, content_version=2, model="test", summary_text="two"),
                BookSummary(book_id=book_two.id, content_version=1, model="test", summary_text="three"),
            ]
        )
        session.commit()
        session.refresh(admin)
        session.expunge(admin)
        return admin, {
            "book_one": book_one.id,
            "book_two": book_two.id,
            "book_one_isbn": book_one.isbn,
            "book_two_isbn": book_two.isbn,
            "category_one": category_one.id,
            "category_two": category_two.id,
        }


def test_admin_statistics_are_aggregated_and_ranked(client, session_factory, monkeypatch) -> None:
    admin, ids = _seed_statistics_data(session_factory)
    monkeypatch.setattr(summary_service_module, "_summary_failure_count", 2)

    overview = client.get("/api/v1/admin/statistics", headers=_admin_headers(admin))
    popular_books = client.get("/api/v1/admin/statistics/popular-books", headers=_admin_headers(admin))
    popular_categories = client.get("/api/v1/admin/statistics/popular-categories", headers=_admin_headers(admin))
    highest_rated = client.get("/api/v1/admin/statistics/highest-rated", headers=_admin_headers(admin))

    assert overview.status_code == 200
    assert overview.json() == {
        "users": {"total_users": 5, "new_users_last_30_days": 2, "active_borrowers": 1},
        "books": {"total_books": 3, "available_books": 2, "archived_books": 2},
        "borrowings": {
            "active_borrowings": 2,
            "overdue_borrowings": 1,
            "borrowings_last_30_days": 2,
            "returns_last_30_days": 1,
        },
        "reservations": {"active_reservations": 2, "books_with_waiting_lists": 1},
        "ratings": {
            "total_ratings": 3,
            "overall_average_rating": 4.0,
            "highest_rated_books": [
                {"book_id": ids["book_one"], "title": "Popular Book", "isbn": ids["book_one_isbn"], "average_rating": 4.0, "rating_count": 2},
                {"book_id": ids["book_two"], "title": "Archived Book", "isbn": ids["book_two_isbn"], "average_rating": 4.0, "rating_count": 1},
            ],
        },
        "ai": {"summaries_generated": 3, "unique_books_summarized": 2, "summary_failure_count": 2},
    }
    assert [(item["book_id"], item["borrowing_count"]) for item in popular_books.json()] == [
        (ids["book_one"], 2),
        (ids["book_two"], 1),
    ]
    assert [(item["category_id"], item["borrowing_count"]) for item in popular_categories.json()] == [
        (ids["category_two"], 3),
        (ids["category_one"], 2),
    ]
    assert [(item["book_id"], item["average_rating"], item["rating_count"]) for item in highest_rated.json()] == [
        (ids["book_one"], 4.0, 2),
        (ids["book_two"], 4.0, 1),
    ]


def test_admin_statistics_require_administrator_role(client, session_factory) -> None:
    admin = _create_admin(session_factory)
    user = _create_user(session_factory)
    endpoints = [
        "/api/v1/admin/statistics",
        "/api/v1/admin/statistics/popular-books",
        "/api/v1/admin/statistics/popular-categories",
        "/api/v1/admin/statistics/highest-rated",
    ]

    for endpoint in endpoints:
        assert client.get(endpoint, headers=_admin_headers(admin)).status_code == 200
        assert client.get(endpoint, headers=_headers(user)).status_code == 403
        assert client.get(endpoint).status_code == 401


def test_admin_statistics_empty_data_is_sensible(client, session_factory) -> None:
    admin = _create_admin(session_factory)
    headers = _admin_headers(admin)

    overview = client.get("/api/v1/admin/statistics", headers=headers)

    assert overview.status_code == 200
    assert overview.json() == {
        "users": {"total_users": 1, "new_users_last_30_days": 1, "active_borrowers": 0},
        "books": {"total_books": 0, "available_books": 0, "archived_books": 0},
        "borrowings": {
            "active_borrowings": 0,
            "overdue_borrowings": 0,
            "borrowings_last_30_days": 0,
            "returns_last_30_days": 0,
        },
        "reservations": {"active_reservations": 0, "books_with_waiting_lists": 0},
        "ratings": {"total_ratings": 0, "overall_average_rating": None, "highest_rated_books": []},
        "ai": {"summaries_generated": 0, "unique_books_summarized": 0, "summary_failure_count": summary_service_module.get_summary_failure_count()},
    }
    assert client.get("/api/v1/admin/statistics/popular-books", headers=headers).json() == []
    assert client.get("/api/v1/admin/statistics/popular-categories", headers=headers).json() == []
    assert client.get("/api/v1/admin/statistics/highest-rated", headers=headers).json() == []
