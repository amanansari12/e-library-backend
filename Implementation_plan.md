# E-Library Backend Implementation Plan

## Document Status

**Status:** Original Phases 1–11 complete; post-Phase-11 Digital Book Storage revision and Multipart Bulk Book Upload enhancement complete. Phase 12 and Phase 13 remain pending.

**Canonical architecture:** `architecture.md`

**Relationship:** `architecture.md` is the authoritative technical design. This document translates that architecture into a dependency-aware implementation sequence. If a conflict is discovered, the implementation must follow `architecture.md` and the conflict must be documented before proceeding.

**Target:** One-student, interview-defensible backend assessment.

**Implementation model:** Synchronous FastAPI modular monolith using PostgreSQL.

---

# 1. Implementation Objectives

The implementation must turn the approved architecture into a complete, tested, maintainable backend.

The final backend must provide:

- User registration and authentication
- JWT access and refresh tokens
- Logout/revocation
- User profile
- USER and ADMIN roles
- Book management
- Authors and categories
- Search, filtering, sorting, and pagination
- Digital-book borrowing with concurrent borrow slots
- Returning and computed overdue status
- Reservations / waiting list
- Favorites
- Ratings
- AI-powered standard book summaries
- AI summary caching and quota protection
- Admin statistics
- Consistent API errors
- Database migrations
- Unit and integration tests
- Seed data
- Accurate README documentation

The implemented post-Phase-11 architecture also provides mandatory PDF-backed book creation, local file storage through a storage abstraction, and authorization-controlled PDF streaming.

The implementation must remain:

- Synchronous
- Modular
- Student-realistic
- Testable
- Secure
- Explainable in an interview
- Free of Docker as a requirement
- Free of Redis, Celery, Kafka, Elasticsearch, Kubernetes, microservices, CQRS, event sourcing, and multiple databases

---

# 2. Canonical Technology Stack

| Component | Technology | Rule |
|---|---|---|
| Language | Python 3.11+ | Required |
| Framework | FastAPI | Synchronous route functions |
| Database | PostgreSQL 15+ | Single relational database |
| ORM | SQLAlchemy 2.x | Synchronous `Session` |
| Migrations | Alembic | One root `alembic.ini` |
| Validation | Pydantic v2 | Request/response validation |
| Authentication | python-jose | JWT |
| Password hashing | passlib[bcrypt] | Never store plaintext passwords |
| HTTP client | httpx | Synchronous `httpx.Client` |
| Rate limiting | slowapi | Simple single-instance limiter |
| Server | uvicorn | ASGI server |
| Testing | pytest | Unit and integration tests |

## Explicitly not required

Do not add these to the implementation:

- Docker
- Redis
- Celery
- Kafka
- Elasticsearch
- Kubernetes
- Microservices
- CQRS
- Event sourcing
- GraphQL
- Distributed queues
- Distributed caching
- ML recommendation systems

They may be discussed only as future improvements.

---

# 3. Architectural Rules

The implementation must follow:

```text
HTTP Request
  ↓
Middleware
  ↓
API Router
  ↓
Authentication / Authorization Dependencies
  ↓
Service Layer
  ↓
Repository Layer
  ↓
PostgreSQL
```

For AI:

```text
SummaryService
  ↓
AI Client
  ↓
Userfacet AI API
```

## Layer responsibilities

### Router

- HTTP handling
- Request parsing
- Dependency injection
- Response serialization
- HTTP status codes
- No significant business logic

### Service

- Business rules
- Workflow orchestration
- Transaction boundaries
- Domain-state authorization
- Coordination between repositories and clients

### Repository

- Database access
- Queries
- Filters
- Aggregations
- Persistence
- No business policy

### Client

- External HTTP communication
- AI authentication
- Timeout handling
- Response parsing
- External error mapping

### Models

SQLAlchemy ORM definitions.

### Schemas

Pydantic request/response definitions.

---

# 4. Repository Structure

The implementation should converge on:

```text
e-library-backend/
├── README.md
├── architecture.md
├── implementation_plan.md
├── .gitignore
├── .env.example
├── requirements.txt
├── alembic.ini
│
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── app/
│   ├── main.py
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
│   │       ├── summaries.py
│   │       ├── admin.py
│   │       └── health.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── exceptions.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── clients/
│   │   └── ai_client.py
│   ├── dependencies/
│   │   └── auth.py
│   └── middleware/
│       ├── request_id.py
│       └── cors.py
└── tests/
    ├── unit/
    └── integration/
```

Only create files that are needed.

Do not create empty abstractions simply to match a diagram.

---

# 5. Approved Database Model

The original Phase 2 baseline specified 12 entities. The implemented post-Phase-11 architectural revision formally supersedes that baseline with these 13 current entities:

1. users
2. books
3. authors
4. categories
5. book_authors
6. book_categories
7. book_files
8. borrowings
9. reservations
10. favorites
11. ratings
12. book_summaries
13. refresh_tokens

---

# 6. Phase 1: Project Foundation

## Objectives

Create the application skeleton and verify that the project starts.

## Tasks

