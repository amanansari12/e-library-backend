"""End-to-end coverage for mandatory digital-book files and access control."""

from app.api.v1 import books as books_api
from app.core.config import Settings
from app.models.book_file import BookFile
from app.services.book_file import BookFileService
from tests.integration.test_borrowings import _borrow, _create_user, _headers
from tests.integration.test_catalog import (
    _create_author,
    _create_book,
    _create_category,
    _create_user as _create_catalog_user,
    _pdf_bytes,
)


def _configure_storage(monkeypatch, tmp_path) -> BookFileService:
    service = BookFileService(
        settings=Settings(
            jwt_secret_key="test-secret",
            book_storage_root=str(tmp_path),
            max_book_file_size_mb=1,
        )
    )
    monkeypatch.setattr(books_api, "book_file_service", service)
    return service


def _create_uploaded_book(client, session_factory, monkeypatch, tmp_path):
    storage_service = _configure_storage(monkeypatch, tmp_path)
    admin = _create_catalog_user(session_factory, role="ADMIN")
    headers = _headers(admin)
    author_id = _create_author(client, headers)
    category_id = _create_category(client, headers)
    response = _create_book(client, headers, author_id, category_id)
    assert response.status_code == 201
    return storage_service, admin, response.json()


def test_admin_uploads_replaces_and_borrower_streams_digital_file(client, session_factory, monkeypatch, tmp_path) -> None:
    storage_service, admin, book = _create_uploaded_book(client, session_factory, monkeypatch, tmp_path)
    with session_factory() as session:
        old_file = session.query(BookFile).filter_by(book_id=book["id"], is_active=True).one()
        old_key = old_file.storage_key
        assert old_file.checksum
        assert old_file.file_size > 0
        assert storage_service.storage.exists(old_key)

    borrower = _create_user(session_factory)
    other_user = _create_user(session_factory)
    borrowing = _borrow(client, borrower, book["id"])
    assert borrowing.status_code == 201
    allowed = client.get(f"/api/v1/books/{book['id']}/file", headers=_headers(borrower))
    denied = client.get(f"/api/v1/books/{book['id']}/file", headers=_headers(other_user))
    replacement = client.post(
        f"/api/v1/books/{book['id']}/file",
        headers=_headers(admin),
        files={"file": ("replacement.pdf", _pdf_bytes(), "application/pdf")},
    )

    assert allowed.status_code == 200
    assert allowed.headers["content-type"].startswith("application/pdf")
    assert allowed.content.startswith(b"%PDF-")
    assert denied.status_code == 403
    assert replacement.status_code == 200
    assert replacement.json()["content_version"] == 2
    assert replacement.json()["digital_file"]["original_filename"] == "replacement.pdf"
    assert storage_service.storage.exists(old_key) is False
    returned = client.post(
        f"/api/v1/borrowings/{borrowing.json()['id']}/return", headers=_headers(borrower)
    )
    revoked = client.get(f"/api/v1/books/{book['id']}/file", headers=_headers(borrower))
    assert returned.status_code == 200
    assert revoked.status_code == 403
    with session_factory() as session:
        files = session.query(BookFile).filter_by(book_id=book["id"]).order_by(BookFile.id).all()
        assert [book_file.is_active for book_file in files] == [False, True]


def test_file_validation_and_missing_file_errors_do_not_create_invalid_books(client, session_factory, monkeypatch, tmp_path) -> None:
    _configure_storage(monkeypatch, tmp_path)
    admin = _create_catalog_user(session_factory, role="ADMIN")
    headers = _headers(admin)
    author_id = _create_author(client, headers)
    category_id = _create_category(client, headers)
    form_data = {"title": "Invalid File", "isbn": "invalid-file-book", "author_ids": str(author_id), "category_ids": str(category_id)}

    empty = client.post("/api/v1/books", headers=headers, data=form_data, files={"file": ("empty.pdf", b"", "application/pdf")})
    invalid_signature = client.post("/api/v1/books", headers=headers, data=form_data, files={"file": ("bad.pdf", b"not a PDF", "application/pdf")})
    invalid_mime = client.post("/api/v1/books", headers=headers, data=form_data, files={"file": ("bad.pdf", _pdf_bytes(), "text/plain")})
    oversized = client.post("/api/v1/books", headers=headers, data=form_data, files={"file": ("large.pdf", b"%PDF-" + b"x" * (1024 * 1024), "application/pdf")})
    user = _create_user(session_factory)
    forbidden = client.post("/api/v1/books", headers=_headers(user), data=form_data, files={"file": ("book.pdf", _pdf_bytes(), "application/pdf")})

    assert empty.json()["error"]["code"] == "EMPTY_FILE"
    assert invalid_signature.json()["error"]["code"] == "INVALID_PDF"
    assert invalid_mime.json()["error"]["code"] == "INVALID_FILE_MIME_TYPE"
    assert oversized.json()["error"]["code"] == "FILE_TOO_LARGE"
    assert forbidden.status_code == 403


def test_archived_or_missing_physical_files_cannot_be_streamed(client, session_factory, monkeypatch, tmp_path) -> None:
    storage_service, admin, book = _create_uploaded_book(client, session_factory, monkeypatch, tmp_path)
    borrower = _create_user(session_factory)
    assert _borrow(client, borrower, book["id"]).status_code == 201
    with session_factory() as session:
        book_file = session.query(BookFile).filter_by(book_id=book["id"], is_active=True).one()
        storage_service.storage.delete(book_file.storage_key)

    missing = client.get(f"/api/v1/books/{book['id']}/file", headers=_headers(borrower))
    archived = client.post(f"/api/v1/books/{book['id']}/archive", headers=_headers(admin))
    archived_access = client.get(f"/api/v1/books/{book['id']}/file", headers=_headers(borrower))

    assert missing.status_code == 404
    assert archived.status_code == 200
    assert archived_access.status_code == 409
