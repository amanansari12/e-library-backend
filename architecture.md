# E-Library Backend Architecture

## 1. Overview

This document is the canonical architecture for the E-Library Management System backend.

The system is a student-level, modular monolith built with Python and FastAPI. It provides book management, controlled digital-book storage and access, users, borrowing, searching, reservations, favorites, ratings, optional written reviews, admin statistics, and AI-powered book summaries.

The architecture intentionally avoids unnecessary enterprise infrastructure. The project should be realistic for one student to implement, test, understand, and defend in an interview.

### Core Architecture

```text
Client
  |
  v
FastAPI Router
  |
  v
Service Layer
  |
  +----------------------+
  |                      |
  v                      v
Repository Layer       AI Client
  |                      |
  +----------------------+\
  |                      | \
  v                      v  v
PostgreSQL      Local Storage  Userfacet AI API
```

The backend is a **modular monolith**.

### Current implementation status

Original Phases 1–13 are complete. The post-Phase-11 Digital Book Storage revision, Multipart Bulk Book Upload enhancement, optional Book Reviews, Phase 12 Cross-Cutting Hardening, and post-Phase-12 Reading Progress are also complete. The current database revision is `20260814_0004 (head)`.

### Additional operational enhancement: Bulk Catalog Creation

Bulk catalog endpoints were added separately from the canonical phase roadmap as an admin operational enhancement. `POST /api/v1/authors/bulk` and `POST /api/v1/categories/bulk` remain JSON batch endpoints. `POST /api/v1/books/bulk` is multipart-only: a JSON metadata array supplies a unique `file_key` per book, a manifest maps those keys to uploaded filenames, and every PDF is validated and stored through `BookFile` before the batch commits. All three use atomic batches and do not trigger AI summary generation.

### Post-Phase 11 architectural revision: Digital Book Storage

PostgreSQL stores metadata and relationships; server-controlled local filesystem storage holds canonical PDFs. `BookFile` is a one-to-many child of `Book`, although only one file is active per book today. `extracted_text` is derived auxiliary data for AI summaries, never a substitute for the original PDF. The storage abstraction isolates `save`, `exists`, streaming, and deletion for a later object-storage migration.

---

## 2. Goals

The architecture prioritizes:

1. Correctness
2. Clear domain modeling
3. Database integrity
4. Security
5. Maintainability
6. Testability
7. Realistic student scope
8. Meaningful feature depth
9. Safe AI integration

The project should demonstrate engineering judgment rather than technology quantity.

---

## 3. Technology Stack

| Technology | Purpose | Decision |
|---|---|---|
| Python 3.11+ | Programming language | Required by assignment |
| FastAPI | REST API framework | Primary backend framework |
| PostgreSQL 15+ | Relational database | Primary persistence layer |
| SQLAlchemy 2.x | ORM / database access | Synchronous sessions |
| Alembic | Schema migrations | Required |
| Pydantic v2 | Validation and serialization | FastAPI integration |
| python-jose | JWT generation/validation | Authentication |
| passlib[bcrypt] | Password hashing | Secure password storage |
| httpx | External HTTP client | Synchronous `httpx.Client` |
| slowapi | Rate limiting | Simple single-instance protection |
| pytest | Testing | Unit and integration tests |
| uvicorn | Application server | Local/production ASGI server |

### Deliberately Not Required

The project does not require:

- Docker
- Redis
- Celery
- Kafka
- Elasticsearch
- Kubernetes
- Microservices
- CQRS
- Event sourcing
- Multiple databases
- Machine-learning recommendation systems

These can appear only in future-improvement discussions when justified.

---

## 4. Execution Model

Use a **synchronous application model**.

- FastAPI route handlers are synchronous.
- SQLAlchemy uses normal `Session`.
- The AI integration uses synchronous `httpx.Client`.
- Do not introduce `AsyncSession`, `AsyncClient`, `asyncio`, or `pytest-asyncio`.

FastAPI can execute synchronous route functions through its worker threadpool, keeping the implementation straightforward for this student project.

---

## 5. Actors and Roles

### USER

A normal library user can:

- Register and log in
- View and update their profile
- Browse books
- Search books
- View book details
- Borrow books
- Return their own books
- View borrowing history
- Reserve unavailable books
- Cancel their own reservations
- Add/remove favorites
- Rate books
- Request AI summaries

### ADMIN

An administrator can additionally:

- Create books
- Update books
- Archive books
- Restore books
- Manage authors
- Manage categories
- View administrative statistics
- View AI usage information where appropriate

---

## 6. Core Functional Scope

### Authentication

- Registration
- Login
- JWT access tokens
- Refresh tokens
- Logout/revocation
- Password hashing
- Role-based authorization

### User Profile

- Get current user
- Update current user

Regular users should use `/users/me` rather than arbitrary user IDs.

### Books

- Create
- Read
- Update
- Archive
- Restore
- List
- Search
- Filter
- Sort
- Paginate

### Authors and Categories

- Author CRUD
- Category CRUD
- Book-author many-to-many relationship
- Book-category many-to-many relationship

### Borrowing

- Borrow
- Return
- Active borrowing list
- Borrowing history
- Due dates
- Overdue detection
- Borrow limit
- Concurrent availability control

### Reservations / Waiting List

