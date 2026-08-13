"""Local filesystem implementation of the book-file storage abstraction."""

from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from uuid import uuid4

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError


class LocalBookStorage:
    """Stores generated keys under one controlled local filesystem root."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.root = Path(self.settings.book_storage_root).resolve()

    def save(self, book_id: int, content: bytes, *, extension: str) -> str:
        """Save bytes using a generated key and return that safe relative key."""
        asset_id = uuid4().hex
        storage_key = f"books/{book_id}/{asset_id}/original{extension}"
        path = self._path_for_key(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(f"{path.suffix}.tmp")
        try:
            temporary_path.write_bytes(content)
            temporary_path.replace(path)
        except OSError as exc:
            temporary_path.unlink(missing_ok=True)
            raise AppError(503, "FILE_STORAGE_UNAVAILABLE", "Unable to store the digital book file") from exc
        return storage_key

    def exists(self, storage_key: str) -> bool:
        return self._path_for_key(storage_key).is_file()

    def delete(self, storage_key: str) -> None:
        try:
            self._path_for_key(storage_key).unlink(missing_ok=True)
        except OSError:
            # The database has already selected a newer canonical file; an orphan can be cleaned later.
            return

    def iter_bytes(self, storage_key: str, *, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
        path = self._path_for_key(storage_key)
        try:
            with path.open("rb") as file_handle:
                while chunk := file_handle.read(chunk_size):
                    yield chunk
        except OSError as exc:
            raise AppError(404, "DIGITAL_FILE_NOT_FOUND", "The digital book file is unavailable") from exc

    def _path_for_key(self, storage_key: str) -> Path:
        key = PurePosixPath(storage_key)
        if key.is_absolute() or ".." in key.parts:
            raise AppError(404, "DIGITAL_FILE_NOT_FOUND", "The digital book file is unavailable")
        path = (self.root / Path(*key.parts)).resolve()
        if self.root != path and self.root not in path.parents:
            raise AppError(404, "DIGITAL_FILE_NOT_FOUND", "The digital book file is unavailable")
        return path
