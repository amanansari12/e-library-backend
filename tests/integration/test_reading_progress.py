"""Integration coverage for private, active-borrowing-gated reading progress."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

from sqlalchemy import func, select

from app.api.v1 import books as books_api
from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.book import Book
from app.models.reading_progress import ReadingProgress
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas.reading_progress import ReadingProgressUpdate
from app.services.book_file import BookFileService
from app.services.reading_progress import ReadingProgressService
from tests.integration.test_borrowings import _borrow, _create_book, _create_user, _headers
from tests.integration.test_catalog import _pdf_bytes


def _put_progress(client, user, book_id: int, current_page: int = 1, total_pages: int = 10):
    return client.put(
        f"/api/v1/books/{book_id}/progress",
        headers=_headers(user),
        json={"current_page": current_page, "total_pages": total_pages},
    )


def test_active_borrower_can_create_and_idempotently_update_private_progress(client, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    assert _borrow(client, user, book.id).status_code == 201

    created = _put_progress(client, user, book.id, 3, 12)
    updated = _put_progress(client, user, book.id, 12, 12)
    with session_factory() as session:
        rows = list(
            session.scalars(
                select(ReadingProgress).where(
                    ReadingProgress.user_id == user.id,
                    ReadingProgress.book_id == book.id,
                )
            )
        )

    assert created.status_code == 200
    assert created.json()["progress_percent"] == 25.0
    assert created.json()["content_version"] == 1
    assert created.json()["is_stale"] is False
    assert updated.status_code == 200
    assert updated.json()["current_page"] == 12
    assert updated.json()["progress_percent"] == 100.0
    assert updated.json()["last_read_at"] >= created.json()["last_read_at"]
    assert len(rows) == 1
    assert rows[0].current_page == 12


def test_progress_requires_active_borrowing_not_reservation_and_valid_book(client, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    with session_factory() as session:
        session.add(Reservation(user_id=user.id, book_id=book.id, position=1))
        session.commit()

    unauthenticated = client.put(
        f"/api/v1/books/{book.id}/progress", json={"current_page": 1, "total_pages": 10}
    )
    reservation_only = _put_progress(client, user, book.id)
    missing = _put_progress(client, user, 99999)

    assert unauthenticated.status_code == 401
    assert reservation_only.status_code == 403
    assert reservation_only.json()["error"]["code"] == "ACTIVE_BORROWING_REQUIRED"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "BOOK_NOT_FOUND"


def test_progress_page_validation_rejects_invalid_values_and_accepts_boundaries(client, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    assert _borrow(client, user, book.id).status_code == 201

    zero_page = _put_progress(client, user, book.id, 0, 10)
    past_end = _put_progress(client, user, book.id, 11, 10)
    zero_total = _put_progress(client, user, book.id, 1, 0)
    valid_first = _put_progress(client, user, book.id, 1, 10)
    valid_last = _put_progress(client, user, book.id, 10, 10)

    assert all(response.status_code == 422 for response in [zero_page, past_end, zero_total])
    assert all(response.json()["error"]["code"] == "VALIDATION_ERROR" for response in [zero_page, past_end, zero_total])
    assert valid_first.status_code == 200
    assert valid_last.status_code == 200


def test_progress_get_is_owner_scoped_and_remains_visible_after_return(client, session_factory) -> None:
    owner = _create_user(session_factory)
    other_user = _create_user(session_factory)
    book = _create_book(session_factory)
    borrowing_id = _borrow(client, owner, book.id).json()["id"]
    assert _put_progress(client, owner, book.id, 6, 20).status_code == 200

    owner_get = client.get(f"/api/v1/books/{book.id}/progress", headers=_headers(owner))
    other_get = client.get(f"/api/v1/books/{book.id}/progress", headers=_headers(other_user))
    no_progress = client.get(f"/api/v1/books/{_create_book(session_factory).id}/progress", headers=_headers(owner))
    assert client.post(f"/api/v1/borrowings/{borrowing_id}/return", headers=_headers(owner)).status_code == 200
    after_return_get = client.get(f"/api/v1/books/{book.id}/progress", headers=_headers(owner))
    after_return_put = _put_progress(client, owner, book.id, 7, 20)

    assert owner_get.status_code == 200
    assert owner_get.json()["current_page"] == 6
    assert other_get.status_code == 404
    assert other_get.json()["error"]["code"] == "READING_PROGRESS_NOT_FOUND"
    assert no_progress.status_code == 404
    assert after_return_get.status_code == 200
    assert after_return_get.json()["current_page"] == 6
    assert after_return_put.status_code == 403
    assert after_return_put.json()["error"]["code"] == "ACTIVE_BORROWING_REQUIRED"


def test_continue_reading_is_private_deterministic_and_marks_stale_versions(client, session_factory) -> None:
    user = _create_user(session_factory)
    other_user = _create_user(session_factory)
    older_book = _create_book(session_factory)
    newer_book = _create_book(session_factory)
    other_book = _create_book(session_factory)
    for book in (older_book, newer_book, other_book):
        borrower = other_user if book.id == other_book.id else user
        assert _borrow(client, borrower, book.id).status_code == 201
    assert _put_progress(client, user, older_book.id, 2, 10).status_code == 200
    assert _put_progress(client, user, newer_book.id, 3, 10).status_code == 200
    assert _put_progress(client, other_user, other_book.id, 4, 10).status_code == 200
    with session_factory() as session:
        older = session.scalar(select(ReadingProgress).where(ReadingProgress.book_id == older_book.id))
        newer = session.scalar(select(ReadingProgress).where(ReadingProgress.book_id == newer_book.id))
        stale_book = session.get(Book, older_book.id)
        assert older is not None and newer is not None and stale_book is not None
        older.last_read_at = datetime.now(UTC) - timedelta(hours=1)
        newer.last_read_at = datetime.now(UTC)
        stale_book.content_version += 1
        session.commit()

    owner_list = client.get("/api/v1/reading-progress/me", headers=_headers(user))
    other_list = client.get("/api/v1/reading-progress/me", headers=_headers(other_user))

    assert [item["book_id"] for item in owner_list.json()] == [newer_book.id, older_book.id]
    assert owner_list.json()[1]["is_stale"] is True
    assert owner_list.json()[1]["content_version"] == 1
    assert [item["book_id"] for item in other_list.json()] == [other_book.id]


def test_progress_update_uses_current_content_version_without_affecting_borrowing_state(client, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    assert _borrow(client, user, book.id).status_code == 201
    assert _put_progress(client, user, book.id, 4, 10).status_code == 200
    with session_factory() as session:
        stored_book = session.get(Book, book.id)
        assert stored_book is not None
        stored_book.content_version += 1
        current_borrow_count = stored_book.current_borrows_count
        session.commit()

    updated = _put_progress(client, user, book.id, 5, 10)
    detail = client.get(f"/api/v1/books/{book.id}")

    assert updated.status_code == 200
    assert updated.json()["content_version"] == 2
    assert updated.json()["is_stale"] is False
    assert detail.json()["current_borrows_count"] == current_borrow_count


def test_archived_book_preserves_progress_but_blocks_new_updates(client, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    assert _borrow(client, user, book.id).status_code == 201
    assert _put_progress(client, user, book.id, 4, 10).status_code == 200
    with session_factory() as session:
        stored_book = session.get(Book, book.id)
        assert stored_book is not None
        stored_book.is_archived = True
        session.commit()

    historical = client.get(f"/api/v1/books/{book.id}/progress", headers=_headers(user))
    update = _put_progress(client, user, book.id, 5, 10)

    assert historical.status_code == 200
    assert historical.json()["current_page"] == 4
    assert update.status_code == 409
    assert update.json()["error"]["code"] == "BOOK_ARCHIVED"


def test_pdf_replacement_marks_existing_progress_stale(client, session_factory, monkeypatch, tmp_path) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    assert _borrow(client, user, book.id).status_code == 201
    assert _put_progress(client, user, book.id, 4, 10).status_code == 200
    identifier = uuid4().hex
    with session_factory() as session:
        admin = User(
            email=f"progress-admin-{identifier}@example.com",
            username=f"progress-admin-{identifier}",
            hashed_password="not-used-in-this-test",
            full_name="Progress Administrator",
            role="ADMIN",
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        session.expunge(admin)
    monkeypatch.setattr(
        books_api,
        "book_file_service",
        BookFileService(
            settings=Settings(
                jwt_secret_key="test-secret",
                book_storage_root=str(tmp_path),
                max_book_file_size_mb=1,
            )
        ),
    )

    replaced = client.post(
        f"/api/v1/books/{book.id}/file",
        headers=_headers(admin),
        files={"file": ("replacement.pdf", _pdf_bytes(), "application/pdf")},
    )
    progress = client.get(f"/api/v1/books/{book.id}/progress", headers=_headers(user))

    assert replaced.status_code == 200
    assert replaced.json()["content_version"] == 2
    assert progress.status_code == 200
    assert progress.json()["content_version"] == 1
    assert progress.json()["is_stale"] is True


def test_concurrent_initial_progress_updates_leave_one_row(session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    with session_factory() as session:
        from app.models.borrowing import Borrowing

        session.add(
            Borrowing(
                user_id=user.id,
                book_id=book.id,
                due_date=datetime.now(UTC) + timedelta(days=14),
                status="ACTIVE",
            )
        )
        stored_book = session.get(Book, book.id)
        assert stored_book is not None
        stored_book.current_borrows_count = 1
        session.commit()
    start = Barrier(2)

    def attempt(page: int) -> str:
        with session_factory() as session:
            start.wait()
            try:
                ReadingProgressService().set_for_book(
                    session,
                    user,
                    book.id,
                    ReadingProgressUpdate(current_page=page, total_pages=10),
                )
                return "success"
            except AppError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, (2, 7)))
    with session_factory() as session:
        count = session.scalar(
            select(func.count(ReadingProgress.id)).where(
                ReadingProgress.user_id == user.id,
                ReadingProgress.book_id == book.id,
            )
        )

    assert outcomes == ["success", "success"]
    assert count == 1