- Create reservation
- Queue ordering
- Cancel reservation
- Promotion after return
- READY state
- Expiry
- Duplicate prevention

### Favorites

- Add
- Remove
- List
- Check status

### Ratings

- 1–5 rating
- Create/update rating
- Delete own rating
- Get ratings for a book
- Average rating
- Rating count

### Reviews

- Create an optional review after borrowing a book at least once
- Update own review
- Delete own review
- List book reviews
- List current user's reviews
- One review per user/book
- Keep written reviews independent from 1–5 ratings

### Reading Progress

- Set current page and total pages only while actively borrowing a book
- Retrieve the current user's historical progress after return
- List the current user's Continue Reading state
- One progress record per user/book
- Derive progress percentage rather than storing it
- Track the book content version to identify stale page coordinates

### AI Book Summary

- Generate standard summary
- Return cached summary
- Regenerate explicitly
- Cache by book/content version
- Protect limited AI quota
- Handle external API failures

### Admin Statistics

- User statistics
- Book statistics
- Borrowing statistics
- Reservation statistics
- Rating statistics
- AI statistics
- Most borrowed books
- Popular categories
- Highest-rated books

---

## 7. Architectural Layers

### Router Layer

Responsible for:

- HTTP routes
- Request parsing
- Authentication dependencies
- Authorization dependencies
- Response serialization
- HTTP status codes

Routers must remain thin.

### Service Layer

Responsible for:

- Business rules
- Workflow orchestration
- Transaction boundaries
- Authorization-aware domain operations
- Coordinating repositories and external clients

Services with meaningful business logic:

- AuthService
- BookService
- BorrowingService
- ReservationService
- SummaryService
- AdminService

Simple CRUD modules can remain thin and should not be artificially complicated.

### Repository Layer

Responsible for:

- Database access
- Queries
- Filtering
- Aggregation
- Persistence

Repositories do not contain business rules.

### Client Layer

Responsible for external dependencies.

Initially this includes:

```text
clients/ai_client.py
```

The AI client handles:

- HTTP communication
- Authorization header
- Timeout
- Response parsing
- External error mapping

### Model Layer

SQLAlchemy ORM models.

### Schema Layer

Pydantic request and response models.

---

## 8. Recommended Project Structure

```text
e-library-backend/
│
├── README.md
├── architecture.md
├── implementation_plan.md
├── .gitignore
├── .env.example
├── requirements.txt
├── alembic.ini
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── books.py
│   │       ├── authors.py
│   │       ├── categories.py
│   │       ├── borrowings.py
│   │       ├── reservations.py
│   │       ├── favorites.py
│   │       ├── ratings.py
│   │       ├── reading_progress.py
│   │       ├── reviews.py
│   │       ├── summaries.py
│   │       ├── admin.py
│   │       └── health.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── rate_limit.py
│   │   └── exceptions.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── book.py
│   │   ├── book_file.py
│   │   ├── author.py
│   │   ├── category.py
│   │   ├── borrowing.py
│   │   ├── reservation.py
│   │   ├── favorite.py
│   │   ├── rating.py
│   │   ├── reading_progress.py
│   │   ├── book_review.py
│   │   ├── book_summary.py
│   │   └── refresh_token.py
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── book.py
│   │   ├── author.py
│   │   ├── category.py
│   │   ├── borrowing.py
│   │   ├── reservation.py
│   │   ├── favorite.py
│   │   ├── rating.py
│   │   ├── reading_progress.py
│   │   ├── review.py
│   │   ├── summary.py
│   │   └── admin.py
│   │
│   ├── repositories/
│   │   ├── user.py
│   │   ├── catalog.py
│   │   ├── book_file.py
│   │   ├── borrowing.py
│   │   ├── reservation.py
│   │   ├── favorite.py
│   │   ├── rating.py
│   │   ├── reading_progress.py
│   │   ├── review.py
│   │   ├── summary.py
│   │   └── statistics.py
│   │
│   ├── services/
│   │   ├── auth.py
│   │   ├── catalog.py
│   │   ├── book_file.py
│   │   ├── text_extraction.py
│   │   ├── borrowing.py
│   │   ├── reservation.py
│   │   ├── favorite.py
│   │   ├── rating.py
│   │   ├── reading_progress.py
│   │   ├── review.py
│   │   ├── summary.py
│   │   └── admin.py
│   │
│   ├── clients/
│   │   └── ai_client.py
│   │
│   ├── storage/
│   │   ├── base.py
│   │   └── local.py
│   │
│   ├── dependencies/
│   │   └── auth.py
│   │
│   └── middleware/
│       ├── request_id.py
│       └── cors.py
│
├── scripts/
│   └── seed.py
│
└── tests/
    ├── test_config.py
    ├── test_health.py
    ├── unit/
    │   ├── test_auth_dependencies.py
    │   ├── test_openapi.py
    │   └── test_schema.py
    └── integration/
        ├── conftest.py
        ├── test_admin_statistics.py
        ├── test_auth.py
        ├── test_book_files.py
        ├── test_borrowings.py
        ├── test_bulk_catalog.py
        ├── test_catalog.py
        ├── test_favorites.py
        ├── test_hardening.py
        ├── test_ratings.py
        ├── test_reading_progress.py
        ├── test_reservations.py
        ├── test_reviews.py
        ├── test_search.py
        └── test_summaries.py
```