- Initialize Python project structure.
- Create virtual-environment documentation.
- Create `requirements.txt`.
- Create `.gitignore`.
- Create `.env.example`.
- Configure Pydantic Settings.
- Create `app/main.py`.
- Create `/health`.
- Configure synchronous FastAPI execution.
- Configure CORS through environment settings.
- Add basic request-ID middleware if included at this stage.
- Configure application-level exception structure without overengineering.

## Environment variables

At minimum:

```env
APP_ENV=development
DEBUG=true

DATABASE_URL=postgresql://postgres:password@localhost:5432/elibrary
TEST_DATABASE_URL=postgresql://postgres:password@localhost:5432/elibrary_test

JWT_SECRET_KEY=change-me
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

AI_API_BASE_URL=https://ai-api.userfacet.com
AI_API_TOKEN=your-assigned-token

CORS_ORIGINS=http://localhost:3000
```

## Security rules

- `.env` must be ignored by Git.
- `.env.example` must not contain real secrets.
- The actual AI token must never be committed.

## Acceptance criteria

- `uvicorn app.main:app --reload` starts.
- `GET /health` returns HTTP 200.
- Configuration loads correctly.
- No Docker is needed.
- Importing the application does not require a live AI call.

## Tests

- Health endpoint test.
- Configuration loading test where practical.

## Depends on

None.

---

# 7. Phase 2: Database, SQLAlchemy, and Alembic

## Objectives

Create the PostgreSQL persistence layer and the initial schema.

## Tasks

- Create synchronous SQLAlchemy engine.
- Create synchronous `Session` factory.
- Create declarative base.
- Create database dependency.
- Define the approved baseline models; the current implementation additionally includes `BookFile` through the post-Phase-11 migration.
- Define relationships.
- Add timestamps.
- Add foreign keys.
- Add unique constraints.
- Add CHECK constraints.
- Add indexes.
- Configure Alembic.
- Ensure only one root-level `alembic.ini`.
- Create initial migration.
- Apply migration to development database.

## Critical model rules

### users

Must contain:

```text
id
email
username
hashed_password
full_name
role
created_at
updated_at
```

Do not create `is_active`.

### books

Must contain:

```text
id
title
isbn
description
publication_year
max_concurrent_borrows
current_borrows_count
content_version
is_archived
created_at
updated_at
```

### borrowings

Stored status values:

```text
ACTIVE
RETURNED
```

Never store `OVERDUE`.

### reservations

Recommended states:

```text
PENDING
READY
FULFILLED
CANCELLED
EXPIRED
```

### book_summaries

Must not contain `summary_type`.

Must contain:

```text
id
book_id
content_version
model
summary_text
token_count
created_at
```

## Required constraints

### Users

```text
UNIQUE(email)
UNIQUE(username)
```

### Books

```text
UNIQUE(isbn)
CHECK(max_concurrent_borrows > 0)
CHECK(current_borrows_count >= 0)
CHECK(content_version >= 1)
```

### Favorites

```text
UNIQUE(user_id, book_id)
```

### Ratings

```text
UNIQUE(user_id, book_id)
CHECK(score BETWEEN 1 AND 5)
```

### Reservations

Required partial unique index:

```sql
CREATE UNIQUE INDEX uq_active_reservation
ON reservations(user_id, book_id)
WHERE status IN ('PENDING', 'READY');
```

### AI summaries

Required:

```text
UNIQUE(book_id, content_version)
```

This is the database-level cache identity and prevents duplicate persisted summaries for the same book version.

## Search optimization

`pg_trgm` is optional.

If used:

- create it through migration;
- document the extension;
- provide `ILIKE` fallback;
- do not make the project unusable when it is unavailable.

## Acceptance criteria

- All approved tables exist.
- All foreign keys work.
- All critical constraints are present.
- Reservation partial unique index exists.
- Summary cache uniqueness exists.
- No `users.is_active`.
- No stored `OVERDUE`.
- No `book_summaries.summary_type`.
- Clean database can be migrated with Alembic.

## Tests

- Migration to head.
- Unique email.
- Unique username.
- Unique ISBN.
- Favorite uniqueness.
- Rating uniqueness.
- Rating CHECK.
- Reservation partial unique index.
- Summary uniqueness.

## Depends on

Phase 1.

---

# 8. Phase 3: Authentication and User Profile

## Objectives

Implement secure registration, login, refresh, logout, and current-user profile.

## Tasks

### Registration

- Validate email.
- Validate password.
- Check unique email/username.
- Hash password with bcrypt.
- Create USER role by default.
- Return safe user data.

### Login

- Find user.
- Verify password.
- Create short-lived JWT access token.
- Create refresh token.
- Store refresh token.
- Return both tokens.

### Refresh

- Validate refresh token.
- Check revocation.
- Check expiration.
- Create new access token.
- Follow the refresh-token policy defined by the architecture.

### Logout

- Revoke refresh token.

### Dependencies

Create:

```text
get_current_user
require_admin
```

## Security requirements

- Never store plaintext passwords.
- Never return hashed passwords.
- Never log credentials or tokens.
- Regular users only access `/users/me`.

## Acceptance criteria

- Registration works.
- Duplicate registration returns 409.
- Login works.
- Invalid credentials return 401.
- Protected routes reject missing/invalid tokens.
- Refresh works.
- Logout invalidates refresh token.
- Admin authorization distinguishes roles.

