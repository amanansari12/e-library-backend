from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import func, select

from app.core.exceptions import AppError
from app.models.author import Author
from app.models.book import Book
from app.models.book_summary import BookSummary
from app.models.category import Category
from app.schemas.book import BookCreate, BulkBookCreate
from app.services.catalog import CatalogService
from tests.integration.test_catalog import _create_user, _headers


def _bulk_authors(client, headers):
    return client.post(
        "/api/v1/authors/bulk",
        headers=headers,
        json={
            "authors": [
                {"name": "Author One", "biography": "First author"},
                {"name": "Author Two", "biography": "Second author"},
                {"name": "Author Three", "biography": "Third author"},
            ]
        },
    )


def _bulk_categories(client, headers):
    return client.post(
        "/api/v1/categories/bulk",
        headers=headers,
        json={
            "categories": [
                {"name": "Programming", "description": "Programming books"},
                {"name": "Architecture", "description": "Architecture books"},
                {"name": "Testing", "description": "Testing books"},
            ]
        },
    )


def test_bulk_authors_and_categories_are_admin_only_and_validate_batch_size(client, session_factory) -> None:
    admin = _create_user(session_factory, "ADMIN")
    user = _create_user(session_factory)

    forbidden = _bulk_authors(client, _headers(user))
    authors = _bulk_authors(client, _headers(admin))
    categories = _bulk_categories(client, _headers(admin))
    empty = client.post("/api/v1/categories/bulk", headers=_headers(admin), json={"categories": []})
    too_many = client.post(
        "/api/v1/authors/bulk",
        headers=_headers(admin),
        json={"authors": [{"name": f"Author {index}"} for index in range(51)]},
    )

    assert forbidden.status_code == 403
    assert authors.status_code == 201 and authors.json()["count"] == 3
    assert categories.status_code == 201 and categories.json()["count"] == 3
    assert empty.status_code == 422
    assert too_many.status_code == 422
    assert too_many.json()["error"]["code"] == "BATCH_TOO_LARGE"


