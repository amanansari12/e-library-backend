from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.exceptions import AppError
from app.models.book import Book
from app.models.favorite import Favorite
from app.schemas.favorite import FavoriteCreate
from app.services.catalog import CatalogService
from app.services.favorite import FavoriteService
from tests.integration.test_borrowings import _create_book, _create_user, _headers


def _favorite(client: TestClient, user, book_id: int):
    return client.post("/api/v1/favorites", headers=_headers(user), json={"book_id": book_id})


def test_authenticated_user_can_add_a_favorite(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)

    unauthenticated = client.post("/api/v1/favorites", json={"book_id": book.id})
    response = _favorite(client, user, book.id)
    with session_factory() as session:
        favorite = session.scalar(
            select(Favorite).where(Favorite.user_id == user.id, Favorite.book_id == book.id)
        )

    assert unauthenticated.status_code == 401
    assert response.status_code == 201
    assert response.json()["user_id"] == user.id
    assert response.json()["book_id"] == book.id
    assert favorite is not None


def test_favorite_rejects_missing_archived_and_duplicate_books(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    favorite_book = _create_book(session_factory)
    archived_book = _create_book(session_factory)
    with session_factory() as session:
        CatalogService().archive_book(session, archived_book.id)

    missing = _favorite(client, user, 99999)
    assert _favorite(client, user, favorite_book.id).status_code == 201
    duplicate = _favorite(client, user, favorite_book.id)
    archived = _favorite(client, user, archived_book.id)

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "BOOK_NOT_FOUND"
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_FAVORITE"
    assert archived.status_code == 409
    assert archived.json()["error"]["code"] == "BOOK_ARCHIVED"


def test_favorites_list_and_status_are_specific_to_authenticated_user(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    other_user = _create_user(session_factory)
    first_book = _create_book(session_factory)
    second_book = _create_book(session_factory)
    assert _favorite(client, user, first_book.id).status_code == 201
    assert _favorite(client, other_user, second_book.id).status_code == 201

    user_list = client.get("/api/v1/favorites/me", headers=_headers(user))
    other_list = client.get("/api/v1/favorites/me", headers=_headers(other_user))
    favorited = client.get(f"/api/v1/favorites/check/{first_book.id}", headers=_headers(user))
    not_favorited = client.get(f"/api/v1/favorites/check/{second_book.id}", headers=_headers(user))
    missing = client.get("/api/v1/favorites/check/99999", headers=_headers(user))

    assert [item["book_id"] for item in user_list.json()] == [first_book.id]
    assert [item["book_id"] for item in other_list.json()] == [second_book.id]
    assert favorited.json() == {"book_id": first_book.id, "is_favorited": True}
    assert not_favorited.json() == {"book_id": second_book.id, "is_favorited": False}
    assert missing.status_code == 404


def test_user_can_remove_only_their_own_favorite(client: TestClient, session_factory) -> None:
    owner = _create_user(session_factory)
    other_user = _create_user(session_factory)
    book = _create_book(session_factory)
    assert _favorite(client, owner, book.id).status_code == 201

    other_delete = client.delete(f"/api/v1/favorites/{book.id}", headers=_headers(other_user))
    owner_delete = client.delete(f"/api/v1/favorites/{book.id}", headers=_headers(owner))
    repeated_delete = client.delete(f"/api/v1/favorites/{book.id}", headers=_headers(owner))

    assert other_delete.status_code == 404
    assert other_delete.json()["error"]["code"] == "FAVORITE_NOT_FOUND"
    assert owner_delete.status_code == 204
    assert repeated_delete.status_code == 404


def test_existing_favorite_remains_stored_after_book_is_archived(client: TestClient, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    assert _favorite(client, user, book.id).status_code == 201
    with session_factory() as session:
        CatalogService().archive_book(session, book.id)

    listed = client.get("/api/v1/favorites/me", headers=_headers(user))
    status = client.get(f"/api/v1/favorites/check/{book.id}", headers=_headers(user))

    assert [item["book_id"] for item in listed.json()] == [book.id]
    assert status.json()["is_favorited"] is True


def test_concurrent_duplicate_favorite_creation_creates_one_row(session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    start = Barrier(2)

    def attempt() -> str:
        with session_factory() as session:
            start.wait()
            try:
                FavoriteService().create(session, user, FavoriteCreate(book_id=book.id))
                return "success"
            except AppError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: attempt(), range(2)))
    with session_factory() as session:
        count = session.scalar(
            select(func.count(Favorite.id)).where(Favorite.user_id == user.id, Favorite.book_id == book.id)
        )

    assert outcomes.count("success") == 1
    assert outcomes.count("DUPLICATE_FAVORITE") == 1
    assert count == 1