## Tests

- Registration success.
- Duplicate email.
- Duplicate username.
- Invalid password.
- Login success.
- Invalid login.
- Access token rejection.
- Refresh success.
- Refresh after revoke.
- Logout.
- `/users/me`.
- Admin-only dependency.

## Depends on

Phase 2.

---

# 9. Phase 4: Books, Authors, and Categories

## Objectives

Implement catalog management and lifecycle.

## Tasks

### Books

- List books.
- Get book details.
- Create book.
- Update book.
- Archive.
- Restore.
- Availability calculation.
- Rating aggregate in book detail where appropriate.

### Authors

- List.
- Detail.
- Create.
- Update.

### Categories

- List.
- Detail.
- Create.
- Update.

### Relationships

- Book-author many-to-many.
- Book-category many-to-many.

## Authorization

Admin only:

- Create book.
- Update book.
- Archive.
- Restore.
- Create/update authors.
- Create/update categories.

Users may read catalog information.

## Book version rule

Every successful `PATCH /books/{book_id}` increments:

```text
content_version += 1
```

Do not diff individual fields.

## Archive transaction

When a book is archived:

1. Set `is_archived = true`.
2. Cancel all PENDING/READY reservations.
3. Do not modify active borrowings.
4. Existing active borrowings remain returnable.
5. Block new borrowing.
6. Block new reservations.
7. Block new favorites.

## Acceptance criteria

- Catalog CRUD works.
- Admin mutation protection works.
- Relationships work.
- Archive/restore work.
- Archive side effects work.
- Every successful update increments content version.

## Tests

- Book CRUD.
- Author CRUD.
- Category CRUD.
- Relationships.
- Admin access.
- Archive side effects.
- Restore.
- Content version increment.

## Depends on

Phase 3.

---

# 10. Phase 5: Search, Filtering, Sorting, Pagination

## Objectives

Provide usable book discovery.

## Query parameters

Support:

```text
q
author_id
category_id
available
year_from
year_to
sort_by
sort_order
page
page_size
```

## Search

Use PostgreSQL-native search.

Support:

- title
- description
- author
- category
- availability
- publication year

`pg_trgm` may optimize matching.

Always preserve `ILIKE` fallback.

## Pagination

Use offset pagination:

```text
?page=2&page_size=20
```

Enforce a maximum page size, for example 100.

## Deterministic sorting

When sorting by a non-unique column, include a stable secondary ordering by ID so pagination is deterministic.

## Acceptance criteria

- Search works.
- Filters can be combined.
- Sorting works.
- Pagination metadata is correct.
- Empty results behave correctly.
- Fallback search works without pg_trgm.

## Tests

- Keyword search.
- Author filter.
- Category filter.
- Availability filter.
- Year range.
- Sort ascending.
- Sort descending.
- Pagination.
- Invalid values.
- Empty results.

## Depends on

Phase 4.

---

# 11. Phase 6: Borrowing

## Objectives

Implement the core lending workflow safely under concurrency.

## Digital availability model

Use:

```text
max_concurrent_borrows
current_borrows_count
```

Default `max_concurrent_borrows` is 3 unless configured otherwise.

Available slots:

```text
max_concurrent_borrows - current_borrows_count
```

## Borrow rules

1. Maximum 5 active borrowings per user.
2. Book must not be archived.
3. User cannot already actively borrow the same book.
4. A slot must be available.
5. Borrow creation and count increment must be atomic.

## Borrow transaction

Within one database transaction:

1. Lock book row using `SELECT FOR UPDATE`.
2. Validate book state.
3. Validate user active borrowing count.
4. Validate no active duplicate borrowing.
5. Validate availability.
6. Create borrowing.
7. Increment `current_borrows_count`.
8. Commit.

## Return transaction

Within one database transaction:

1. Load borrowing.
2. Verify current user owns it.
3. Verify status is ACTIVE.
4. Mark RETURNED.
5. Set `returned_at`.
6. Decrement book borrow count.
7. Trigger eligible reservation promotion.
8. Commit.

## Overdue

Do not store overdue state.

Computed condition:

```text
status == ACTIVE AND due_date < now
```

Expose `OVERDUE` only in API representation when appropriate.

Admin overdue statistics use the same condition.

## Acceptance criteria

- Borrowing works.
- Availability is enforced.
- Borrow limit works.
- Duplicate active borrowing is blocked.
- Concurrent final-slot borrowing cannot exceed capacity.
- Return works.
- Returning archived-book borrowings still works.
- Overdue is computed correctly.

## Tests

- Successful borrow.
- Unavailable book.
- Borrow limit.
- Duplicate borrowing.
- Return.
- Invalid return.
- Ownership.
- Archived-book return.
- Concurrent final-slot competition.

## Depends on

Phase 4.

---

# 12. Phase 7: Reservations / Waiting List

## Objectives

Implement deterministic waiting lists and promotion.

## Rules

1. Maximum 3 active reservations per user.
2. User can reserve only a fully borrowed/unavailable book.
3. User cannot reserve a book they actively borrow.
4. Duplicate PENDING/READY reservation is prohibited.
5. Queue ordering is deterministic.
6. READY expires after 48 hours.
7. Return can promote the next reservation.
8. Archive cancels PENDING/READY reservations.