Only create files that are actually required. The structure is guidance, not a requirement to create empty boilerplate.

---

## 9. Domain Model

### User

Fields:

- id
- email
- username
- hashed_password
- full_name
- role
- created_at
- updated_at

Do not include `is_active` unless a later requirement introduces account suspension/deactivation.

### Book

Fields:

- id
- title
- isbn
- description
- publication_year
- max_concurrent_borrows
- current_borrows_count
- content_version
- is_archived
- created_at
- updated_at

`books.content` has been removed. `Book` is catalog and domain metadata only; it is not the canonical container for a digital document.

### BookFile

- id
- book_id
- original_filename
- storage_key (internal only)
- mime_type
- file_size
- file_format
- checksum
- extracted_text (derived only)
- is_active
- created_at
- updated_at

`storage_key` is an internal, server-controlled reference to the stored asset and is never exposed through book responses. The original PDF remains in configurable local storage and is the canonical digital content. `extracted_text` is derived auxiliary data for AI and possible future search; it does not preserve images, graphs, tables, formatting, or page layout, which remain in the original PDF. A book requires one active PDF before it can be borrowed. Archive operations retain the asset but block file access.

### Author

Fields:

- id
- name
- biography
- created_at

### Category

Fields:

- id
- name
- description
- created_at

### Borrowing

Fields:

- id
- user_id
- book_id
- borrowed_at
- due_date
- returned_at
- status

Stored status values:

```text
ACTIVE
RETURNED
```

`OVERDUE` is **computed**, not stored.

### Reservation

Fields:

- id
- user_id
- book_id
- position
- status
- created_at
- notified_at
- expires_at

Recommended states:

```text
PENDING
READY
FULFILLED
CANCELLED
EXPIRED
```

### Favorite

Fields:

- id
- user_id
- book_id
- created_at

### Rating

Fields:

- id
- user_id
- book_id
- score
- created_at
- updated_at

### BookReview

Fields:

- id
- user_id
- book_id
- review_text
- created_at
- updated_at

Each user may have one review for a book. Review creation requires a borrowing record for the same `user_id` and `book_id`; an ACTIVE or RETURNED borrowing qualifies. Reservations, favorites, ratings, and book views do not qualify.

### ReadingProgress

Fields:

- id
- user_id
- book_id
- content_version
- current_page
- total_pages
- last_read_at
- created_at
- updated_at

Each user has at most one record for a book. `current_page` and `total_pages` are the source of truth; `progress_percent` is derived as `current_page / total_pages * 100` and rounded to two decimal places in API responses.

### BookSummary

Fields:

- id
- book_id
- content_version
- model
- summary_text
- token_count where available
- created_at

There is only **one summary type: standard**.

Do not add `summary_type` to the database.

### RefreshToken

Fields:

- id
- user_id
- token
- expires_at
- revoked
- created_at

### Implemented database entities

The current schema contains 15 domain entities/association tables: `users`, `books`, `authors`, `categories`, `book_authors`, `book_categories`, `book_files`, `borrowings`, `reservations`, `favorites`, `ratings`, `book_reviews`, `reading_progress`, `book_summaries`, and `refresh_tokens`. `book_files` was introduced by migration `20260814_0002`, which also removed `books.content`; `book_reviews` was introduced by migration `20260814_0003`; `reading_progress` was introduced by migration `20260814_0004`.

---

## 10. Digital Availability Model

Do not model physical book copies.

For this project, a digital book has a configurable concurrent borrowing capacity.

Example:

```text
max_concurrent_borrows = 3
current_borrows_count = 2
```

Therefore:

```text
available_slots = 3 - 2 = 1
```

The count is maintained transactionally.

This is simpler than introducing a separate BookCopy or License entity.

---

## 11. Database Constraints

Important invariants must be protected at the database level where appropriate.

### Users

- UNIQUE(email)
- UNIQUE(username)

### Books

- UNIQUE(isbn)
- CHECK(max_concurrent_borrows > 0)
- CHECK(current_borrows_count >= 0)
- CHECK(content_version >= 1)

### Book files

- UNIQUE(storage_key)
- CHECK(file_size > 0)
- CHECK(file_format IN ('PDF'))
- One active file per book through the `uq_active_book_file` partial unique index

### Favorites

```sql
UNIQUE(user_id, book_id)
```

### Ratings

```sql
UNIQUE(user_id, book_id)
```

and:

```sql
CHECK(score BETWEEN 1 AND 5)
```

### Reservations

Required partial unique index:

```sql
CREATE UNIQUE INDEX uq_active_reservation
ON reservations(user_id, book_id)
WHERE status IN ('PENDING', 'READY');
```

This is required because application-only duplicate checks are not safe under concurrent requests.

### AI summaries

Require a unique constraint that makes the cache key idempotent:

```sql
UNIQUE(book_id, content_version)
```

This ensures concurrent requests cannot persist duplicate summaries for the same book version.

---

## 12. Borrowing Rules

The final business rules are:

1. A user cannot exceed 5 active borrowings.
2. A book cannot be borrowed when all concurrent slots are occupied.
3. A user cannot borrow an archived book.
4. A user cannot actively borrow the same book more than once.
5. A user can only return their own borrowing.
6. Active borrowing of an archived book can still be returned.
7. Overdue status is computed from `due_date`.
8. Returning a book decrements `current_borrows_count`.
9. Returning a book may promote the next reservation.
10. Borrowing and availability updates must occur atomically.
11. A book must have an active `BookFile` before it can be borrowed.
12. An active borrowing authorizes `GET /api/v1/books/{book_id}/file`; returning the borrowing changes its status to `RETURNED` and revokes that access.

---

## 13. Borrowing Concurrency

When two users try to borrow the last available slot:

```text
User A ─┐
        ├──> Lock book row
User B ─┘
```

Use a database transaction and row-level locking such as `SELECT FOR UPDATE`.

The transaction should:

1. Lock the book row.
2. Verify it is not archived.
3. Verify the user has not exceeded their limit.
4. Verify the user does not already actively borrow the book.
5. Verify an available slot remains.
6. Create the borrowing.
7. Increment `current_borrows_count`.
8. Commit.

Only one concurrent transaction should successfully consume the final slot.

---

## 14. Borrowing Return

Return flow:

1. Load borrowing.
2. Verify it belongs to current user.
3. Verify it is active.
4. Mark it returned.
5. Set `returned_at`.
6. Decrement `current_borrows_count`.
7. Promote the next eligible reservation when appropriate.
8. Commit.

All related changes must be inside the same transaction.

---

## 15. Overdue Handling

Do not maintain a background job solely to mark overdue records.

A borrowing is considered overdue when:

```text
status == ACTIVE
AND
due_date < current_time
```

The API can expose:

```text
status = OVERDUE
```

in its response even though the database stores only `ACTIVE` or `RETURNED`.

Admin overdue statistics use the same database condition.

---

## 16. Reservation Rules

1. A user cannot exceed 3 active reservations.
2. A user can reserve only a fully borrowed book.
3. A user cannot create duplicate PENDING/READY reservations for the same book.
4. Reservation order must be deterministic.
5. Queue position is assigned inside a transaction.
6. READY reservations expire after 48 hours.
7. Returning a book promotes the next eligible PENDING reservation.
8. Archived books cannot receive new reservations.
9. Archiving a book cancels all PENDING and READY reservations for that book.

---

## 17. Reservation Promotion

Example:

```text
Book has no available slots

A → PENDING position 1
B → PENDING position 2
C → PENDING position 3
```

When a slot becomes available:

```text
A → READY
```

Set:

- `status = READY`
- `notified_at = now`
- `expires_at = now + 48 hours`

If A borrows successfully:

```text
A → FULFILLED
B → next candidate
```

If A's READY window expires:

```text
A → EXPIRED
B → READY
```

Because there is no notification service in the initial project, promotion is represented as a backend state transition. Notification delivery can be a future enhancement.

---

## 18. Archive Behavior

When an admin archives a book:

1. Set `is_archived = true`.
2. Cancel all PENDING and READY reservations.
3. Do not alter active borrowings.
4. Existing borrowers must still be able to return the book.
5. Block new borrowing.
6. Block new reservations.
7. Block new favorites.

Existing favorites may remain stored, but the service should decide consistently whether archived books appear in favorite lists.

The recommended approach is to retain the relationship but prevent new favorites and optionally omit archived books from active favorite listings.

---

## 19. Favorites Rules

- Add favorite only for a valid, non-archived book.
- Duplicate user/book favorite returns conflict.
- Remove only the current user's favorite.
- List only the current user's favorites.
- Database uniqueness prevents duplicate rows.

---

## 20. Rating Rules

- Rating must be between 1 and 5.
- One rating per user/book.
- POST can act as create-or-update/upsert.
- DELETE removes only the current user's rating.
- Average rating is computed with SQL aggregation.
- Rating count is returned with average where useful.
- Archived books may still retain historical ratings.

---

## 21. Review Rules

- Reviews are optional; a user may rate without reviewing, review without rating, do both, or do neither.
- A review is permitted only when the same user has at least one record in `borrowings` for the same book. Both ACTIVE and RETURNED borrowings qualify.
- A reservation alone never qualifies a user to review.
- `book_reviews` enforces `UNIQUE(user_id, book_id)`; duplicate creation returns a conflict.
- Review text is required, cannot be blank or whitespace-only, and is limited to 1–2000 characters without silently rewriting the submitted text.
- Only the review owner may update or delete it. A non-owner receives `403 FORBIDDEN`.
- A review does not store, create, update, or delete a rating. Deleting either record does not alter the other.
- Reviews remain readable after a book is archived. A user with qualifying borrowing history may also add historical feedback for an archived book.
- Book list and detail responses do not embed complete review lists; `GET /api/v1/reviews/books/{book_id}` is the dedicated read endpoint.

### Reading Progress Rules

