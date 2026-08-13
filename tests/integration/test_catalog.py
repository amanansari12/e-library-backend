from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.reservation import Reservation
from app.models.user import User


def _create_user(session_factory, role: str = "USER") -> User:
    with session_factory() as session:
        user = User(
            email=f"{role.lower()}-{role}-{id(session)}@example.com",
            username=f"{role.lower()}-{id(session)}",
            hashed_password="not-used-in-this-test",
            full_name=f"{role.title()} User",
            role=role,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role)}"}


def _create_author(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post("/api/v1/authors", headers=headers, json={"name": "Octavia Butler"})
    assert response.status_code == 201
    return response.json()["id"]


def _create_category(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/categories", headers=headers, json={"name": "Science Fiction"}
    )
    assert response.status_code == 201
    return response.json()["id"]


def _book_payload(author_id: int, category_id: int) -> dict[str, object]:
    return {
        "title": "Parable of the Sower",
        "isbn": "978-0446675505",
        "description": "A speculative novel.",
        "publication_year": 1993,
        "max_concurrent_borrows": 3,
        "author_ids": [author_id],
        "category_ids": [category_id],
    }


def test_catalog_mutations_require_admin(client: TestClient, session_factory) -> None:
    regular_user = _create_user(session_factory)

    response = client.post("/api/v1/authors", headers=_headers(regular_user), json={"name": "Denied"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_author_category_and_book_crud_with_relationships(client: TestClient, session_factory) -> None:
    admin = _create_user(session_factory, "ADMIN")
    headers = _headers(admin)
    author_id = _create_author(client, headers)
    category_id = _create_category(client, headers)

    create_response = client.post("/api/v1/books", headers=headers, json=_book_payload(author_id, category_id))
    assert create_response.status_code == 201
    book = create_response.json()
    assert book["available_slots"] == 3
    assert book["content_version"] == 1
    assert [author["id"] for author in book["authors"]] == [author_id]
    assert [category["id"] for category in book["categories"]] == [category_id]

    detail_response = client.get(f"/api/v1/books/{book['id']}")
    list_response = client.get("/api/v1/books")
    author_update_response = client.patch(
        f"/api/v1/authors/{author_id}", headers=headers, json={"biography": "Author biography."}
    )
    category_update_response = client.patch(
        f"/api/v1/categories/{category_id}", headers=headers, json={"description": "Genre."}
    )

    assert detail_response.status_code == 200
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert author_update_response.json()["biography"] == "Author biography."
    assert category_update_response.json()["description"] == "Genre."


def test_book_patch_always_increments_content_version(client: TestClient, session_factory) -> None:
    admin = _create_user(session_factory, "ADMIN")
    headers = _headers(admin)
    author_id = _create_author(client, headers)
    category_id = _create_category(client, headers)
    book = client.post("/api/v1/books", headers=headers, json=_book_payload(author_id, category_id)).json()

    first_update = client.patch(f"/api/v1/books/{book['id']}", headers=headers, json={"title": book["title"]})
    second_update = client.patch(
        f"/api/v1/books/{book['id']}", headers=headers, json={"description": "Updated description."}
    )

    assert first_update.status_code == 200
    assert first_update.json()["content_version"] == 2
    assert second_update.status_code == 200
    assert second_update.json()["content_version"] == 3


def test_archive_cancels_active_reservations_and_restore_preserves_book(client: TestClient, session_factory) -> None:
    admin = _create_user(session_factory, "ADMIN")
    headers = _headers(admin)
    author_id = _create_author(client, headers)
    category_id = _create_category(client, headers)
    book = client.post("/api/v1/books", headers=headers, json=_book_payload(author_id, category_id)).json()

    with session_factory() as session:
        session.add(Reservation(user_id=admin.id, book_id=book["id"], position=1, status="PENDING"))
        session.add(Reservation(user_id=admin.id, book_id=book["id"], position=2, status="CANCELLED"))
        session.commit()

    archive_response = client.post(f"/api/v1/books/{book['id']}/archive", headers=headers)
    restore_response = client.post(f"/api/v1/books/{book['id']}/restore", headers=headers)

    with session_factory() as session:
        statuses = list(session.scalars(select(Reservation.status).order_by(Reservation.position)))

    assert archive_response.status_code == 200
    assert archive_response.json()["is_archived"] is True
    assert restore_response.status_code == 200
    assert restore_response.json()["is_archived"] is False
    assert statuses == ["CANCELLED", "CANCELLED"]
