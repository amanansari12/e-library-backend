"""Digital-book upload, replacement, and authorized-access workflows."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.models.book import Book
from app.models.book_file import BookFile
from app.models.borrowing import Borrowing
from app.models.user import User
from app.repositories.book_file import BookFileRepository
from app.services.text_extraction import PDFTextExtractionService
from app.storage.base import BookStorage
from app.storage.local import LocalBookStorage


@dataclass(frozen=True)
class PreparedBookFile:
    original_filename: str
    mime_type: str
    file_size: int
    checksum: str
    extracted_text: str | None
    content: bytes


class BookFileService:
    """Coordinates safe local file operations with database metadata changes."""

    def __init__(
        self,
        repository: BookFileRepository | None = None,
        storage: BookStorage | None = None,
        extractor: PDFTextExtractionService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.repository = repository or BookFileRepository()
        self.settings = settings or get_settings()
        self.storage = storage or LocalBookStorage(self.settings)
        self.extractor = extractor or PDFTextExtractionService()

    def prepare_upload(self, upload: UploadFile) -> PreparedBookFile:
        """Validate a PDF before either database or filesystem mutation."""
        original_filename = Path(upload.filename or "").name
        original_filename = "".join(
            character if character.isalnum() or character in {" ", ".", "-", "_"} else "_"
            for character in original_filename
        )
        if not original_filename or Path(original_filename).suffix.lower() != ".pdf":
            raise AppError(422, "UNSUPPORTED_FILE_TYPE", "Only PDF digital book files are supported")
        if upload.content_type != "application/pdf":
            raise AppError(422, "INVALID_FILE_MIME_TYPE", "The digital book file must use application/pdf")
        content = upload.file.read(self.settings.max_book_file_size_bytes + 1)
        if not content:
            raise AppError(422, "EMPTY_FILE", "The digital book file must not be empty")
        if len(content) > self.settings.max_book_file_size_bytes:
            raise AppError(422, "FILE_TOO_LARGE", "The digital book file exceeds the configured size limit")
        if not content.startswith(b"%PDF-"):
            raise AppError(422, "INVALID_PDF", "The uploaded file is not a valid PDF")
        self.extractor.validate(content)
        return PreparedBookFile(
            original_filename=original_filename[:255],
            mime_type="application/pdf",
            file_size=len(content),
            checksum=sha256(content).hexdigest(),
            extracted_text=self.extractor.extract(content),
            content=content,
        )

    def add_prepared_file(self, db: Session, book: Book, prepared: PreparedBookFile) -> BookFile:
        storage_key = self.storage.save(book.id, prepared.content, extension=".pdf")
        try:
            book_file = BookFile(
                book_id=book.id,
                original_filename=prepared.original_filename,
                storage_key=storage_key,
                mime_type=prepared.mime_type,
                file_size=prepared.file_size,
                file_format="PDF",
                checksum=prepared.checksum,
                extracted_text=prepared.extracted_text,
                is_active=True,
            )
            db.add(book_file)
            return book_file
        except Exception:
            self.storage.delete(storage_key)
            raise

    def replace(self, db: Session, book: Book, upload: UploadFile) -> BookFile:
        """Commit new metadata before removing the old physical file."""
        if book.is_archived:
            raise AppError(409, "BOOK_ARCHIVED", "Archived books cannot have their digital file replaced")
        prepared = self.prepare_upload(upload)
        old_file = self.repository.get_active(db, book.id)
        new_file: BookFile | None = None
        try:
            new_file = self.add_prepared_file(db, book, prepared)
            if old_file is not None:
                old_file.is_active = False
            book.content_version += 1
            db.commit()
            db.refresh(new_file)
        except AppError:
            db.rollback()
            if new_file is not None:
                self.storage.delete(new_file.storage_key)
            raise
        except IntegrityError as exc:
            db.rollback()
            if new_file is not None:
                self.storage.delete(new_file.storage_key)
            raise AppError(409, "CONFLICT", "Unable to replace the digital book file") from exc
        if old_file is not None:
            self.storage.delete(old_file.storage_key)
        return new_file

    def stream_for_active_borrower(self, db: Session, user: User, book_id: int) -> tuple[BookFile, object]:
        """Return a safe byte iterator only to a user with an active borrowing."""
        book = db.get(Book, book_id)
        if book is None:
            raise AppError(404, "BOOK_NOT_FOUND", "Book not found")
        if book.is_archived:
            raise AppError(409, "BOOK_ARCHIVED", "Archived book files are not available")
        active_borrowing = db.scalar(
            select(Borrowing.id).where(
                Borrowing.user_id == user.id,
                Borrowing.book_id == book_id,
                Borrowing.status == "ACTIVE",
            )
        )
        if active_borrowing is None:
            raise AppError(403, "FILE_ACCESS_FORBIDDEN", "An active borrowing is required to access this digital book")
        book_file = self.repository.get_active(db, book_id)
        if book_file is None or not self.storage.exists(book_file.storage_key):
            raise AppError(404, "DIGITAL_FILE_NOT_FOUND", "The digital book file is unavailable")
        return book_file, self.storage.iter_bytes(book_file.storage_key)
