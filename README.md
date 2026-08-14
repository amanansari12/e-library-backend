# E-Library Management System Backend

This repository contains the backend for a modern E-Library Management System. It models the core operations of a physical and digital library, providing robust features for users to explore catalogs, borrow books, manage reservations, read digital copies, and track their reading progress. 

Built with FastAPI and PostgreSQL, the system is designed for high performance and strict type safety. It goes beyond simple CRUD operations by implementing real-world library business logic, such as enforcing borrowing limits, managing waiting lists, deriving reading progress across document versions, and abstracting digital file storage to maintain a clean separation between database metadata and binary assets.

The backend provides a comprehensive suite of features including role-based authentication, digital access control, user ratings and reviews, AI-generated book summaries, and administrative statistics.

---

# 1. Project Highlights

* JWT authentication
* Role-based admin authorization
* PostgreSQL persistence
* Alembic migrations
* Local digital file storage abstraction
* SHA-256 file integrity
* Borrowing-based PDF access control
* Content-version-aware reading progress
* Reservations with READY/PENDING states
* Reviews and ratings
* Favorites
* AI summary caching
* Rate limiting
* Request correlation IDs
* Isolated integration test database
* Reusable real-book catalog
* Local admin bootstrap

---

# 2. Architecture Overview

The system uses a layered architecture, cleanly separating the API transport layer from the core business logic and storage abstractions.

```text
Client / Frontend / Swagger
            |
            v
        FastAPI API
            |
    +-------+--------+
    |       |        |
    v       v        v
PostgreSQL Services Storage
                    |
                    v
              storage/books/
```

* **API/router layer**: Defines the HTTP endpoints and handles input validation using Pydantic schemas.
* **Dependencies/authentication**: Provides reusable dependency injection for database sessions and role-based authentication.
* **Domain/services**: Contains the core business logic (e.g., borrowing rules, reservation state transitions).
* **SQLAlchemy models**: Defines the database schema and object-relational mapping.
* **Database**: PostgreSQL manages all relational data (users, metadata, relations).
* **Storage abstraction**: Manages local digital files securely, shielding binary data from the database.
* **Seed/data assets**: A curated library catalog used for testing and demonstration.
* **Tests**: Comprehensive pytest suite running against an isolated PostgreSQL instance.

---

# 3. How the Main Book Flow Works

The lifecycle of a book and its digital content is strictly managed:

```text
Admin creates book
      ↓
PDF uploaded
      ↓
BookFileService
      ↓
SHA-256 integrity check
      ↓
storage/books/{book_id}/{storage_key}/canonical.pdf
      ↓
BookFile database record
      ↓
User borrows book
      ↓
PDF retrieval allowed
```

When a user finishes reading or the borrowing period expires:

```text
Book returned
      ↓
PDF access revoked
```

The database stores metadata (title, author, `storage_key`, `content_version`) while the local storage layer (`BookFileService`) owns the canonical PDF binary on the filesystem. 
If an admin uploads a new PDF for an existing book, the `content_version` increments. This invalidates cached AI summaries and flags users' previous reading progress as stale, ensuring they know the content has changed.

---

# 4. Project Structure

```text
e-library-backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── dependencies/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── storage/
│   └── main.py
├── alembic/
├── data/
│   ├── books/
│   ├── book_catalog.json
│   ├── authors.json
│   ├── categories.json
│   └── sources.json
├── docs/
├── scripts/
├── storage/
├── tests/
├── .env.example
└── requirements.txt
```

* **`app/main.py`**: The FastAPI application entrypoint.
* **`app/models/` & `app/schemas/`**: SQLAlchemy ORM models and Pydantic validation schemas.
* **`app/api/` & `app/dependencies/`**: Route definitions and authentication dependency injection.
* **`app/services/` & `app/storage/`**: Business logic and the local file storage abstraction.
* **`alembic/`**: Database migration versions.
* **`scripts/seed.py`**: The default demonstration data bootstrap script.
* **`scripts/create_admin.py`**: The interactive local admin provisioning tool.
* **`scripts/validate_catalog.py`**: Integrity checker for the developer source catalog.
* **`data/` & `data/books/`**: Reusable real-book test assets.
* **`docs/API_REFERENCE.md`**: Complete REST API endpoint documentation.
* **`tests/`**: Integration tests using isolated fixture-driven state.

---

# 5. Configuration

Environment variables configure the application. Copy `.env.example` to `.env` to begin.

### Runtime configuration
* `DATABASE_URL`: PostgreSQL connection string for the main application.
* `JWT_SECRET_KEY`: Secret key for signing authentication tokens.
* `BOOK_STORAGE_ROOT`: The directory where the runtime manages PDFs (default: `storage/books`).
* `MAX_BOOK_FILE_SIZE_MB`: Limit for PDF uploads.
* **AI configuration**: Credentials for external AI summary generation.
* **CORS configuration**: Allowed origins for frontend clients.
* **Rate limits**: Request limits for API protection.

