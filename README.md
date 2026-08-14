# e-library-backend
A modular FastAPI backend for an E-Library Management System with book management, controlled digital-file access, borrowing, reservations, favorites, ratings, optional written reviews, admin statistics, and AI-powered book summaries.

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

## Optional Book Reviews

Written reviews are separate from ratings. A user may rate without reviewing, review without rating, do both, or do neither. Each user may create one review per book only after they have borrowed that exact book at least once; an ACTIVE or RETURNED borrowing qualifies, while a reservation does not. Review text is required, preserves the submitted content, and must be 1–2000 characters excluding whitespace-only values.

Only the review owner may update or delete it. Reviews remain available after archiving a book, and a user with borrowing history may still add historical feedback. The review API is:

```text
POST   /api/v1/reviews
PATCH  /api/v1/reviews/{review_id}
DELETE /api/v1/reviews/{review_id}
GET    /api/v1/reviews/books/{book_id}
GET    /api/v1/reviews/me
```

Book responses remain lightweight and do not include complete review lists; use the dedicated book-reviews endpoint instead.

Review-feature verification recorded `89 passed` for the full test suite; Alembic revision `20260814_0003 (head)` has no schema drift.

## Phase 12 Hardening

The API uses configured CORS origins with credentials, explicit allowed methods/headers, and no wildcard origin. Every response includes `X-Request-ID`: a safe client-provided value is preserved, otherwise the server generates one for correlation. Domain, validation, rate-limit, framework HTTP, and unexpected failures use the same safe error envelope; internal exception details are logged but never returned.

SlowAPI protects registration, login, AI summary generation, review creation, and admin PDF write endpoints. Defaults are configured in `.env.example`; rate-limit failures return HTTP 429 with `RATE_LIMIT_EXCEEDED`.

```env
CORS_ORIGINS=http://localhost:3000
CORS_ALLOW_METHODS=GET,POST,PATCH,DELETE,OPTIONS
CORS_ALLOW_HEADERS=Authorization,Content-Type,X-Request-ID
AUTH_REGISTRATION_RATE_LIMIT=5/minute
AUTH_LOGIN_RATE_LIMIT=5/minute
AI_SUMMARY_RATE_LIMIT=10/hour
REVIEW_CREATE_RATE_LIMIT=10/hour
BOOK_CREATE_RATE_LIMIT=10/hour
BULK_BOOK_UPLOAD_RATE_LIMIT=5/hour
BOOK_FILE_REPLACE_RATE_LIMIT=10/hour
```

Logs intentionally exclude passwords, JWTs, refresh tokens, AI tokens, request bodies, PDF content, and extracted text.

Phase 12 automated verification recorded `96 passed`; Alembic remains clean at `20260814_0003 (head)`.

## Reading Progress / Continue Reading

The backend stores private, per-user progress for digital books so a frontend can implement Continue Reading. It stores `current_page`, client-supplied positive `total_pages`, server-controlled `last_read_at`, and the book `content_version`. Responses derive `progress_percent`; clients cannot submit a percentage, timestamp, content version, or user ID.

```text
GET /api/v1/books/{book_id}/progress
PUT /api/v1/books/{book_id}/progress
GET /api/v1/reading-progress/me
```

PUT requires an ACTIVE borrowing for the same book and is idempotent: one progress record exists per user/book. GET remains private and can return historical progress after return or archival, but returned or archived books cannot update it. Continue Reading lists only the authenticated user's records by most recently read.

When a book's `content_version` changes, saved progress is preserved but returned as `is_stale: true`; page values are never silently remapped to a different PDF. The frontend decides where to show Continue Reading, progress bars, and PDF resume behavior.

Reading Progress verification recorded `107 passed`; Alembic is clean at `20260814_0004 (head)`.

## Phase 13: Seed Data, Documentation, and Final Verification

Phase 13 established deterministic seed data, clean-start validation, and documentation synchronization. All acceptance criteria passed. The project is **feature-frozen** after Phase 13.

### Verification milestone history

| Milestone | Tests | Migration head |
|---|---|---|
| Digital Book Storage + Bulk Upload | 80 | `20260814_0002` |
| OpenAPI file-picker regression | 81 | `20260814_0002` |
| Optional Book Reviews | 89 | `20260814_0003` |
| Phase 12 Hardening | 96 | `20260814_0003` |
| Reading Progress | 107 | `20260814_0004` |
| **Phase 13 (current)** | **107** | **`20260814_0004`** |

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+

### Setup

```bash
# Clone and enter the project
cd e-library-backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate
# Activate (Linux/macOS)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env with your PostgreSQL credentials and a secure JWT_SECRET_KEY
```

### Database Setup

```bash
# Create PostgreSQL databases
# (use psql or your preferred tool)
# CREATE DATABASE elibrary;
# CREATE DATABASE elibrary_test;

# Run migrations
alembic upgrade head

# Verify migration head
alembic current
# Expected: 20260814_0004 (head)
```

### Seed Data (DEVELOPMENT ONLY)

The seed script populates the database with deterministic demonstration data. It is **development-only** and must never run against production.

```bash
python scripts/seed.py
```

Seeded entities: 6 users (1 admin, 5 regular), 10 authors, 8 categories, 20 books with valid PDFs, 25 borrowings (including 2 overdue), 10 reservations (PENDING and READY), 14 favorites, 46 ratings, 8 reviews, 6 reading progress records, and 8 cached AI summaries.

The seed script is idempotence-guarded: it refuses to run if seed identities already exist. For a clean reset:

```bash
# WARNING: Destroys all data. DEVELOPMENT ONLY.
alembic downgrade base
alembic upgrade head
python scripts/seed.py
```

Seeded accounts:

| Role | Email | Password |
|---|---|---|
| ADMIN | `admin@elibrary.dev` | `AdminPass!123` |
| USER | `alice@elibrary.dev` | `DevUser!123` |
| USER | `bob@elibrary.dev` | `DevUser!123` |
| USER | `carol@elibrary.dev` | `DevUser!123` |
| USER | `dave@elibrary.dev` | `DevUser!123` |
| USER | `erin@elibrary.dev` | `DevUser!123` |

### Run the Application

```bash
uvicorn app.main:app --reload
```

- Health check: `GET http://localhost:8000/health`
- Swagger UI: `http://localhost:8000/docs`

### Run Tests

```bash
pytest -q
```

Current suite: **107 passed** (Phase 13 final count).

---

## Security Notes

- `.env` is gitignored — never commit secrets.
- `storage/` is gitignored — server-managed PDFs are not committed.
- AI tokens, JWT secrets, and database credentials come from environment variables only.
- Logs exclude passwords, JWTs, refresh tokens, AI tokens, request bodies, PDF content, and extracted text.
- API responses never expose filesystem paths, storage keys, or internal security fields.

## Domain Model (15 entities)

`users`, `books`, `authors`, `categories`, `book_authors`, `book_categories`, `book_files`, `borrowings`, `reservations`, `favorites`, `ratings`, `book_reviews`, `reading_progress`, `book_summaries`, `refresh_tokens`

## Future Considerations

The following are explicitly **not implemented** and not planned:

Docker, Redis, Celery, Elasticsearch, Kafka, microservices, email notifications, WebSockets, advanced ML recommendations, persistent AI event history, distributed AI locking.
