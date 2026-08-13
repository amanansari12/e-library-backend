from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.book import Book
from app.models.user import User


def _admin_headers(session_factory) -> dict[str, str]:
    with session_factory() as session:
        admin = User(
            email=f"search-admin-{id(session)}@example.com",
            username=f"search-admin-{id(session)}",
            hashed_password="not-used",
            full_name="Search Admin",
            role="ADMIN",
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        return {"Authorization": f"Bearer {create_access_token(admin.id, admin.role)}"}


def _build_catalog(client: TestClient, session_factory) -> dict[str, int]:
    headers = _admin_headers(session_factory)
    author_one = client.post("/api/v1/authors", headers=headers, json={"name": "Author One"}).json()["id"]
    author_two = client.post("/api/v1/authors", headers=headers, json={"name": "Author Two"}).json()["id"]
    category_one = client.post("/api/v1/categories", headers=headers, json={"name": "Adventure"}).json()["id"]
    category_two = client.post("/api/v1/categories", headers=headers, json={"name": "History"}).json()["id"]
    book_ids: list[int] = []
    for title, isbn, year, author_id, category_id, capacity in (
        ("Alpha Book", "isbn-alpha", 2000, author_one, category_one, 2),
        ("Beta Book", "isbn-beta", 2005, author_one, category_two, 1),
        ("Gamma Book", "isbn-gamma", 2010, author_two, category_one, 3),
    ):
        response = client.post(
            "/api/v1/books",
            headers=headers,
            json={
                "title": title,
                "isbn": isbn,
                "description": f"Description for {title}",
                "publication_year": year,
                "max_concurrent_borrows": capacity,
                "author_ids": [author_id],
                "category_ids": [category_id],
            },
        )
        assert response.status_code == 201
        book_ids.append(response.json()["id"])
    with session_factory() as session:
        beta = session.get(Book, book_ids[1])
        assert beta is not None
        beta.current_borrows_count = beta.max_concurrent_borrows
        session.commit()
    return {
        "author_one": author_one,
        "author_two": author_two,
        "category_one": category_one,
        "category_two": category_two,
    }


def test_search_filters_and_year_range(client: TestClient, session_factory) -> None:
    ids = _build_catalog(client, session_factory)

    keyword = client.get("/api/v1/books", params={"q": "gamma"}).json()
    by_author = client.get("/api/v1/books", params={"author_id": ids["author_one"]}).json()
    combined = client.get(
        "/api/v1/books",
        params={"author_id": ids["author_one"], "category_id": ids["category_one"]},
    ).json()
    year_range = client.get("/api/v1/books", params={"year_from": 2005, "year_to": 2010}).json()
    unavailable = client.get("/api/v1/books", params={"available": "false"}).json()
    available = client.get("/api/v1/books", params={"available": "true"}).json()

    assert [book["title"] for book in keyword["items"]] == ["Gamma Book"]
    assert by_author["total"] == 2
    assert [book["title"] for book in combined["items"]] == ["Alpha Book"]
    assert [book["title"] for book in year_range["items"]] == ["Beta Book", "Gamma Book"]
    assert [book["title"] for book in unavailable["items"]] == ["Beta Book"]
    assert available["total"] == 2


def test_sorting_pagination_empty_results_and_invalid_values(client: TestClient, session_factory) -> None:
    _build_catalog(client, session_factory)

    first_page = client.get(
        "/api/v1/books", params={"sort_by": "title", "sort_order": "asc", "page": 1, "page_size": 1}
    ).json()
    second_page = client.get(
        "/api/v1/books", params={"sort_by": "title", "sort_order": "asc", "page": 2, "page_size": 1}
    ).json()
    descending = client.get("/api/v1/books", params={"sort_order": "desc"}).json()
    empty = client.get("/api/v1/books", params={"q": "not-present"}).json()

    assert first_page["total"] == 3
    assert first_page["pages"] == 3
    assert [book["title"] for book in first_page["items"]] == ["Alpha Book"]
    assert [book["title"] for book in second_page["items"]] == ["Beta Book"]
    assert [book["title"] for book in descending["items"]] == ["Gamma Book", "Beta Book", "Alpha Book"]
    assert empty == {"items": [], "total": 0, "page": 1, "page_size": 20, "pages": 0}
    assert client.get("/api/v1/books", params={"page": 0}).status_code == 422
    assert client.get("/api/v1/books", params={"sort_by": "unknown"}).status_code == 422
    assert client.get("/api/v1/books", params={"year_from": 2020, "year_to": 2000}).status_code == 422