- Reading progress is private user state, not an admin analytics feature. It is not coupled to ratings, reviews, favorites, or borrowing counters.
- `PUT /api/v1/books/{book_id}/progress` requires an ACTIVE borrowing for the exact authenticated user/book pair. Reservations and returned borrowings do not qualify.
- `GET /api/v1/books/{book_id}/progress` and `GET /api/v1/reading-progress/me` are scoped only to the authenticated user. No endpoint accepts an arbitrary `user_id`.
- Progress remains readable after return or archival, but cannot be updated without a new ACTIVE borrowing. An archived book also blocks updates because its existing file-access rule blocks further PDF reading.
- `reading_progress` enforces `UNIQUE(user_id, book_id)`, `total_pages > 0`, `current_page >= 1`, and `current_page <= total_pages`.
- The server sets `last_read_at`; clients cannot set timestamps, content version, or percentage.
- On each successful PUT, stored `content_version` is set to the book's current version. If the current book version later differs, responses mark `is_stale = true`; old page numbers are preserved as historical data and never remapped automatically.
- The backend stores and retrieves state only. The frontend decides how to display Continue Reading, progress bars, and PDF resume navigation.

---

## 22. AI Summary Architecture

Request flow:

```text
Client
  |
  v
POST /api/v1/books/{book_id}/summary
  |
  v
SummaryService
  |
  +--> Active BookFile extracted_text + book metadata
  |
  +--> Database cache lookup
  |
  +--> Cache hit --> Return existing summary
  |
  +--> Cache miss --> AIClient
                         |
                         v
                  Userfacet AI API
                         |
                         v
                    Save summary
                         |
                         v
                      Response
```

There is only one summary format:

```text
standard
```

Use a maximum of 1000 output tokens for normal generation.

---

## 23. AI Cache

Cache key:

```text
(book_id, content_version)
```

Any `PATCH /books/{id}` increments `content_version`. Replacing the active PDF through `POST /books/{id}/file` also increments it.

This intentionally invalidates the previous summary even if only metadata changed.

The simpler rule avoids field-level diffing.

Before calling the AI API:

1. Fetch the book.
2. Check for a summary with the same book and current content version.
3. Return it when present.
4. If `force_regenerate=true`, bypass the cache.
5. Call the AI API only when necessary.
6. Persist the result.
7. Rely on the unique `(book_id, content_version)` constraint for database-level idempotency.

---

## 24. AI Regeneration

The summary endpoint supports:

```text
force_regenerate=false
```

When `false`:

- Return valid cached summary if available.

When `true`:

- Bypass the existing cache.
- Make a new AI call.
- Replace or update the cached result for the current content version.

Because regeneration consumes quota, it must still be rate-limited.

---

## 25. AI Quota Protection

The supplied API has a limited quota of 100 calls.

Use:

- Database-backed summary caching
- One summary type
- Explicit regeneration
- AI endpoint rate limiting
- Input size limits
- Controlled max tokens
- No unnecessary retries

Do not implement a custom in-memory AI request tracker.

Do not implement an in-memory generation lock.

A rare concurrent duplicate external request is acceptable for this student-scale project. Database uniqueness prevents duplicate persistence.

A distributed locking solution may be discussed as a future improvement.

---

## 26. AI Token Security

Never hardcode or expose the token.

Environment variables:

```env
AI_API_BASE_URL=https://ai-api.userfacet.com
AI_API_TOKEN=your_token_here
```

The token must never:

- Appear in source code
- Appear in frontend code
- Appear in API responses
- Appear in logs
- Be committed to GitHub

Commit only `.env.example`.

---

## 27. AI External Error Handling

Map the external service failures into clean application errors.

Relevant upstream cases:

- 400 invalid request
- 401 invalid token
- 403 CORS rejection
- 404 invalid model
- 429 quota exhausted
- Timeout
- Other upstream failures
- Malformed response

Do not retry authentication or authorization failures.

Do not retry indefinitely.

Return a safe internal error rather than leaking provider implementation details.

---

## 28. AI Prompt

The generated prompt should use available book information such as:

- Title
- Author
- Description
- Category
- Derived extracted-text excerpt from the active PDF

Use a controlled system/user prompt.

Do not allow arbitrary client-provided instructions to replace the intended summarization task.

Limit derived extracted text before sending it upstream.

Treat extracted text as untrusted input from a prompt-injection perspective.

---

## 29. Search

Use PostgreSQL-native search.

Support:

- Title search
- Description search
- Author filtering
- Category filtering
- Availability filtering
- Publication year filtering
- Sorting
- Pagination

`pg_trgm` may be used as a SHOULD-level optimization.

The application must remain functional with regular `ILIKE` fallback if the extension is unavailable.

Do not introduce Elasticsearch.

---

## 30. Pagination

Use offset pagination.

Example:

```text
?page=2&page_size=20
```

Response:

```json
{
  "items": [],
  "total": 150,
  "page": 2,
  "page_size": 20,
  "pages": 8
}
```

Maximum page size should be controlled, for example 100.

Cursor pagination is a future enhancement only.

---

## 31. Authentication

### Registration

1. Validate input.
2. Check unique email/username.
3. Hash password.
4. Create USER account.
5. Return safe user information.

### Login

1. Find user by email.
2. Verify password.
3. Create access token.
4. Create refresh token.
5. Persist refresh token.
6. Return tokens.

### Access Token

Short-lived JWT, for example 30 minutes.

Contains:

- user ID
- role
- issued-at
- expiration

### Refresh Token

Longer-lived token, for example 7 days.

Store a server-side representation so it can be revoked.

---

## 32. Authorization

Use FastAPI dependencies such as:

```text
get_current_user
require_admin
```