## Reservation creation transaction

Use a transaction and lock the relevant book row with `SELECT FOR UPDATE`.

Within the transaction:

1. Lock the book.
2. Verify the book is fully borrowed.
3. Verify user is not already borrowing it.
4. Check user's active reservation limit.
5. Determine next queue position.
6. Insert reservation.
7. Commit.

The partial unique index remains the final duplicate-protection mechanism.

## Queue ordering

Use stable queue ordering such as:

```text
position ASC, created_at ASC, id ASC
```

Avoid ambiguous ordering.

## Promotion

Within the return transaction:

1. Find earliest eligible PENDING reservation.
2. Promote to READY.
3. Set `notified_at`.
4. Set `expires_at = notified_at + 48 hours`.

## Expiry

Use lazy evaluation.

When relevant reservation records are accessed:

- detect expired READY records;
- mark them EXPIRED;
- allow the next valid PENDING reservation to become READY when the workflow requires it.

No background worker is required.

## Acceptance criteria

- Unavailable books can be reserved.
- Available books cannot be unnecessarily reserved.
- Duplicate active reservation is blocked.
- Queue order is deterministic.
- User can cancel own reservation.
- User cannot cancel another user's reservation.
- Return promotes next user.
- READY expires.
- Archive cancels PENDING/READY records.

## Tests

- Reservation creation.
- Duplicate reservation.
- Reserve available book.
- Reserve own actively borrowed book.
- Reservation limit.
- Queue order.
- Cancellation.
- Promotion.
- Expiry.
- Archive cancellation.
- Concurrent duplicate reservation attempts.

## Depends on

Phase 6.

---

# 13. Phase 8: Favorites

## Tasks

Implement:

- Add favorite.
- Remove favorite.
- List current user's favorites.
- Check whether a book is favorited.

## Rules

- Authenticated user required.
- Book must exist.
- Archived book cannot receive a new favorite.
- Duplicate user/book pair is a 409.
- Only owner may remove.
- Database uniqueness is authoritative.

## Acceptance criteria

- Add works.
- Duplicate add returns 409.
- Remove works.
- Ownership is enforced.
- List is user-specific.
- Archived books cannot be newly favorited.

## Tests

- Add.
- Duplicate.
- Remove.
- Unauthorized ownership.
- List.
- Check status.
- Archived-book favorite.

## Depends on

Phase 4.

---

# 14. Phase 9: Ratings

## Tasks

Implement:

- Create/update rating.
- Delete own rating.
- Get ratings for a book.
- Get current user's ratings.
- Average rating.
- Rating count.

## Rules

- Score must be integer 1–5.
- One rating per user/book.
- POST behaves as upsert.
- Delete is owner-only.
- Historical ratings may remain on archived books.

## Database

```text
UNIQUE(user_id, book_id)
CHECK(score BETWEEN 1 AND 5)
```

## Acceptance criteria

- User can rate.
- User can update.
- Duplicate rows cannot occur.
- Ownership is protected.
- Invalid scores fail.
- Average/count are correct.

## Tests

- Create.
- Update.
- Delete.
- Duplicate protection.
- Validation.
- Ownership.
- Aggregation.

## Depends on

Phase 4.

---

# 15. Phase 10: AI Book Summaries

## Objectives

Integrate the supplied Userfacet AI API safely.

## AI API

Base:

```text
https://ai-api.userfacet.com
```

Use:

```text
GET /health
GET /v1/usage
POST /v1/chat/completions
```

Model:

```text
gpt-4o-mini
```

## AI client

Use synchronous:

```python
httpx.Client
```

The client must handle:

- Base URL.
- Bearer token.
- Timeout.
- Request creation.
- Response parsing.
- 400 handling.
- 401 handling.
- 403 handling.
- 404 handling.
- 429 handling.
- Timeout handling.
- Upstream failure mapping.
- Malformed response handling.

## Environment

```env
AI_API_BASE_URL=https://ai-api.userfacet.com
AI_API_TOKEN=...
```

Never hardcode the token.

Never log or return it.

## Summary model

Only one type:

```text
standard
```

Do not expose `summary_type`.

## Cache

Cache key:

```text
(book_id, content_version)
```

Database must enforce uniqueness on this pair.

## Summary request

Endpoint:

```text
POST /api/v1/books/{book_id}/summary
```

Supports:

```text
force_regenerate=false
```

## Workflow

1. Authenticate user.
2. Fetch book.
3. Ensure sufficient source data exists.
4. Check current cache.
5. If cache exists and `force_regenerate=false`, return it.
6. If regeneration is requested or cache missing, build prompt.
7. Send controlled request to AI.
8. Validate returned summary.
9. Persist or reuse the summary row.
10. Return response.

## Important regeneration failure rule

If `force_regenerate=true` and the AI call fails:

- Keep the existing valid cached summary.
- Return an appropriate error.
- Do not delete or corrupt the existing summary.

If regeneration succeeds:

- Replace/update the current summary row for that book version.

## Content version

Every successful book PATCH increments `content_version`.

Therefore old summaries naturally become stale.

