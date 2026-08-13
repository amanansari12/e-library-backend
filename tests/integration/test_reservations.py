from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.exceptions import AppError
from app.models.book import Book
from app.models.reservation import Reservation
from app.schemas.reservation import ReservationCreate
from app.services.catalog import CatalogService
from app.services.reservation import ReservationService
from tests.integration.test_borrowings import _borrow, _create_book, _create_user, _headers


def _make_unavailable(session_factory, book_id: int) -> None:
    with session_factory() as session:
        book = session.get(Book, book_id)
        assert book is not None
        book.current_borrows_count = book.max_concurrent_borrows
        session.commit()


def _reserve(client: TestClient, user, book_id: int):
    return client.post("/api/v1/reservations", headers=_headers(user), json={"book_id": book_id})


def test_successful_reservation_requires_an_unavailable_book(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    available_book = _create_book(session_factory)
    unavailable_book = _create_book(session_factory)
    _make_unavailable(session_factory, unavailable_book.id)

    available_response = _reserve(client, user, available_book.id)
    reservation_response = _reserve(client, user, unavailable_book.id)
    listed = client.get("/api/v1/reservations/me", headers=_headers(user))

    assert available_response.status_code == 409
    assert available_response.json()["error"]["code"] == "BOOK_AVAILABLE"
    assert reservation_response.status_code == 201
    assert reservation_response.json()["position"] == 1
    assert reservation_response.json()["status"] == "PENDING"
    assert [item["id"] for item in listed.json()] == [reservation_response.json()["id"]]


def test_reservation_rejects_an_active_borrower(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory, capacity=1)

    assert _borrow(client, user, book.id).status_code == 201
    response = _reserve(client, user, book.id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ALREADY_BORROWING"


def test_duplicate_pending_and_ready_reservations_are_blocked(client: TestClient, session_factory) -> None:
    borrower = _create_user(session_factory)
    waiting_user = _create_user(session_factory)
    book = _create_book(session_factory, capacity=1)
    borrowing_id = _borrow(client, borrower, book.id).json()["id"]

    assert _reserve(client, waiting_user, book.id).status_code == 201
    pending_duplicate = _reserve(client, waiting_user, book.id)
    assert client.post(f"/api/v1/borrowings/{borrowing_id}/return", headers=_headers(borrower)).status_code == 200
    ready_duplicate = _reserve(client, waiting_user, book.id)

    assert pending_duplicate.status_code == 409
    assert pending_duplicate.json()["error"]["code"] == "DUPLICATE_RESERVATION"
    assert ready_duplicate.status_code == 409
    assert ready_duplicate.json()["error"]["code"] == "DUPLICATE_RESERVATION"


def test_reservation_limit_and_deterministic_positions(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    books = [_create_book(session_factory) for _ in range(4)]
    for book in books:
        _make_unavailable(session_factory, book.id)

    for book in books[:3]:
        assert _reserve(client, user, book.id).status_code == 201
    limit_response = _reserve(client, user, books[3].id)

    queue_book = _create_book(session_factory)
    _make_unavailable(session_factory, queue_book.id)
    queue_users = [_create_user(session_factory) for _ in range(3)]
    positions = [_reserve(client, queue_user, queue_book.id).json()["position"] for queue_user in queue_users]

    assert limit_response.status_code == 409
    assert limit_response.json()["error"]["code"] == "RESERVATION_LIMIT_EXCEEDED"
    assert positions == [1, 2, 3]


def test_user_can_cancel_only_their_own_active_reservation(client: TestClient, session_factory) -> None:
    owner = _create_user(session_factory)
    other_user = _create_user(session_factory)
    book = _create_book(session_factory, capacity=1)
    _make_unavailable(session_factory, book.id)
    reservation_id = _reserve(client, owner, book.id).json()["id"]

    forbidden = client.delete(f"/api/v1/reservations/{reservation_id}", headers=_headers(other_user))
    cancelled = client.delete(f"/api/v1/reservations/{reservation_id}", headers=_headers(owner))

    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"


def test_return_promotes_earliest_pending_with_48_hour_window(client: TestClient, session_factory) -> None:
    borrower = _create_user(session_factory)
    first_waiter = _create_user(session_factory)
    second_waiter = _create_user(session_factory)
    book = _create_book(session_factory, capacity=1)
    borrowing_id = _borrow(client, borrower, book.id).json()["id"]
    first = _reserve(client, first_waiter, book.id).json()
    second = _reserve(client, second_waiter, book.id).json()

    assert client.post(f"/api/v1/borrowings/{borrowing_id}/return", headers=_headers(borrower)).status_code == 200
    with session_factory() as session:
        reservations = list(
            session.scalars(
                select(Reservation)
                .where(Reservation.id.in_((first["id"], second["id"])))
                .order_by(Reservation.position)
            )
        )

    assert [reservation.status for reservation in reservations] == ["READY", "PENDING"]
    assert reservations[0].notified_at is not None
    assert reservations[0].expires_at == reservations[0].notified_at + timedelta(hours=48)


def test_ready_reservation_holds_the_promoted_slot_for_its_owner(client: TestClient, session_factory) -> None:
    borrower = _create_user(session_factory)
    waiting_user = _create_user(session_factory)
    bypass_user = _create_user(session_factory)
    book = _create_book(session_factory, capacity=1)
    borrowing_id = _borrow(client, borrower, book.id).json()["id"]
    _reserve(client, waiting_user, book.id)
    assert client.post(f"/api/v1/borrowings/{borrowing_id}/return", headers=_headers(borrower)).status_code == 200

    bypass_attempt = _borrow(client, bypass_user, book.id)
    fulfilled_attempt = _borrow(client, waiting_user, book.id)
    with session_factory() as session:
        reservation = session.scalar(
            select(Reservation).where(
                Reservation.user_id == waiting_user.id,
                Reservation.book_id == book.id,
            )
        )

    assert bypass_attempt.status_code == 409
    assert bypass_attempt.json()["error"]["code"] == "BOOK_NOT_AVAILABLE"
    assert fulfilled_attempt.status_code == 201
    assert reservation is not None and reservation.status == "FULFILLED"


def test_expired_ready_reservation_is_lazily_expired_and_next_waiter_promoted(
    client: TestClient, session_factory
) -> None:
    borrower = _create_user(session_factory)
    expired_waiter = _create_user(session_factory)
    next_waiter = _create_user(session_factory)
    book = _create_book(session_factory, capacity=1)
    borrowing_id = _borrow(client, borrower, book.id).json()["id"]
    expired_reservation_id = _reserve(client, expired_waiter, book.id).json()["id"]
    next_reservation_id = _reserve(client, next_waiter, book.id).json()["id"]
    assert client.post(f"/api/v1/borrowings/{borrowing_id}/return", headers=_headers(borrower)).status_code == 200
    with session_factory() as session:
        ready = session.get(Reservation, expired_reservation_id)
        assert ready is not None
        ready.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()

    response = client.get("/api/v1/reservations/me", headers=_headers(expired_waiter))
    with session_factory() as session:
        expired = session.get(Reservation, expired_reservation_id)
        promoted = session.get(Reservation, next_reservation_id)

    assert response.status_code == 200
    assert response.json()[0]["status"] == "EXPIRED"
    assert expired is not None and expired.status == "EXPIRED"
    assert promoted is not None and promoted.status == "READY"
    assert promoted.notified_at is not None
    assert promoted.expires_at == promoted.notified_at + timedelta(hours=48)


def test_archiving_cancels_pending_and_ready_reservations_and_blocks_new_ones(
    client: TestClient, session_factory
) -> None:
    borrower = _create_user(session_factory)
    pending_user = _create_user(session_factory)
    ready_user = _create_user(session_factory)
    book = _create_book(session_factory, capacity=1)
    borrowing_id = _borrow(client, borrower, book.id).json()["id"]
    pending_reservation_id = _reserve(client, pending_user, book.id).json()["id"]
    ready_reservation_id = _reserve(client, ready_user, book.id).json()["id"]
    with session_factory() as session:
        ready_reservation = session.get(Reservation, ready_reservation_id)
        assert ready_reservation is not None
        ready_reservation.status = "READY"
        session.commit()
    with session_factory() as session:
        CatalogService().archive_book(session, book.id)
    with session_factory() as session:
        statuses = list(
            session.scalars(
                select(Reservation.status)
                .where(Reservation.id.in_((pending_reservation_id, ready_reservation_id)))
                .order_by(Reservation.id)
            )
        )

    response = _reserve(client, _create_user(session_factory), book.id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BOOK_ARCHIVED"
    assert statuses == ["CANCELLED", "CANCELLED"]
    assert client.post(f"/api/v1/borrowings/{borrowing_id}/return", headers=_headers(borrower)).status_code == 200


def test_concurrent_duplicate_reservation_attempts_create_only_one_active_record(session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    _make_unavailable(session_factory, book.id)
    start = Barrier(2)

    def attempt() -> str:
        with session_factory() as session:
            start.wait()
            try:
                ReservationService().create(session, user, ReservationCreate(book_id=book.id))
                return "success"
            except AppError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: attempt(), range(2)))
    with session_factory() as session:
        active_count = session.scalar(
            select(Reservation).where(
                Reservation.user_id == user.id,
                Reservation.book_id == book.id,
                Reservation.status.in_(("PENDING", "READY")),
            )
        )

    assert outcomes.count("success") == 1
    assert outcomes.count("DUPLICATE_RESERVATION") == 1
    assert active_count is not None