### Test-only configuration
* `TEST_DATABASE_URL`: Used exclusively by `pytest`. This must point to a separate PostgreSQL database to ensure tests do not destroy development data.

---

# 6. Local Setup

Requirements: Python 3.11+ and PostgreSQL 15+.

```bash
# 1. Clone the repository
git clone <repository_url>
cd e-library-backend

# 2. Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# 5. Run database migrations
alembic upgrade head

# 6. Verify migration status (Expected: 20260814_0004)
alembic current
```

---

# 7. Create a Local Admin

The application does not have a public self-admin endpoint for security reasons. To bootstrap a local operator, run:

```bash
python scripts/create_admin.py
```

This interactive CLI tool can safely create a new admin or promote an existing user. It handles duplicate emails and ensures role-based constraints. Multiple administrators are fully supported.

---

# 8. Seed Demo Data (Development)

**Development only.**
To populate the database with a rich demonstration environment, run:

```bash
python scripts/seed.py
```

This script reads from `data/book_catalog.json` (specifically filtering for `seed_demo=true`) and seeds exactly 8 default demo books along with representative relational data.
Current seed output:
* 6 users, 15 authors, 11 categories, 8 demo books, 8 BookFiles, 8 borrowings, 3 reservations, 3 favorites, 4 ratings, 2 reviews, 3 reading progress, 3 summaries

---

# 9. Production Demo Bootstrap

**Production Interviewer Environment only.**
To safely populate the deployed interviewer environment, run:

```bash
python scripts/bootstrap_production_demo.py
```

While `scripts/seed.py` is exclusively for local development and destroys duplicate environments, `scripts/bootstrap_production_demo.py` is safely idempotent and protects existing production state.

**Behavior:**
* **Safety**: Requires `APP_ENV=production`. Never drops tables, never downgrades schemas, and skips any existing records.
* **Books**: Safely imports the exactly 8 demo books (`seed_demo=true`) and matching PDFs using the production `BookFileService` into `BOOK_STORAGE_ROOT`.
* **Admins**: Safely preserves your manually created production admin (via `create_admin.py`). It never creates a hard-coded admin.
* **Demo Users**: Creates demo user accounts (alice, bob, carol, dave, erin) required for the interviewer workflow. It requires you to provide the `DEMO_USERS_PASSWORD` environment variable to securely set their credentials without hardcoding secrets.
* **Relations**: Seeds representative borrowings, reservations, favorites, ratings, reviews, progress, and deterministic cached AI summaries to demonstrate the full application experience.

---

# 9. Clean Database Reset

**WARNING: destroys development database data. DEVELOPMENT ONLY.**

```bash
alembic downgrade base
alembic upgrade head
python scripts/seed.py
```

---

# 10. The 20 Reusable Book Assets

The `data/books/` directory contains 20 real, repository-owned book PDFs.
* **8 are default demo books** automatically imported by the seed script.
* **12 are additional developer assets** intended for developers or interviewers to use when manually testing the book creation and PDF upload workflows.

These assets are safely tracked in Git. For a complete list of all 20 titles and their metadata, see `docs/BOOK_CATALOG.md` and `data/book_catalog.json`.

---

# 11. Runtime Storage vs Catalog Assets

The repository maintains a strict distinction between source assets and the application's runtime data.

* `data/books/`: Repository-owned source/test assets, safely committed to Git.
* `storage/books/`: Application-managed runtime storage, strictly ignored by Git.

When the application or seed script imports a book, the `BookFileService` securely copies the file into an isolated hashed directory (`storage/books/{book_id}/{storage_key}/canonical.pdf`). This ensures the application never mutates the repository's source assets.

---

# 12. How to Add Another Book

To manually add one of the 12 unseeded developer assets:
1. Browse `data/book_catalog.json` and choose an unseeded book.
2. Ensure you have an active Admin token.
3. Use the `POST /api/v1/books/` endpoint to create the book metadata.
4. Use the `POST /api/v1/books/{book_id}/file` endpoint to upload the corresponding PDF from `data/books/`.
5. The `BookFileService` will hash and store it in `storage/books/`.
6. You can now use a normal user token to test borrowing, PDF retrieval, and reading progress.

See `docs/API_REFERENCE.md` for exact request bodies and responses.

---

# 13. Authentication and Authorization

The API uses standard OAuth2 Password Flow with Bearer tokens (JWT). 
* Public endpoints handle registration and login.
* Standard protected endpoints require a valid `USER` token.
* Administrative endpoints require an `ADMIN` role token.
Users must hold an active borrowing to access a book's PDF or update reading progress. Written reviews also enforce a historical borrowing requirement, and only the owner of a review can update or delete it.

---

# 14. Core Domain Workflows

