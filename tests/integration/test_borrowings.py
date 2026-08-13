from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.exceptions import AppError
from app.core.security import create_access_token
from app.models.book import Book
from app.models.book_file import BookFile
from app.models.borrowing import Borrowing
from app.models.user import User
from app.schemas.borrowing import BorrowingCreate
from app.services.borrowing import BorrowingService


def _create_user(session_factory) -> User:
    identifier = uuid4().hex
    with session_factory() as session:
        user = User(
            email=f"reader-{identifier}@example.com",
            username=f"reader-{identifier}",
            hashed_password="not-used-in-this-test",
            full_name="Library Reader",
            role="USER",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


def _create_book(session_factory, *, capacity: int = 3) -> Book:
    identifier = uuid4().hex[:20]
    with session_factory() as session:
        book = Book(
            title=f"Borrowing Book {identifier}",
            isbn=f"borrow-{identifier}",
            max_concurrent_borrows=capacity,
        )
        book.files.append(
            BookFile(
                original_filename="fixture.pdf",
                storage_key=f"fixtures/{identifier}/original.pdf",
                mime_type="application/pdf",
                file_size=1,
                file_format="PDF",
                checksum="0" * 64,
                is_active=True,
            )
        )
        session.add(book)
        session.commit()
        session.refresh(book)
        session.expunge(book)
        return book


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _due_date(*, days: int = 14) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def _borrow(client: TestClient, user: User, book_id: int, *, days: int = 14):
    return client.post(
        "/api/v1/borrowings",
        headers=_headers(user),
        json={"book_id": book_id, "due_date": _due_date(days=days)},
    )


def _book_count(session_factory, book_id: int) -> int:
    with session_factory() as session:
        book = session.get(Book, book_id)
        assert book is not None
        return book.current_borrows_count


def test_successful_borrow_and_authenticated_queries(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)

    borrow_response = _borrow(client, user, book.id)
    all_response = client.get("/api/v1/borrowings/me", headers=_headers(user))
    active_response = client.get("/api/v1/borrowings/me/active", headers=_headers(user))

    assert borrow_response.status_code == 201
    assert borrow_response.json()["status"] == "ACTIVE"
    assert _book_count(session_factory, book.id) == 1
    assert [item["id"] for item in all_response.json()] == [borrow_response.json()["id"]]
    assert [item["id"] for item in active_response.json()] == [borrow_response.json()["id"]]


def test_borrow_rejects_unavailable_book(client: TestClient, session_factory) -> None:
    book = _create_book(session_factory, capacity=1)

    assert _borrow(client, _create_user(session_factory), book.id).status_code == 201
    unavailable = _borrow(client, _create_user(session_factory), book.id)

    assert unavailable.status_code == 409
    assert unavailable.json()["error"]["code"] == "BOOK_NOT_AVAILABLE"


def test_borrow_rejects_five_active_borrowings(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    books = [_create_book(session_factory) for _ in range(6)]

    for book in books[:5]:
        assert _borrow(client, user, book.id).status_code == 201
    limit_response = _borrow(client, user, books[5].id)

    assert limit_response.status_code == 409
    assert limit_response.json()["error"]["code"] == "BORROW_LIMIT_EXCEEDED"


def test_borrow_rejects_duplicate_active_borrowing(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)

    assert _borrow(client, user, book.id).status_code == 201
    duplicate = _borrow(client, user, book.id)

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "ALREADY_BORROWING"


def test_return_releases_slot_and_removes_active_record(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    borrowing = _borrow(client, user, book.id).json()

    returned = client.post(f"/api/v1/borrowings/{borrowing['id']}/return", headers=_headers(user))
    active_response = client.get("/api/v1/borrowings/me/active", headers=_headers(user))

    assert returned.status_code == 200
    assert returned.json()["status"] == "RETURNED"
    assert returned.json()["returned_at"] is not None
    assert _book_count(session_factory, book.id) == 0
    assert active_response.json() == []


def test_return_rejects_unknown_and_already_returned_borrowings(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    borrowing_id = _borrow(client, user, book.id).json()["id"]

    assert client.post("/api/v1/borrowings/99999/return", headers=_headers(user)).status_code == 404
    assert client.post(f"/api/v1/borrowings/{borrowing_id}/return", headers=_headers(user)).status_code == 200
    repeated_return = client.post(f"/api/v1/borrowings/{borrowing_id}/return", headers=_headers(user))

    assert repeated_return.status_code == 409
    assert repeated_return.json()["error"]["code"] == "BORROWING_ALREADY_RETURNED"


def test_return_requires_borrowing_owner(client: TestClient, session_factory) -> None:
    owner = _create_user(session_factory)
    other_user = _create_user(session_factory)
    book = _create_book(session_factory)
    borrowing_id = _borrow(client, owner, book.id).json()["id"]

    forbidden = client.post(f"/api/v1/borrowings/{borrowing_id}/return", headers=_headers(other_user))

    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"
    assert _book_count(session_factory, book.id) == 1


def test_active_borrowing_remains_returnable_after_archive(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    borrowing_id = _borrow(client, user, book.id).json()["id"]
    with session_factory() as session:
        stored_book = session.get(Book, book.id)
        assert stored_book is not None
        stored_book.is_archived = True
        session.commit()

    returned = client.post(f"/api/v1/borrowings/{borrowing_id}/return", headers=_headers(user))

    assert returned.status_code == 200
    assert returned.json()["status"] == "RETURNED"
    assert _book_count(session_factory, book.id) == 0


def test_overdue_is_computed_without_changing_stored_status(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    borrowing_id = _borrow(client, user, book.id, days=-1).json()["id"]

    response = client.get("/api/v1/borrowings/me/active", headers=_headers(user))
    with session_factory() as session:
        stored_status = session.scalar(select(Borrowing.status).where(Borrowing.id == borrowing_id))

    assert response.status_code == 200
    assert response.json()[0]["status"] == "OVERDUE"
    assert stored_status == "ACTIVE"


def test_concurrent_final_slot_borrowing_allows_only_one_success(session_factory) -> None:
    book = _create_book(session_factory, capacity=1)
    users = [_create_user(session_factory), _create_user(session_factory)]
    start = Barrier(2)

    def attempt(user: User) -> str:
        with session_factory() as session:
            start.wait()
            try:
                BorrowingService().borrow(
                    session,
                    user,
                    BorrowingCreate(book_id=book.id, due_date=datetime.now(UTC) + timedelta(days=14)),
                )
                return "success"
            except AppError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, users))

    assert outcomes.count("success") == 1
    assert outcomes.count("BOOK_NOT_AVAILABLE") == 1
    assert _book_count(session_factory, book.id) == 1