Object-level access must be enforced.

Examples:

- A user cannot return another user's borrowing.
- A user cannot cancel another user's reservation.
- A user cannot delete another user's rating.
- A user cannot delete another user's favorite.
- A non-admin cannot access admin statistics.

This prevents IDOR vulnerabilities.

---

## 33. API Versioning

All application endpoints use:

```text
/api/v1
```

Health endpoint:

```text
/health
```

AI-related internal endpoints can be grouped consistently under the API version.

---

## 34. API Groups

### Auth

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
```

### Users

```text
GET   /api/v1/users/me
PATCH /api/v1/users/me
```

### Books

```text
GET   /api/v1/books
GET   /api/v1/books/{book_id}
POST  /api/v1/books
POST  /api/v1/books/bulk
POST  /api/v1/books/{book_id}/file
GET   /api/v1/books/{book_id}/file
PATCH /api/v1/books/{book_id}
POST  /api/v1/books/{book_id}/archive
POST  /api/v1/books/{book_id}/restore
```

#### Digital-book operations

| Endpoint | Access | Implemented behavior |
|---|---|---|
| `POST /api/v1/books` | ADMIN | `multipart/form-data`: creates one book with a required, validated PDF; storage writes, checksum calculation, derived-text extraction, and `BookFile` creation are coordinated without storing PDF bytes in PostgreSQL. |
| `POST /api/v1/books/bulk` | ADMIN | Atomic `multipart/form-data` bulk creation. `books` is JSON metadata with unique `file_key` values, `file_manifest` maps each key to one uploaded filename, and `files` supplies the PDFs. Every successful item receives one active `BookFile`; failed batches create no partial records and clean up stored files. AI is not called automatically. |
| `POST /api/v1/books/{book_id}/file` | ADMIN | Replaces the current PDF for an unarchived book, validates/stores it, updates active `BookFile` state, and increments `content_version`. Existing summaries for the preceding version naturally become stale. |
| `GET /api/v1/books/{book_id}/file` | Authenticated active borrower | Streams the actual PDF bytes from local storage. It does not return metadata JSON or an absolute path. Archived books and inactive/returned borrowings are denied. |

Upload validation uses the configured size limit, PDF extension/client MIME checks, PDF signature/parser validation, SHA-256 checksum generation, and derived PDF-text extraction. In OpenAPI, each bulk `files` item is `type: string`, `format: binary`, so Swagger presents a file picker. Swagger may display streamed PDF bytes as text with an unrecognized-response message; that is a Swagger binary-rendering limitation, not a change to the actual PDF response.

### Authors

```text
GET   /api/v1/authors
GET   /api/v1/authors/{author_id}
POST  /api/v1/authors
PATCH /api/v1/authors/{author_id}
```

### Categories

```text
GET   /api/v1/categories
GET   /api/v1/categories/{category_id}
POST  /api/v1/categories
PATCH /api/v1/categories/{category_id}
```

### Borrowings

```text
POST /api/v1/borrowings
POST /api/v1/borrowings/{borrowing_id}/return
GET  /api/v1/borrowings/me
GET  /api/v1/borrowings/me/active
```

### Reservations

```text
POST   /api/v1/reservations
DELETE /api/v1/reservations/{reservation_id}
GET    /api/v1/reservations/me
```

### Favorites

```text
POST   /api/v1/favorites
DELETE /api/v1/favorites/{book_id}
GET    /api/v1/favorites/me
GET    /api/v1/favorites/check/{book_id}
```

### Ratings

```text
POST   /api/v1/ratings
DELETE /api/v1/ratings/{book_id}
GET    /api/v1/ratings/books/{book_id}
GET    /api/v1/ratings/me
```

### Reviews

```text
POST   /api/v1/reviews
PATCH  /api/v1/reviews/{review_id}
DELETE /api/v1/reviews/{review_id}
GET    /api/v1/reviews/books/{book_id}
GET    /api/v1/reviews/me
```

`POST /api/v1/reviews` is authenticated and requires previous borrowing history for the same book. PATCH and DELETE are owner-only. Book-review lists return only safe reviewer display data (`id`, `username`, and `full_name`), never email, password data, tokens, or internal security fields.

### Reading Progress

```text
GET /api/v1/books/{book_id}/progress
PUT /api/v1/books/{book_id}/progress
GET /api/v1/reading-progress/me
```

The PUT body contains only `current_page` and `total_pages`; it sets one idempotent `(user, book)` state and requires an ACTIVE borrowing. GET returns the current user's historical record when present. Continue Reading returns only the caller's records in `last_read_at DESC, id DESC` order.

### AI Summaries

```text
POST /api/v1/books/{book_id}/summary
GET  /api/v1/books/{book_id}/summary
GET  /api/v1/ai/usage
GET  /api/v1/ai/health
```

`POST /summary` accepts `force_regenerate`.

It does not accept `summary_type`.

Summary prompts use the active file's extracted text along with book metadata. Replacing a digital file increments `content_version`, so the existing `(book_id, content_version)` cache automatically becomes stale.

### Admin Statistics

```text
GET /api/v1/admin/statistics
GET /api/v1/admin/statistics/popular-books
GET /api/v1/admin/statistics/popular-categories
GET /api/v1/admin/statistics/highest-rated
```

### Health

```text
GET /health
```

---

## 35. Consistent Error Format

Use:

```json
{
  "error": {
    "code": "BOOK_NOT_AVAILABLE",
    "message": "This book has no available borrowing slots"
  }
}
```

Examples of application error codes:

```text
INVALID_CREDENTIALS
BOOK_NOT_FOUND
BOOK_ARCHIVED
BOOK_NOT_AVAILABLE
BORROW_LIMIT_EXCEEDED
ALREADY_BORROWING
BORROWING_NOT_FOUND
FORBIDDEN
RESERVATION_NOT_FOUND
DUPLICATE_RESERVATION
DUPLICATE_FAVORITE
DUPLICATE_RATING
AI_QUOTA_EXHAUSTED
AI_PROVIDER_UNAVAILABLE
```

Use appropriate HTTP statuses including:

```text
400
401
403
404
409
422
429
500
502
503
```

---

## 36. Admin Statistics

The statistics subsystem uses PostgreSQL aggregation queries.

### Users

- Total users
- New users in last 30 days
- Active borrowers

### Books

- Total books
- Available books
- Archived books

### Borrowings

- Active
- Overdue
- Last 30 days
- Returns last 30 days

### Reservations

- Active reservations
- Books with waiting lists

### Ratings

- Total ratings
- Overall average rating

### AI

- Summaries generated
- Unique books summarized
- Summary generation failures where tracked

### Ranking endpoints

- Most borrowed books
- Popular categories
- Highest-rated books

Admin access only.

---

## 37. AI Failure Statistics

Persistent AI failure analytics are not required.

The initial implementation may use a lightweight in-memory failure counter or application logs for failure visibility.

Persistent AI event history is a future enhancement.

Do not add a dedicated AI event-sourcing system.

---

## 38. Rate Limiting

The implementation uses `slowapi` for simple single-instance, per-client-IP rate limiting. The limiter is deliberately local-process only; this project does not require Redis or distributed rate-limit state.

Configured abuse-sensitive endpoints are:

```text
POST /api/v1/auth/register       AUTH_REGISTRATION_RATE_LIMIT (default 5/minute)
POST /api/v1/auth/login          AUTH_LOGIN_RATE_LIMIT (default 5/minute)
POST /api/v1/books/{id}/summary  AI_SUMMARY_RATE_LIMIT (default 10/hour)
POST /api/v1/reviews             REVIEW_CREATE_RATE_LIMIT (default 10/hour)
POST /api/v1/books               BOOK_CREATE_RATE_LIMIT (default 10/hour)
POST /api/v1/books/bulk          BULK_BOOK_UPLOAD_RATE_LIMIT (default 5/hour)
POST /api/v1/books/{id}/file     BOOK_FILE_REPLACE_RATE_LIMIT (default 10/hour)
```

Rate-limit failures return HTTP 429 with `RATE_LIMIT_EXCEEDED` in the standard error envelope.

Do not implement an additional custom in-memory per-user tracker.

---

## 39. Middleware

Implemented lightweight middleware:

- CORS configuration with explicit origins, methods, request headers, and credentials.
- Request ID. Each response includes `X-Request-ID`; a client-provided ID is accepted only when it matches `[A-Za-z0-9_-]{1,128}`, otherwise the server generates a UUID-based value.

Application logs record request completion and safe failure metadata with the request ID, method/path, status, and duration. They do not log request bodies, passwords, access/refresh tokens, AI tokens, uploaded PDF contents, or extracted text.

Do not add complex observability infrastructure.

---

## 40. Configuration

Use Pydantic Settings and environment variables.

Example `.env.example`:

```env
APP_ENV=development
DEBUG=true