def test_bulk_category_conflict_rolls_back_entire_batch(client, session_factory) -> None:
    admin = _create_user(session_factory, "ADMIN")
    response = client.post(
        "/api/v1/categories/bulk",
        headers=_headers(admin),
        json={
            "categories": [
                {"name": "Would Roll Back", "description": "First"},
                {"name": "Would Roll Back", "description": "Duplicate"},
            ]
        },
    )
    with session_factory() as session:
        count = session.scalar(select(func.count(Category.id)).where(Category.name == "Would Roll Back"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    assert count == 0


def test_bulk_books_create_shared_many_to_many_relationships_and_normal_defaults(client, session_factory) -> None:
    admin = _create_user(session_factory, "ADMIN")
    headers = _headers(admin)
    authors = _bulk_authors(client, headers).json()["created"]
    categories = _bulk_categories(client, headers).json()["created"]
    response = client.post(
        "/api/v1/books/bulk",
        headers=headers,
        json={
            "books": [
                {
                    "title": "Shared Relationships",
                    "isbn": "bulk-shared-001",
                    "description": "First bulk book.",
                    "content": "Bulk source content.",
                    "publication_year": 2024,
                    "max_concurrent_borrows": 3,
                    "author_ids": [authors[0]["id"], authors[1]["id"]],
                    "category_ids": [categories[0]["id"], categories[1]["id"]],
                },
                {
                    "title": "Same Author and Category",
                    "isbn": "bulk-shared-002",
                    "description": "Second bulk book.",
                    "author_ids": [authors[0]["id"]],
                    "category_ids": [categories[0]["id"]],
                },
                {
                    "title": "Another Shared Book",
                    "isbn": "bulk-shared-003",
                    "description": "Third bulk book.",
                    "author_ids": [authors[0]["id"]],
                    "category_ids": [categories[0]["id"]],
                },
            ]
        },
    )
    books = response.json()["created"]
    with session_factory() as session:
        author = session.get(Author, authors[0]["id"])
        category = session.get(Category, categories[0]["id"])
        summary_count = session.scalar(select(func.count(BookSummary.id)))
        assert author is not None and category is not None
        author_book_count = len(author.books)
        category_book_count = len(category.books)

    assert response.status_code == 201
    assert response.json()["count"] == 3
    assert [author["id"] for author in books[0]["authors"]] == [authors[0]["id"], authors[1]["id"]]
    assert [category["id"] for category in books[0]["categories"]] == [categories[0]["id"], categories[1]["id"]]
    assert all(book["content_version"] == 1 for book in books)
    assert all(book["current_borrows_count"] == 0 and book["is_archived"] is False for book in books)
    assert author_book_count == 3
    assert category_book_count == 3
    assert summary_count == 0


def test_bulk_books_reject_bad_references_and_duplicate_isbns_atomically(client, session_factory) -> None:
    admin = _create_user(session_factory, "ADMIN")
    headers = _headers(admin)
    author_id = _bulk_authors(client, headers).json()["created"][0]["id"]
    category_id = _bulk_categories(client, headers).json()["created"][0]["id"]
    invalid_reference = client.post(
        "/api/v1/books/bulk",
        headers=headers,
        json={
            "books": [
                {"title": "Valid Before Failure", "isbn": "bulk-rollback-001", "author_ids": [author_id], "category_ids": [category_id]},
                {"title": "Invalid Author", "isbn": "bulk-rollback-002", "author_ids": [99999], "category_ids": [category_id]},
            ]
        },
    )
    duplicate_isbn = client.post(
        "/api/v1/books/bulk",
        headers=headers,
        json={
            "books": [
                {"title": "Duplicate One", "isbn": "bulk-duplicate-isbn", "author_ids": [author_id], "category_ids": [category_id]},
                {"title": "Duplicate Two", "isbn": "bulk-duplicate-isbn", "author_ids": [author_id], "category_ids": [category_id]},
            ]
        },
    )
    with session_factory() as session:
        count = session.scalar(
            select(func.count(Book.id)).where(Book.isbn.in_(("bulk-rollback-001", "bulk-rollback-002", "bulk-duplicate-isbn")))
        )

    assert invalid_reference.status_code == 404
    assert invalid_reference.json()["error"]["code"] == "AUTHOR_NOT_FOUND"
    assert duplicate_isbn.status_code == 409
    assert duplicate_isbn.json()["error"]["code"] == "DUPLICATE_ISBN"
    assert count == 0


def test_bulk_books_preserve_single_create_and_database_isbn_protection(client, session_factory) -> None:
    admin = _create_user(session_factory, "ADMIN")
    headers = _headers(admin)
    author_id = _bulk_authors(client, headers).json()["created"][0]["id"]
    category_id = _bulk_categories(client, headers).json()["created"][0]["id"]
    single = client.post(
        "/api/v1/books",
        headers=headers,
        json={"title": "Single Still Works", "isbn": "bulk-existing-isbn", "author_ids": [author_id], "category_ids": [category_id]},
    )
    existing = client.post(
        "/api/v1/books/bulk",
        headers=headers,
        json={
            "books": [
                {"title": "Existing ISBN", "isbn": "bulk-existing-isbn", "author_ids": [author_id], "category_ids": [category_id]},
                {"title": "Would Roll Back", "isbn": "bulk-never-created", "author_ids": [author_id], "category_ids": [category_id]},
            ]
        },
    )
    forbidden = client.post("/api/v1/books/bulk", headers=_headers(_create_user(session_factory)), json={"books": []})
    with session_factory() as session:
        never_created = session.scalar(select(Book).where(Book.isbn == "bulk-never-created"))

    assert single.status_code == 201
    assert existing.status_code == 409
    assert forbidden.status_code == 403
    assert never_created is None


def test_concurrent_bulk_book_requests_cannot_create_duplicate_isbns(session_factory) -> None:
    admin = _create_user(session_factory, "ADMIN")
    with session_factory() as session:
        author = Author(name="Concurrency Author")
        category = Category(name="Concurrency Category")
        session.add_all((author, category))
        session.commit()
        session.refresh(author)
        session.refresh(category)
        author_id, category_id = author.id, category.id
    payload = BulkBookCreate(
        books=[BookCreate(title="Concurrent Bulk Book", isbn="bulk-concurrent-isbn", author_ids=[author_id], category_ids=[category_id])]
    )
    start = Barrier(2)

    def create() -> str:
        with session_factory() as session:
            start.wait()
            try:
                CatalogService().create_books_bulk(session, payload)
                return "success"
            except AppError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: create(), range(2)))
    with session_factory() as session:
        count = session.scalar(select(func.count(Book.id)).where(Book.isbn == "bulk-concurrent-isbn"))

    assert outcomes.count("success") == 1
    assert outcomes.count("CONFLICT") == 1
    assert count == 1
