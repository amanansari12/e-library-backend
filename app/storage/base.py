"""Storage contract used by digital-book domain services."""

from collections.abc import Iterator
from typing import Protocol


class BookStorage(Protocol):
    """Small provider-neutral interface for server-managed book assets."""

    def save(self, book_id: int, content: bytes, *, extension: str) -> str: ...

    def exists(self, storage_key: str) -> bool: ...

    def delete(self, storage_key: str) -> None: ...

    def iter_bytes(self, storage_key: str, *, chunk_size: int = 64 * 1024) -> Iterator[bytes]: ...
