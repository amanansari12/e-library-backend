"""Integration coverage for atomic multipart bulk catalog creation."""

import json

from app.api.v1 import books as books_api
from app.core.config import Settings
from app.models.book import Book
from app.models.book_file import BookFile
from app.models.category import Category
from app.services.book_file import BookFileService
from tests.integration.test_borrowings import _borrow, _create_user, _headers
from tests.integration.test_catalog import _create_user as _create_catalog_user, _pdf_bytes


def _bulk_authors(client, headers):
    return client.post(
        "/api/v1/authors/bulk",
        headers=headers,
        json={"authors": [{"name": "Author One"}, {"name": "Author Two"}, {"name": "Author Three"}]},
    )


def _bulk_categories(client, headers):
    return client.post(
        "/api/v1/categories/bulk",
        headers=headers,
        json={"categories": [{"name": "Programming"}, {"name": "Architecture"}, {"name": "Testing"}]},
    )


def _configure_storage(monkeypatch, tmp_path) -> BookFileService:
    service = BookFileService(
        settings=Settings(jwt_secret_key="test-secret", book_storage_root=str(tmp_path), max_book_file_size_mb=1)
    )
    monkeypatch.setattr(books_api, "book_file_service", service)
    return service


def _text_pdf_bytes(text: str) -> bytes:
    """Generate a minimal valid PDF with extractable text without a new dependency."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, value in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode() + value + b"\nendobj\n")
    xref_offset = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    content.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    content.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode())
    return bytes(content)


def _bulk_request(client, headers, books, manifest, files):
    return client.post(
        "/api/v1/books/bulk",
        headers=headers,
        data={"books": json.dumps(books), "file_manifest": json.dumps(manifest)},
        files=[("files", (filename, content, mime_type)) for filename, content, mime_type in files],
    )


def test_bulk_authors_and_categories_remain_admin_only(client, session_factory) -> None:
    admin = _create_catalog_user(session_factory, "ADMIN")
    user = _create_user(session_factory)

    assert _bulk_authors(client, _headers(user)).status_code == 403
    assert _bulk_authors(client, _headers(admin)).json()["count"] == 3
    assert _bulk_categories(client, _headers(admin)).json()["count"] == 3


def test_bulk_category_conflict_rolls_back_entire_batch(client, session_factory) -> None:
    admin = _create_catalog_user(session_factory, "ADMIN")
    response = client.post(
        "/api/v1/categories/bulk",
        headers=_headers(admin),
        json={"categories": [{"name": "Would Roll Back"}, {"name": "Would Roll Back"}]},
    )
    with session_factory() as session:
        assert session.query(Category).filter_by(name="Would Roll Back").count() == 0
    assert response.status_code == 409


def test_admin_creates_atomic_bulk_books_with_mapped_pdfs(client, session_factory, monkeypatch, tmp_path) -> None:
    storage_service = _configure_storage(monkeypatch, tmp_path)
    admin = _create_catalog_user(session_factory, "ADMIN")
    headers = _headers(admin)
    authors = _bulk_authors(client, headers).json()["created"]
    categories = _bulk_categories(client, headers).json()["created"]
    books = [
        {"title": "Bulk One", "isbn": "bulk-file-001", "author_ids": [authors[0]["id"], authors[1]["id"]], "category_ids": [categories[0]["id"]], "file_key": "bulk_one"},
        {"title": "Bulk Two", "isbn": "bulk-file-002", "author_ids": [authors[0]["id"]], "category_ids": [categories[0]["id"], categories[1]["id"]], "file_key": "bulk_two"},
    ]
    response = _bulk_request(
        client,
        headers,
        books,
        {"bulk_one": "bulk-one.pdf", "bulk_two": "bulk-two.pdf"},
        [("bulk-one.pdf", _text_pdf_bytes("Bulk One extracted text"), "application/pdf"), ("bulk-two.pdf", _text_pdf_bytes("Bulk Two extracted text"), "application/pdf")],
    )

    assert response.status_code == 201
    assert response.json()["count"] == 2
    assert [item["has_digital_copy"] for item in response.json()["created"]] == [True, True]
    with session_factory() as session:
        created = session.query(Book).filter(Book.isbn.in_(("bulk-file-001", "bulk-file-002"))).order_by(Book.isbn).all()
        files = session.query(BookFile).filter(BookFile.book_id.in_([book.id for book in created])).order_by(BookFile.book_id).all()
        assert len(created) == len(files) == 2
        assert all(book.content_version == 1 and book.current_borrows_count == 0 and not book.is_archived for book in created)
        assert all(book_file.checksum and book_file.extracted_text and book_file.is_active for book_file in files)
        assert all(storage_service.storage.exists(book_file.storage_key) for book_file in files)
        assert {author.id for author in created[0].authors} == {authors[0]["id"], authors[1]["id"]}

    borrower = _create_user(session_factory)
    other_user = _create_user(session_factory)
    assert _borrow(client, borrower, created[0].id).status_code == 201
    assert client.get(f"/api/v1/books/{created[0].id}/file", headers=_headers(borrower)).status_code == 200
    assert client.get(f"/api/v1/books/{created[0].id}/file", headers=_headers(other_user)).status_code == 403


def test_bulk_batch_validation_is_atomic_and_cleans_up_files(client, session_factory, monkeypatch, tmp_path) -> None:
    _configure_storage(monkeypatch, tmp_path)
    admin = _create_catalog_user(session_factory, "ADMIN")
    headers = _headers(admin)
    author_id = _bulk_authors(client, headers).json()["created"][0]["id"]
    category_id = _bulk_categories(client, headers).json()["created"][0]["id"]
    books = [
        {"title": "Would Be Valid", "isbn": "bulk-atomic-001", "author_ids": [author_id], "category_ids": [category_id], "file_key": "valid"},
        {"title": "Invalid PDF", "isbn": "bulk-atomic-002", "author_ids": [author_id], "category_ids": [category_id], "file_key": "invalid"},
    ]
    invalid_pdf = _bulk_request(
        client,
        headers,
        books,
        {"valid": "valid.pdf", "invalid": "invalid.pdf"},
        [("valid.pdf", _pdf_bytes(), "application/pdf"), ("invalid.pdf", b"not a PDF", "application/pdf")],
    )
    with session_factory() as session:
        assert session.query(Book).filter(Book.isbn.in_(("bulk-atomic-001", "bulk-atomic-002"))).count() == 0
        assert session.query(BookFile).count() == 0
    assert invalid_pdf.status_code == 422
    assert invalid_pdf.json()["error"]["code"] == "INVALID_PDF"
    assert list(tmp_path.rglob("*")) == []


def test_bulk_file_mapping_isbns_references_and_authorization_are_enforced(client, session_factory, monkeypatch, tmp_path) -> None:
    _configure_storage(monkeypatch, tmp_path)
    admin = _create_catalog_user(session_factory, "ADMIN")
    user = _create_user(session_factory)
    headers = _headers(admin)
    author_id = _bulk_authors(client, headers).json()["created"][0]["id"]
    category_id = _bulk_categories(client, headers).json()["created"][0]["id"]
    base = {"title": "Check", "isbn": "bulk-check", "author_ids": [author_id], "category_ids": [category_id], "file_key": "check"}
    missing_mapping = _bulk_request(client, headers, [base], {}, [("check.pdf", _pdf_bytes(), "application/pdf")])
    duplicate_isbn = _bulk_request(
        client,
        headers,
        [base, {**base, "title": "Duplicate", "file_key": "second"}],
        {"check": "check.pdf", "second": "second.pdf"},
        [("check.pdf", _pdf_bytes(), "application/pdf"), ("second.pdf", _pdf_bytes(), "application/pdf")],
    )
    bad_author = _bulk_request(
        client,
        headers,
        [{**base, "isbn": "bulk-bad-author", "author_ids": [99999]}],
        {"check": "check.pdf"},
        [("check.pdf", _pdf_bytes(), "application/pdf")],
    )
    forbidden = _bulk_request(client, _headers(user), [base], {"check": "check.pdf"}, [("check.pdf", _pdf_bytes(), "application/pdf")])

    assert missing_mapping.json()["error"]["code"] == "INVALID_FILE_MAPPING"
    assert duplicate_isbn.json()["error"]["code"] == "DUPLICATE_ISBN"
    assert bad_author.json()["error"]["code"] == "AUTHOR_NOT_FOUND"
    assert forbidden.status_code == 403