DATABASE_URL=postgresql://postgres:password@localhost:5432/elibrary
TEST_DATABASE_URL=postgresql://postgres:password@localhost:5432/elibrary_test

JWT_SECRET_KEY=change-me-to-a-long-random-secret
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

AI_API_BASE_URL=https://ai-api.userfacet.com
AI_API_TOKEN=your-ai-api-token

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

`CORS_ORIGINS` cannot use `*` because credentials are enabled. Actual secrets must never be committed.

---

## 41. Database Migrations

Use Alembic.

Only one `alembic.ini` exists at project root.

Directory:

```text
alembic/
├── env.py
├── script.py.mako
└── versions/
```

Never create a second `alembic.ini` inside `alembic/`.

---

## 42. Transactions

Transactions are critical for:

### Borrow

- Availability lock
- Validation
- Borrow record
- Count increment

### Return

- Borrowing validation
- Return record update
- Count decrement
- Reservation promotion

### Reservation creation

- Queue position calculation
- Insert
- Unique constraint protection

### Rating/favorite creation

- Database uniqueness protection

### Book archive

- Archive book
- Cancel relevant reservations

### AI persistence

- Save summary safely after successful external generation

---

## 43. Testing Strategy

### Unit Tests

Test:

- Password/auth rules
- Book rules
- Borrow limits
- Reservation logic
- Favorite rules
- Rating rules
- AI response parsing
- Admin calculation logic

### Integration Tests

Test API + PostgreSQL for:

- Auth
- Books
- Search
- Borrowing
- Reservations
- Favorites
- Ratings
- Admin statistics

### AI Client Tests

