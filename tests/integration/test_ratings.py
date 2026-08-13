from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.exceptions import AppError
from app.models.rating import Rating
from app.schemas.rating import RatingCreate
from app.services.catalog import CatalogService
from app.services.rating import RatingService
from tests.integration.test_borrowings import _create_book, _create_user, _headers


def _rate(client: TestClient, user, book_id: int, score: int):
    return client.post(
        "/api/v1/ratings",
        headers=_headers(user),
        json={"book_id": book_id, "score": score},
    )


def test_authenticated_user_can_create_rating_with_valid_score(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)

    unauthenticated = client.post("/api/v1/ratings", json={"book_id": book.id, "score": 5})
    response = _rate(client, user, book.id, 5)
    with session_factory() as session:
        stored_rating = session.scalar(
            select(Rating).where(Rating.user_id == user.id, Rating.book_id == book.id)
        )

    assert unauthenticated.status_code == 401
    assert response.status_code == 201
    assert response.json()["score"] == 5
    assert stored_rating is not None and stored_rating.score == 5


def test_rating_rejects_missing_book_and_invalid_scores(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)

    missing = _rate(client, user, 99999, 3)
    below_range = _rate(client, user, book.id, 0)
    above_range = _rate(client, user, book.id, 6)
    non_integer = client.post(
        "/api/v1/ratings", headers=_headers(user), json={"book_id": book.id, "score": 3.5}
    )

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "BOOK_NOT_FOUND"
    assert below_range.status_code == 422
    assert above_range.status_code == 422
    assert non_integer.status_code == 422


def test_rating_post_updates_existing_user_rating_without_second_row(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)

    first = _rate(client, user, book.id, 2)
    updated = _rate(client, user, book.id, 5)
    with session_factory() as session:
        ratings = list(
            session.scalars(select(Rating).where(Rating.user_id == user.id, Rating.book_id == book.id))
        )

    assert first.status_code == 201
    assert updated.status_code == 201
    assert updated.json()["id"] == first.json()["id"]
    assert updated.json()["score"] == 5
    assert len(ratings) == 1
    assert ratings[0].score == 5


def test_book_ratings_sql_aggregates_and_book_detail_follow_mutations(client: TestClient, session_factory) -> None:
    first_user = _create_user(session_factory)
    second_user = _create_user(session_factory)
    book = _create_book(session_factory)

    empty = client.get(f"/api/v1/ratings/books/{book.id}")
    assert empty.json() == {"book_id": book.id, "items": [], "average_rating": None, "rating_count": 0}
    assert _rate(client, first_user, book.id, 5).status_code == 201
    assert _rate(client, second_user, book.id, 3).status_code == 201
    combined = client.get(f"/api/v1/ratings/books/{book.id}")
    detail = client.get(f"/api/v1/books/{book.id}")
    assert _rate(client, second_user, book.id, 1).status_code == 201
    updated = client.get(f"/api/v1/ratings/books/{book.id}")
    assert client.delete(f"/api/v1/ratings/{book.id}", headers=_headers(first_user)).status_code == 204
    deleted = client.get(f"/api/v1/ratings/books/{book.id}")

    assert combined.json()["average_rating"] == 4.0
    assert combined.json()["rating_count"] == 2
    assert detail.json()["average_rating"] == 4.0
    assert detail.json()["rating_count"] == 2
    assert updated.json()["average_rating"] == 3.0
    assert updated.json()["rating_count"] == 2
    assert deleted.json()["average_rating"] == 1.0
    assert deleted.json()["rating_count"] == 1


def test_rating_lists_and_deletion_are_scoped_to_current_user(client: TestClient, session_factory) -> None:
    owner = _create_user(session_factory)
    other_user = _create_user(session_factory)
    owner_book = _create_book(session_factory)
    other_book = _create_book(session_factory)
    assert _rate(client, owner, owner_book.id, 4).status_code == 201
    assert _rate(client, other_user, other_book.id, 2).status_code == 201

    owner_list = client.get("/api/v1/ratings/me", headers=_headers(owner))
    other_list = client.get("/api/v1/ratings/me", headers=_headers(other_user))
    denied_delete = client.delete(f"/api/v1/ratings/{owner_book.id}", headers=_headers(other_user))
    owner_delete = client.delete(f"/api/v1/ratings/{owner_book.id}", headers=_headers(owner))
    repeated_delete = client.delete(f"/api/v1/ratings/{owner_book.id}", headers=_headers(owner))

    assert [rating["book_id"] for rating in owner_list.json()] == [owner_book.id]
    assert [rating["book_id"] for rating in other_list.json()] == [other_book.id]
    assert denied_delete.status_code == 404
    assert denied_delete.json()["error"]["code"] == "RATING_NOT_FOUND"
    assert owner_delete.status_code == 204
    assert repeated_delete.status_code == 404


def test_archived_book_retains_historical_ratings(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    assert _rate(client, user, book.id, 4).status_code == 201
    with session_factory() as session:
        CatalogService().archive_book(session, book.id)

    ratings = client.get(f"/api/v1/ratings/books/{book.id}")
    own_ratings = client.get("/api/v1/ratings/me", headers=_headers(user))

    assert ratings.json()["rating_count"] == 1
    assert ratings.json()["average_rating"] == 4.0
    assert [rating["book_id"] for rating in own_ratings.json()] == [book.id]


def test_concurrent_rating_creation_leaves_one_user_book_row(session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    start = Barrier(2)

    def attempt(score: int) -> str:
        with session_factory() as session:
            start.wait()
            try:
                RatingService().create_or_update(session, user, RatingCreate(book_id=book.id, score=score))
                return "success"
            except AppError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, (2, 5)))
    with session_factory() as session:
        count = session.scalar(
            select(func.count(Rating.id)).where(Rating.user_id == user.id, Rating.book_id == book.id)
        )

    assert outcomes.count("success") == 1
    assert outcomes.count("DUPLICATE_RATING") == 1
    assert count == 1