## Duplicate generation

Do not implement an in-memory generation lock.

If two rare requests call the AI simultaneously:

- both may reach the external API;
- only one summary row may persist because of the database unique constraint;
- the second request must handle the unique conflict cleanly and reuse the persisted row.

## Quota protection

Use:

- Database-backed cache.
- One summary type.
- Rate limiting.
- Input size limits.
- Controlled `max_tokens`.
- No unnecessary retries.

Do not create custom in-memory per-user AI tracking.

## Rate limiting

Use slowapi on the summary endpoint.

Recommended starting limit:

```text
10 requests/hour/IP
```

Make the value configurable.

## Failure tracking

Initial version may keep a lightweight current-process failure count.

Persistent historical AI event tracking is future work.

## Prompt

Use:

- Title
- Author
- Description
- Category
- Derived extracted-text excerpt from the active PDF

Treat content as untrusted input.

Prevent arbitrary user content from replacing the summarization instruction.

Limit prompt size.

## Acceptance criteria

- AI summary works.
- Standard summary only.
- Cached summary is returned without new AI call.
- `force_regenerate` bypasses cache.
- Failed regeneration preserves previous valid summary.
- Book updates invalidate cache through version.
- External errors map cleanly.
- Token is never exposed.
- Real quota is not consumed in automated tests.

## Tests

Mock the AI client and test:

- Health.
- Usage.
- Generation success.
- Cache hit.
- Cache miss.
- Force regeneration.
- Failed regeneration preserving previous cache.
- 400.
- 401.
- 403.
- 404.
- 429.
- Timeout.
- Malformed response.
- Concurrent summary persistence.

## Depends on

Phase 4.

---

## Additional Feature: Bulk Catalog Creation

> This is an additional operational enhancement added after official Phase 10. It is **not** part of the original Phase 1–13 roadmap and is intentionally separated from the canonical phase sequence below.

### Purpose

Bulk Catalog Creation makes admin catalog entry and development data preparation more efficient without changing the existing catalog domain model, single-resource endpoints, or official roadmap phases.

### Admin-only endpoints

```text
POST /api/v1/authors/bulk
POST /api/v1/categories/bulk
POST /api/v1/books/bulk
```

All three endpoints require the existing `require_admin` authorization dependency. The original single-create contracts remain unchanged:

```text
POST /api/v1/authors
POST /api/v1/categories
POST /api/v1/books
```

### Batch and transaction behavior

- `CATALOG_BULK_MAX_ITEMS` configures the maximum number of items in each request; the default is 50.
- Each bulk operation validates its complete batch and commits once. Book batches use multipart form data: `books` is a JSON metadata array with a unique `file_key` per item, `file_manifest` maps keys to uploaded filenames, and `files` provides exactly one PDF per key.
- Invalid author/category references, duplicate category conflicts, and ISBN conflicts cause the entire relevant batch to roll back.
- ISBNs must also be unique within a bulk-book request.
- Book-file metadata reuses the post-Phase-11 `BookFile` schema; no migration is required for this multipart enhancement.

### Relationship and AI behavior

Bulk books preserve the existing many-to-many relationships:

- One book may reference multiple authors and multiple categories.
- One author or category may be associated with multiple books.
- Existing records are referenced by ID; bulk creation does not duplicate authors or categories for shared relationships.
- Books keep the same normal defaults as single creation, including `content_version = 1`, no active borrows, and not archived.
- Bulk creation never generates AI summaries automatically; summaries remain an explicit separate operation. A failed book batch cleans up stored files and creates no partial catalog records.

### Roadmap relationship

```text
Official roadmap:
Phase 1 -> ... -> Phase 10 -> Phase 11 -> ... -> Phase 13

Additional feature:
Bulk Catalog Creation
    added after Phase 10
    does not replace, renumber, or alter any official phase
```

Verification for this additional feature is part of the current suite; it uses the current `BookFile` migration revision and does not add a migration for multipart bulk uploads.

---

# 16. Phase 11: Admin Statistics

> Note: Bulk Catalog Creation was added separately before this phase as an additional feature; it does not alter this official Phase 11 definition.

## Objectives

Implement SQL aggregation endpoints restricted to ADMIN.

## Statistics

### Users

- Total users.
- New users in last 30 days.
- Active borrowers.

### Books

- Total books.
- Available books.
- Archived books.

### Borrowings

- Active.
- Overdue.
- Borrowings in last 30 days.
- Returns in last 30 days.

### Reservations

- Active reservations.
- Books with waiting lists.

### Ratings

- Total ratings.
- Overall average rating.
- Highest-rated books.

### AI

- Summaries generated.
- Unique books summarized.
- Lightweight current-process summary failure count.

## Required endpoints

```text
GET /api/v1/admin/statistics
GET /api/v1/admin/statistics/popular-books
GET /api/v1/admin/statistics/popular-categories
GET /api/v1/admin/statistics/highest-rated
GET /api/v1/ai/usage
```

`/api/v1/ai/usage` is admin-only when exposed as an administrative quota endpoint.

## Query rules

- Use PostgreSQL aggregation.
- Do not add analytics database.
- Do not add materialized analytics infrastructure.

## Overdue query

Use:

```text
status = ACTIVE
AND due_date < current_time
```

## Highest-rated books

Use average rating grouped by book, ordered descending.

Use a simple assessment-friendly implementation rather than adding a complex recommendation or statistical-ranking system.

## Acceptance criteria

- Statistics match seeded data.
- Admin-only access works.
- Non-admin receives 403.
- Empty data returns sensible values.
- Queries do not expose unrelated user-sensitive data.
- Highest-rated endpoint exists.

## Tests

Seed deterministic known values and verify exact aggregates.

## Depends on

Phases 6–10.

---

## Post-Phase 11 Architectural Revision: Digital Book Storage and Content Architecture

This revision was added after official Phase 11. It does not renumber, rewrite, or claim to have been part of Phases 1–11; the official roadmap continues with Phase 12.

### Completed status

- Completed baseline: Phases 1 through 11.
- Completed post-Phase-11 revision: Digital Book Storage and Content Architecture.
- Completed follow-on enhancement: Multipart Bulk Book Upload.
- Remaining official roadmap: Phase 12, Cross-Cutting Hardening; then Phase 13, Seed Data, Documentation, and Final Verification.

### Decision

- Remove `books.content` as the digital book source of truth.
- Store canonical PDF files in controlled local filesystem storage, never PostgreSQL text or BYTEA.
- Add `Book 1:N BookFile`; one active PDF per book is supported initially.
- Keep safe metadata, checksum, and derived `extracted_text` in PostgreSQL.
- Use a small storage abstraction so future object storage can replace local storage without changing the domain service.

`Book` now represents catalog metadata only. The original `books.content` field has been removed; the authoritative digital content is the stored PDF, while `BookFile.extracted_text` is derived data and cannot preserve PDF images, graphs, tables, formatting, or page layout.

### Workflow and access

- `POST /api/v1/books` is ADMIN-only `multipart/form-data` creation and requires book metadata plus a valid PDF. It validates the file, stores it through the storage abstraction, calculates a checksum, extracts derived text, and creates the `Book`/`BookFile` relationship without storing PDF bytes in PostgreSQL.
- `POST /api/v1/books/{book_id}/file` is ADMIN-only `multipart/form-data` replacement for an unarchived book. It validates/stores the replacement, changes active `BookFile` state, and increments `content_version`.
- `GET /api/v1/books/{book_id}/file` streams actual PDF binary from local storage to an authenticated user with an active borrowing. It is not a metadata response and it does not expose a filesystem path. Returning the borrowing revokes access; archive retains the asset but blocks streaming.
- Stored paths are UUID-generated and never exposed. Uploads validate extension, client MIME type, PDF signature/parser readability, non-empty content, and configured size.
- The existing transactional concurrent-borrowing model remains: `max_concurrent_borrows`, `current_borrows_count`, and `available_slots` are unchanged. No `BookCopy` model is introduced.

### Compatibility and migration

- AI summaries consume available book metadata plus derived PDF text through `BookFile -> extracted_text -> SummaryService -> AI Client`. The existing one-standard-summary cache remains keyed by `(book_id, content_version)`, supports `force_regenerate`, quota protection, rate limiting, safe error mapping, and mocked AI tests. A successful PATCH or PDF replacement increments `content_version`, making prior-version summaries naturally stale.
- `POST /api/v1/books/bulk` is ADMIN-only and multipart-only. `books` is a JSON metadata array containing unique `file_key` values; `file_manifest` maps each key to an uploaded filename; `files` contains the required PDFs. Mapping is deterministic: `file_key -> file_manifest -> uploaded filename -> BookFile -> Book`. OpenAPI represents each `files` item as `type: string`, `format: binary` for Swagger file-picker controls.
- Bulk creation validates the complete batch before database writes. Invalid mappings, duplicate file keys, duplicate/existing ISBNs, missing files, invalid PDFs, invalid author/category references, authorization failures, and other validation failures reject the whole request. Database changes roll back and stored files from a failed batch are cleaned up. Every successful item creates one `Book`, one active `BookFile`, and one stored PDF; AI summaries are never generated automatically. Bulk author and category endpoints remain available.
- Migration `20260814_0002` adds `book_files` and removes `books.content`. Existing short development-only text was not fabricated into invalid digital files; legacy no-file records are archived and their active reservations cancelled, while active borrowings remain returnable.
- `BOOK_STORAGE_ROOT` and `MAX_BOOK_FILE_SIZE_MB` configure local storage; managed storage is Git-ignored.

### Verified results recorded for this revision

- `pytest -q`: 80 tests passed for the digital-storage and bulk-upload verification.
- `alembic check`: no new upgrade operations detected.
- `alembic current`: `20260814_0002 (head)`.
- Manual single-book verification: **The Metamorphosis**, by Franz Kafka in Classic Literature, was created with a PDF; `has_digital_copy = true` and safe file metadata showed its original filename, `application/pdf`, file size, and `PDF` format.
- Manual multipart bulk verification: **Pride and Prejudice** and **Test Bulk Book** were created with independently mapped PDFs; each received `has_digital_copy = true`, a corresponding `BookFile`, and PDF metadata.
- Manual retrieval verification: `GET /api/v1/books/{book_id}/file` returned the stored PDF. Swagger displayed raw binary content as text because of its response renderer, but the response was a downloadable PDF.
- Manual authorization verification: an active borrowing allowed PDF streaming; returning that borrowing revoked access.

