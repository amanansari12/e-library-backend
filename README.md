# e-library-backend
A modular FastAPI backend for an E-Library Management System with book management, controlled digital-file access, borrowing, reservations, favorites, ratings, admin statistics, and AI-powered book summaries.

## Post-Phase 11 architectural revision: Digital Book Storage

PostgreSQL stores book metadata and relationships; local filesystem storage stores the canonical PDF. Each valid book is created through multipart `POST /api/v1/books` with a mandatory PDF, while `book_files` stores safe metadata, a SHA-256 checksum, and optional derived extracted text. Digital files are streamed only to authenticated users with an active borrowing.

`POST /api/v1/books/{book_id}/file` replaces the active PDF and increments `content_version`, naturally invalidating the previous AI-summary cache version. The storage interface is local today but can be replaced by object storage later without changing the domain service. Configure `BOOK_STORAGE_ROOT` and `MAX_BOOK_FILE_SIZE_MB`; managed `storage/` files are ignored by Git.

## Additional implemented feature

Bulk Catalog Creation is an operational, admin-only enhancement added separately from the official Phase 1–13 roadmap. It provides atomic catalog batches through:

```text
POST /api/v1/authors/bulk
POST /api/v1/categories/bulk
POST /api/v1/books/bulk
```

The configurable default limit is 50 items per batch. `POST /api/v1/books/bulk` is an ADMIN-only multipart endpoint: `books` is a JSON array whose entries carry a unique `file_key`, `file_manifest` maps each key to one unique uploaded filename, and `files` contains the PDFs. The whole batch is validated before database writes; a failed batch creates neither book rows nor retained files. It never generates AI summaries automatically.

Digital-storage verification recorded `80 passed`; database revision `20260814_0002 (head)` with no Alembic upgrade drift. The separate OpenAPI file-picker regression suite subsequently increased the current automated total to 81 tests.
