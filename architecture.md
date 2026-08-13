# E-Library Backend Architecture

## 1. Overview

This document is the canonical architecture for the E-Library Management System backend.

The system is a student-level, modular monolith built with Python and FastAPI. It provides book management, users, borrowing, searching, reservations, favorites, ratings, admin statistics, and AI-powered book summaries.

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
  v                      v
PostgreSQL         Userfacet AI API
```

The backend is a **modular monolith**.

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
├── migrations/
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
│   │       ├── summaries.py
│   │       ├── admin.py
│   │       └── health.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── exceptions.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── book.py
│   │   ├── author.py
│   │   ├── category.py
│   │   ├── borrowing.py
│   │   ├── reservation.py
│   │   ├── favorite.py
│   │   ├── rating.py
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
│   │   ├── summary.py
│   │   └── admin.py
│   │
│   ├── repositories/
│   │   ├── user.py
│   │   ├── book.py
│   │   ├── borrowing.py
│   │   ├── reservation.py
│   │   ├── favorite.py
│   │   ├── rating.py
│   │   ├── summary.py
│   │   └── statistics.py
│   │
│   ├── services/
│   │   ├── auth.py
│   │   ├── book.py
│   │   ├── borrowing.py
│   │   ├── reservation.py
│   │   ├── favorite.py
│   │   ├── rating.py
│   │   ├── summary.py
│   │   └── admin.py
│   │
│   ├── clients/
│   │   └── ai_client.py
│   │
│   ├── dependencies/
│   │   └── auth.py
│   │
│   └── middleware/
│       ├── request_id.py
│       └── cors.py
│
└── tests/
    ├── unit/
    └── integration/
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
- content
- publication_year
- max_concurrent_borrows
- current_borrows_count
- content_version
- is_archived
- created_at
- updated_at

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

## 21. AI Summary Architecture

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

## 22. AI Cache

Cache key:

```text
(book_id, content_version)
```

Any `PATCH /books/{id}` increments `content_version`.

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

## 23. AI Regeneration

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

## 24. AI Quota Protection

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

## 25. AI Token Security

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

## 26. AI External Error Handling

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

## 27. AI Prompt

The generated prompt should use available book information such as:

- Title
- Author
- Description
- Category
- Content/excerpt

Use a controlled system/user prompt.

Do not allow arbitrary client-provided instructions to replace the intended summarization task.

Limit content size before sending it upstream.

Treat book content as untrusted input from a prompt-injection perspective.

---

## 28. Search

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

## 29. Pagination

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

## 30. Authentication

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

## 31. Authorization

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

## 32. API Versioning

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

## 33. API Groups

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
PATCH /api/v1/books/{book_id}
POST  /api/v1/books/{book_id}/archive
POST  /api/v1/books/{book_id}/restore
```

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

### AI Summaries

```text
POST /api/v1/books/{book_id}/summary
GET  /api/v1/books/{book_id}/summary
GET  /api/v1/ai/usage
GET  /api/v1/ai/health
```

`POST /summary` accepts `force_regenerate`.

It does not accept `summary_type`.

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

## 34. Consistent Error Format

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

## 35. Admin Statistics

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

## 36. AI Failure Statistics

Persistent AI failure analytics are not required.

The initial implementation may use a lightweight in-memory failure counter or application logs for failure visibility.

Persistent AI event history is a future enhancement.

Do not add a dedicated AI event-sourcing system.

---

## 37. Rate Limiting

Use `slowapi` for simple single-instance rate limiting.

The AI summary endpoint should have a stricter rate limit, such as:

```text
10 requests/hour per IP
```

The exact value is configuration and should be documented.

Do not implement an additional custom in-memory per-user tracker.

---

## 38. Middleware

Recommended lightweight middleware:

- CORS configuration
- Request ID

Do not add complex observability infrastructure.

---

## 39. Configuration

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
```

Actual secrets must never be committed.

---

## 40. Database Migrations

Use Alembic.

Only one `alembic.ini` exists at project root.

Directory:

```text
migrations/
├── env.py
├── script.py.mako
└── versions/
```

Never create a second `alembic.ini` inside `migrations/`.

---

## 41. Transactions

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

## 42. Testing Strategy

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

## 43. Seed Data

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

## 44. Local Development

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

## 45. README Requirements

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

## 46. Important Trade-offs

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

---

## 47. Future Improvements

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
- File/object storage
- Cursor pagination
- Distributed locking for AI generation
- More advanced search

These are not part of the initial implementation.

---

## 48. Final Implementation Boundary

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

## 49. Final Architecture Summary

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
borrowings
reservations
favorites
ratings
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