Swagger presentation is distinct from backend behavior: the upload OpenAPI schema uses binary file items, while Swagger may display a streamed PDF as unrecognized text. The API response remains the actual PDF binary.

---

# 17. Phase 12: Cross-Cutting Hardening

## Tasks

Implement or finalize:

- slowapi rate limiting.
- Request-ID middleware.
- CORS.
- Common exception handlers.
- Structured logging.
- OpenAPI tags/descriptions.
- Common pagination response schema.
- Final authorization review.
- Final IDOR review.
- Final validation review.
- Final transaction review.

## Security checklist

Verify:

- Passwords are hashed.
- JWT secret comes from environment.
- AI token comes from environment.
- AI token is not logged.
- User data is ownership-protected.
- Admin endpoints are protected.
- ORM parameters prevent SQL injection.
- Secrets are absent from source control.
- Sensitive data is absent from logs.

## Rate limiting

At minimum protect:

- Login.
- Registration.
- AI summary generation.

Do not create custom in-memory rate-limit dictionaries.

## Acceptance criteria

- Full suite passes.
- Authorization is consistent.
- Rate limits work.
- Error format is consistent.
- No secret appears in logs.
- OpenAPI is usable.

## Depends on

Phases 1–11.

---

# 18. Phase 13: Seed Data, Documentation, and Final Verification

## Seed data

Create deterministic demonstration data:

- 1 admin.
- 5 regular users.
- 10 authors.
- 8 categories.
- 20 books.
- Active borrowings.
- Returned borrowings.
- Overdue borrowings.
- Pending reservations.
- READY reservations.
- Favorites.
- Ratings.
- Optional cached summaries.

Do not put real secrets in seed scripts.

Any demo password shown in documentation must be clearly identified as local-development-only.

## README

The final README must include:

1. Project overview.
2. Features.
3. Tech stack.
4. Architecture.
5. ER diagram.
6. API documentation.
7. Authentication and authorization.
8. Borrowing workflow.
9. Reservation workflow.
10. Favorites and ratings.
11. AI integration.
12. AI token security.
13. AI caching and quota protection.
14. Local PostgreSQL setup.
15. Python environment setup.
16. Environment variables.
17. Alembic migrations.
18. Seed data.
19. Test commands.
20. Design decisions.
21. Assumptions.
22. Trade-offs.
23. Implemented vs future features.

## No-Docker requirement

README setup must work without Docker.

## Clean-start verification

Perform:

```text
Fresh clone
  ↓
Create Python virtual environment
  ↓
Install requirements
  ↓
Configure PostgreSQL
  ↓
Create .env
  ↓
Run Alembic migrations
  ↓
Run seed script
  ↓
Start Uvicorn
  ↓
Open Swagger
  ↓
Run tests
```

## Acceptance criteria

- Fresh setup works.
- Database migrates cleanly.
- Seed data loads.
- Application starts.
- Swagger is available.
- Tests pass.
- README instructions are accurate.
- No secret is committed.

## Depends on

Phases 1–12.

---

# 19. Testing Strategy

Testing must happen throughout implementation.

## Unit testing

Cover:

- Authentication rules.
- Book rules.
- Borrow limits.
- Reservation rules.
- Favorite rules.
- Rating rules.
- Summary cache decisions.
- AI error mapping.
- Admin calculation logic.

## Integration testing

Cover:

- Registration/login.
- Protected routes.
- Books.
- Search.
- Borrowing.
- Reservations.
- Favorites.
- Ratings.
- Admin statistics.

## Database integrity tests

Explicitly verify:

- Unique email.
- Unique username.
- Unique ISBN.
- Unique favorite.
- Unique rating.
- Partial unique active reservation.
- Unique book summary cache key.
- Rating CHECK.
- Foreign keys.

## Concurrency tests

Cover:

1. Two users borrowing final slot.
2. Two concurrent active reservations from same user for same book.
3. Return + reservation promotion.
4. Concurrent favorite creation.
5. Concurrent rating upsert where practical.
6. Concurrent AI summary persistence.

## AI tests

Never call the real Userfacet API in automated tests.

Mock the AI client.

Test:

- Success.
- Cache hit.
- Cache miss.
- Force regenerate.
- Regeneration failure preserving old cache.
- 400.
- 401.
- 403.
- 404.
- 429.
- Timeout.
- Malformed response.

---

# 20. Implementation Order Within Each Phase

For database-backed features:

```text
Model
  ↓
Migration
  ↓
Schema
  ↓
Repository
  ↓
Service
  ↓
Router
  ↓
Tests
```

For AI:

```text
Configuration
  ↓
AI Client
  ↓
Mocked client tests
  ↓
Summary Model / Migration
  ↓
Summary Repository
  ↓
Summary Service
  ↓
Summary Router
  ↓
Integration Tests
```

Do not build routes first and retrofit the architecture later.

---

# 21. MUST / SHOULD / FUTURE

## MUST IMPLEMENT