Mock the external API.

Do not consume the real assessment quota during automated tests.

Test:

- Success
- 400
- 401
- 403
- 404
- 429
- Timeout
- Malformed response

### Concurrency Tests

At minimum test or explicitly verify:

- Two users competing for the last book slot
- Concurrent duplicate reservation
- Duplicate favorite
- Duplicate rating
- Concurrent AI summary insertion

---

## 44. Seed Data

Provide deterministic demo data.

Suggested dataset:

- 1 admin
- 5 regular users
- 10 authors
- 8 categories
- 20 books
- Example borrowings
- Example reservations
- Example favorites
- Example ratings

Do not put real secrets into seed scripts.

Credentials used for development/demo should be clearly identified as local seed credentials only.

---

## 45. Local Development

The application must run without Docker.

Prerequisites:

```text
Python 3.11+
PostgreSQL 15+
```

Typical setup:

```bash
python -m venv .venv
```

Activate the virtual environment, install dependencies, configure `.env`, create the PostgreSQL database, run:

```bash
alembic upgrade head
```

then start:

```bash
uvicorn app.main:app --reload
```

API documentation:

```text
http://localhost:8000/docs
http://localhost:8000/redoc
```

Tests:

```bash
pytest
```

Docker can be mentioned in future improvements but is not a setup requirement.

---

## 46. README Requirements

The final README must describe the actual implementation.

Required sections:

1. Project Overview
2. Features
3. Tech Stack
4. Architecture
5. Database / ER Diagram
6. API Documentation
7. AI Integration
8. AI Token Security
9. AI Quota and Caching
10. Local Setup
11. Environment Variables
12. Alembic Migrations
13. Seed Data
14. Testing
15. Design Decisions
16. Assumptions
17. Trade-offs
18. Future Improvements

The README must not claim that unimplemented features exist.

---

## 47. Important Trade-offs

### Modular monolith instead of microservices

Chosen because:

- One student
- One database
- Shared ACID transactions
- Lower operational complexity
- Easier testing

### PostgreSQL instead of Elasticsearch

Chosen because the dataset and scope do not justify a separate search system.

### Database-backed AI cache instead of Redis

Chosen because the quota is small and summary persistence naturally belongs in the database.

### Lazy expiry instead of background workers

Chosen because reservation expiry and overdue state can be determined when records are accessed.

### Synchronous code instead of async database/HTTP stack

Chosen because it is easier to reason about and sufficient for this project.

### Concurrent borrowing slots instead of BookCopy

Chosen because this is an e-library model, not a physical inventory system.

### Local storage for PDFs instead of PostgreSQL document storage

PostgreSQL stores metadata and relational state; local filesystem storage holds large PDF bytes. The storage abstraction avoids coupling domain services to a specific backend, keeps the original PDF canonical, and treats extracted text as derived data. This is a deliberate student-level modular-monolith trade-off; object storage is a future replacement option, not a current implementation.

---

## 48. Future Improvements

Future work may include:

- Docker
- Redis
- Background workers
- Persistent AI event tracking
- Email notifications
- WebSockets
- Advanced recommendations
- Elasticsearch
- OAuth/social login
- Object-storage provider implementation
- Cursor pagination
- Distributed locking for AI generation
- More advanced search

These are not part of the initial implementation.

---

## 49. Final Implementation Boundary

### MUST IMPLEMENT

- Authentication
- User profile
- Books
- Authors
- Categories
- Search/filter/sort/pagination
- Borrowing
- Reservations
- Favorites
- Ratings
- AI standard summary
- AI caching
- AI quota protection
- Admin statistics
- Tests
- Alembic migrations
- Seed data
- README

### SHOULD IMPLEMENT

- slowapi rate limiting
- Request ID middleware
- CORS configuration
- pg_trgm optimization if convenient
- Strong OpenAPI descriptions

### FUTURE

- Docker
- Redis
- Celery
- Elasticsearch
- Kafka
- Microservices
- Email
- WebSockets
- Advanced recommendations
- Persistent AI event history
- Distributed AI locking

---

## 50. Final Architecture Summary

```text
                    CLIENT
                       |
                       v
               +---------------+
               |    FastAPI    |
               |   /api/v1     |
               +-------+-------+
                       |
              +--------+--------+
              |                 |
              v                 v
        Router Layer       Dependencies
              |
              v
        Service Layer
              |
       +------+------+
       |             |
       v             v
 Repository       AI Client
       |             |
       v             v
 PostgreSQL     Userfacet AI API
```

### Database

```text
users
books
authors
categories
book_authors
book_categories
book_files
borrowings
reservations
favorites
ratings
book_reviews
reading_progress
book_summaries
refresh_tokens
```

### Core workflows

```text
Authentication
Books
Search
Borrowing
Reservations
Favorites
Ratings
Reviews
Reading Progress
AI Summaries
Admin Statistics
```

### Core engineering principles

- Thin routers
- Business logic in services
- Database operations in repositories
- External AI isolated in a client
- Database constraints for critical invariants
- Transactions for state-changing workflows
- Synchronous implementation
- No unnecessary infrastructure
- AI token kept server-side
- AI quota protected with caching and rate limiting
- Tests for business rules and important concurrency cases

This is the canonical architecture to use when implementing the project.