### Borrowing
Users can borrow up to 5 books. 
`borrow → active borrowing → PDF access permitted`
`return → active borrowing closed → PDF access revoked`

### Reservations
If a book has zero available copies, a user can reserve it. The state begins as `PENDING`. When a copy is returned, the oldest reservation is promoted to `READY`, reserving the copy specifically for that user for 48 hours.

### Reading Progress
Tracks the user's current `page`, the `total_pages`, and derives a `percentage`. Updates are only permitted during an active borrowing. Progress is bound to a specific `content_version`. If an admin replaces the PDF, progress is marked with a stale flag. After returning the book, the user has read-only access to their final progress.

### Reviews
Users can leave a maximum of one written review per book, provided they have a borrowing history with that book. Users can only update or delete their own reviews.

### Ratings
1-5 star ratings. The system aggregates these to expose `average_rating` and `rating_count` on the book metadata.

### Favorites
Users can bookmark their favorite books to easily retrieve them later.

### AI Summaries
The system can generate AI summaries for books. Summaries are aggressively cached in the database. If an admin replaces a book's PDF (bumping the `content_version`), the cache is busted and a fresh summary must be generated.

---

# 15. API Documentation

Complete API reference: `docs/API_REFERENCE.md`

An interactive Swagger UI is available at runtime:
`http://localhost:8000/docs`

The API is grouped logically by feature area (Auth, Books, Borrowings, Ratings, Admin Statistics, etc.).

---

# 16. Running the Application

```bash
uvicorn app.main:app --reload
```
Health Check: `http://localhost:8000/health`
Swagger UI: `http://localhost:8000/docs`

---

# 17. Running Tests

```bash
pytest -q
```
Tests require `TEST_DATABASE_URL` in your `.env` to point to an isolated PostgreSQL instance. The test suite spins up isolated deterministic fixture states and does not rely on the developer seed data.
Current verified result: `107 passed`

---

# 18. Security Notes

* `.env` and `storage/` are strictly ignored by Git.
* Secrets and AI credentials are provided via environment variables.
* JWT payloads do not leak sensitive user data.
* Internal filesystem paths and `storage_key` UUIDs are never exposed in public API responses.
* Administrative endpoints are strongly protected by role checks.
* There is no public self-admin endpoint.
* Rate limiting prevents abuse.
* Request correlation IDs allow secure diagnostic tracing.
* Errors are wrapped in a safe envelope to prevent stack trace leaks.

---

# 19. Testing Philosophy

The testing strategy emphasizes behavior-driven integration coverage:
`unit/domain/API integration tests + isolated PostgreSQL test database + clean deterministic fixtures`
Using a separate database guarantees that destructive tests never damage the developer's local seed data, ensuring a reliable local development loop.

---

# 20. Important Files to Read First

If you are reviewing this project, start here in order:
1. `README.md` - Overall system context (you are here).
2. `architecture.md` - Deeper technical architecture decisions.
3. `app/main.py` - Application bootstrapping and middleware configuration.
4. `app/dependencies/auth.py` - Role-based authorization implementation.
5. `app/api/v1/books.py` - Core router demonstrating dependency injection.
6. `app/services/book_file.py` - Domain logic bridging DB metadata and binary storage.
7. `app/storage/local.py` - The low-level filesystem abstraction.
8. `app/models/` - SQLAlchemy schemas defining relational constraints.
9. `scripts/seed.py` - Demonstrates how the data models interconnect.
10. `scripts/create_admin.py` - The secure bootstrapping utility.
11. `docs/API_REFERENCE.md` - The complete capability surface area.
12. `tests/` - Example of isolated fixture-based integration testing.

---

# 21. Interviewer Quick Start

1. Clone the repository.
2. Configure PostgreSQL and your `.env` file.
3. Install dependencies (`pip install -r requirements.txt`).
4. `alembic upgrade head`
5. `python scripts/create_admin.py`
6. `python scripts/seed.py`
7. `uvicorn app.main:app --reload`
8. Open `http://localhost:8000/docs`

Recommended demonstration flow:
`Browse books → Login → Borrow → Retrieve PDF → Update reading progress → Favorite → Rate/review → Return → Verify PDF access is revoked → Inspect reservations → Login as admin → View admin statistics → Open API reference`

---

# 22. Current Project Status

Current status:
* Feature-frozen backend
* Migration head: `20260814_0004`
* Automated tests: 107 passing
* 20 reusable real-book assets
* 8 default demo books
* 12 additional developer assets

---

# 23. Future Considerations

The following technologies were intentionally omitted to maintain focus on core library modeling and minimize deployment complexity:
* Docker
* Redis
* Celery / Kafka
* Elasticsearch
* WebSockets
* Microservices

---

# 24. Frontend Note

Frontend:
A separate React/TypeScript client can consume this REST API. There is currently no frontend implemented within this backend repository.