- Authentication.
- User profile and roles.
- Books.
- Authors.
- Categories.
- Search/filter/sort/pagination.
- Borrowing.
- Reservations.
- Favorites.
- Ratings.
- Standard AI summary.
- AI caching.
- AI quota protection.
- Admin statistics.
- Error handling.
- Alembic migrations.
- Unit and integration tests.
- Seed data.
- README.

## SHOULD IMPLEMENT

- slowapi.
- Request-ID middleware.
- CORS configuration.
- pg_trgm optimization if convenient.
- Strong OpenAPI descriptions.

## FUTURE

- Docker.
- Redis.
- Celery.
- Elasticsearch.
- Kafka.
- Microservices.
- Email notifications.
- WebSockets.
- Advanced recommendations.
- Persistent AI event history.
- Distributed AI locking.
- Multiple summary modes.
- Cursor pagination.
- OAuth/social login.
- Account deactivation.

---

# 22. Implementation Gate Checklist

Before starting each major phase, confirm:

## Architecture

- Synchronous FastAPI.
- Synchronous SQLAlchemy.
- Synchronous httpx.
- No AsyncSession.
- No AsyncClient.
- No pytest-asyncio.
- Exactly one root-level `alembic.ini`.
- No Docker requirement.
- No Redis/Celery/Elasticsearch/microservices.

## AI

- One standard summary.
- No `summary_type` column.
- Cache key `(book_id, content_version)`.
- Unique DB cache key.
- `force_regenerate`.
- Token from environment.
- No token in logs/responses/source.
- No in-memory AI generation lock.
- No custom in-memory per-user AI limiter.
- Real AI quota not consumed by tests.

## Reservations

- Partial unique index required.
- Relevant book row locking for queue mutation.
- Deterministic position.
- Promotion on return.
- READY expiry.
- Archive cancellation.

## Borrowing

- Stored status only ACTIVE/RETURNED.
- OVERDUE computed.
- Book row locked for borrow.
- Counter changes transactional.
- Archived-book active borrow remains returnable.

## Database

- No `users.is_active`.
- Favorite uniqueness.
- Rating uniqueness.
- Rating CHECK.
- ISBN uniqueness.
- Foreign keys.
- AI summary uniqueness.

## Admin

- Overview statistics.
- Popular books.
- Popular categories.
- Highest-rated books.
- AI usage admin access.

---

# 23. Definition of Done

The backend is complete only when:

1. Application starts.
2. PostgreSQL schema is created by Alembic.
3. Authentication works.
4. Role-based access works.
5. Books work.
6. Search works.
7. Borrowing works.
8. Final-slot concurrency is handled.
9. Reservations work.
10. Reservation uniqueness is database-enforced.
11. Favorites work.
12. Ratings work.
13. AI summaries work through the supplied Userfacet API.
14. AI token is protected.
15. AI caching works.
16. AI quota protection works.
17. Admin statistics work.
18. Highest-rated statistics work.
19. Error responses are consistent.
20. Tests pass.
21. Seed data works.
22. README is accurate.
23. No secrets are committed.
24. No unnecessary infrastructure is required.

---

# 24. Final Implementation Roadmap

```text
Phase 1
Project foundation
        ↓
Phase 2
PostgreSQL + SQLAlchemy + Alembic
        ↓
Phase 3
Authentication + users
        ↓
Phase 4
Books + authors + categories
        ↓
Phase 5
Search + filters + pagination
        ↓
Phase 6
Borrowing + concurrency
        ↓
Phase 7
Reservations + waiting list
        ↓
Phase 8
Favorites
        ↓
Phase 9
Ratings
        ↓
Phase 10
AI summaries + cache + quota protection
        ↓
Phase 11
Admin statistics
        ↓
Phase 12
Security + rate limiting + errors + observability
        ↓
Phase 13
Seed data + README + final verification
```

The implementation must proceed phase by phase.

At the end of each phase:

1. Run relevant tests.
2. Verify acceptance criteria.
3. Review changed files.
4. Check architecture consistency.
5. Fix issues before moving forward.

---

# 25. Final Instruction to the Coding Agent

Use `architecture.md` and this `implementation_plan.md` as the canonical implementation documents.

Before writing code:

1. Confirm synchronous execution.
2. Confirm no Docker is required.
3. Confirm the current 13-entity domain model, including `BookFile` and no `books.content` field.
4. Confirm a single standard AI summary.
5. Confirm cache key `(book_id, content_version)`.
6. Confirm unique AI cache constraint.
7. Confirm `force_regenerate`.
8. Confirm reservation partial unique index.
9. Confirm reservation queue uses safe transactional ordering.
10. Confirm stored borrowing statuses are only ACTIVE/RETURNED.
11. Confirm OVERDUE is computed.
12. Confirm `users.is_active` is absent.
13. Confirm book archive side effects.
14. Confirm highest-rated admin statistics.
15. Confirm AI token comes only from environment configuration.

Then implement one phase at a time.

Do not silently redesign the architecture.

If implementation reveals a real contradiction or missing requirement, stop before making a major architectural change, explain the issue, and recommend the smallest correction.

The goal is a complete, secure, maintainable student backend that follows the approved architecture and can be confidently explained in an interview.
