# E-Library Management System Backend

## Live Deployment

The backend is currently deployed on Railway.

### Production API
**Base URL:** https://e-library-backend-production.up.railway.app
**Health:** https://e-library-backend-production.up.railway.app/health
**Swagger UI:** https://e-library-backend-production.up.railway.app/docs
**OpenAPI JSON:** https://e-library-backend-production.up.railway.app/openapi.json

### Production Infrastructure
- **Hosting:** Railway
- **Application:** FastAPI
- **Database:** Railway PostgreSQL
- **Runtime PDF Storage:** Railway Persistent Volume
- **Migration Head:** `20260814_0004`

> **Demo Environment Notice:** This live deployment is intended for portfolio/interviewer evaluation. The credentials shown below are demonstration credentials only and must not be reused for a real production deployment.

> The production database and runtime storage are separate from the local development environment.

## Demo Access

### Public Demo User

Username: `alice`  
Password: `Demo1234`

The same demo password is used for the other seeded demo users:

`bob`, `carol`, `dave`, `erin`

### Demo Administrator

Email: `admin@example.com`  
Password: `Admin@123`

> **Temporary Demo Credential Disclaimer**
>
> The administrator password is currently documented because this deployment is being used as a temporary interviewer/portfolio demonstration environment.
>
> This credential is **not intended for production or sensitive use**. Before this application is used for any real deployment, the administrator password will be rotated and this password will be removed from the README.
>
> For self-hosted/local deployments, administrators should be created using:
>
> ```bash
> python scripts/create_admin.py
> ```

---

## 1. Project Overview

This is a FastAPI E-Library Management System backend. It models the core operations of a physical and digital library. PostgreSQL stores relational data, while local/runtime storage manages digital PDFs. 

Users borrow books, and their digital access depends on their borrowing state. Reservations manage unavailable books. Users can track reading progress, and can favorite, rate, and review books. Administrators can manage the catalog and view statistics. AI summaries are cached and version-aware. The project includes reusable real public-domain book assets. 

The frontend is not currently part of this repository.

## 2. Features

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

## 3. Architecture

```text
Client / Swagger / Future Frontend
               |
               v
            FastAPI
               |
      +--------+---------+
      |                  |
      v                  v
 PostgreSQL         Application Services
                         |
                         v
                  BookFileService
                         |
                         v
                  Runtime PDF Storage
```

* **API/router layer**: Defines the HTTP endpoints and handles input validation using Pydantic schemas.
* **Dependencies/authentication**: Provides reusable dependency injection for database sessions and role-based authentication.
* **Domain/services**: Contains the core business logic.
* **SQLAlchemy models**: Defines the database schema and object-relational mapping.
* **Database (PostgreSQL)**: Manages all relational data (users, metadata, relations).
* **Storage abstraction (`BookFileService`)**: Manages local digital files securely, shielding binary data from the database. Digital PDF bytes are not stored directly inside the main `books` table to maintain a clean separation between database metadata and binary assets, allowing efficient file delivery and versioning.
* **AI client**: Generates AI book summaries.
* **Tests**: Comprehensive pytest suite.

## 4. Project Structure

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
* **`app/core/config.py`**: Configuration definition.
* **`app/core/security.py`**: Authentication and security definitions.
* **`app/api/`**: HTTP endpoints.
* **`app/services/book_file.py`**: Digital PDF workflow logic.
* **`app/storage/`**: Runtime storage abstraction.
* **`scripts/seed.py`**: Development bootstrap script.
* **`scripts/create_admin.py`**: Admin provisioning tool.
* **`scripts/bootstrap_production_demo.py`**: Production demo data bootstrap.
* **`scripts/validate_catalog.py`**: Developer catalog validation.
* **`scripts/download_and_build_pdfs.py`**: PDF build utility.
* **`docs/API_REFERENCE.md`**: Complete API documentation.
* **`docs/BOOK_CATALOG.md`**: 20 real books metadata mapping.
* **`.env.example`**: Example environment variables.
* **`requirements.txt`**: Python dependencies.

## 5. Configuration

### Runtime variables
Variables from `.env.example` configure the application:
* `APP_ENV`: Application environment (development or production).
* `DEBUG`: Debug mode toggle.
* `DATABASE_URL`: Main application database connection URL.
* `JWT_SECRET_KEY`: Secret key for JWT signing.
* `AI_API_TOKEN`: Token for Userfacet AI summaries.
* `CORS_ORIGINS`: Allowed frontend origins.
* `BOOK_STORAGE_ROOT`: Path to persistent PDF location.
* `MAX_BOOK_FILE_SIZE_MB`: Max PDF file size upload limit.
* `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiry.
* `JWT_REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token expiry.
* `RATE_LIMIT_GLOBAL`, `RATE_LIMIT_LOGIN`, etc.: Rate-limit settings.

### Test-only variable
* `TEST_DATABASE_URL`: This is only for pytest/test environments and must be a separate database from the application database.
> **DO NOT CONFIGURE TEST_DATABASE_URL FOR THE PRODUCTION APPLICATION.**

## 6. Local Development Setup

Requirements: Python 3.11+ and PostgreSQL 15+.

```bash
git clone <repository-url>
cd e-library-backend

python -m venv .venv
```

Windows:
```powershell
.venv\Scripts\activate
```

Linux/macOS:
```bash
source .venv/bin/activate
```

Install:
```bash
pip install -r requirements.txt
```

Create `.env` from `.env.example`. Configure your local PostgreSQL.

Run:
```bash
alembic upgrade head
```

Verify:
```bash
alembic current
```
Expected: `20260814_0004 (head)`

Start:
```bash
uvicorn app.main:app --reload
```

Then:
* http://localhost:8000/health
* http://localhost:8000/docs

## 7. Local Admin Setup

```bash
python scripts/create_admin.py
```
This is an operator/bootstrap tool. It creates a new admin or can promote an existing user. It supports multiple administrators, prevents duplicate emails, and does not expose a public self-admin API.

Never publish the actual production admin password in README.

## 8. Development Demo Seed

**DEVELOPMENT ONLY**

```bash
python scripts/seed.py
```

It reads `data/book_catalog.json`, selects `seed_demo=true`, requires exactly 8 demo books, and creates deterministic development/demo data. It is designed for local development/testing and must NOT be run against production.

Current verified output:
6 users, 15 authors, 11 categories, 8 demo books, 8 BookFiles, 8 borrowings, 3 reservations, 3 favorites, 4 ratings, 2 reviews, 3 reading progress records, 3 book summaries.

**Clean Reset (WARNING: destroys development data)**
```bash
alembic downgrade base
alembic upgrade head
python scripts/seed.py
```

## 9. Production Demo Bootstrap

**PRODUCTION BOOTSTRAP ONLY**

```bash
python scripts/bootstrap_production_demo.py
```

This initializes a live/interviewer database without resetting it.

**Safety**: It requires `APP_ENV=production`, `DATABASE_URL`, and `DEMO_USERS_PASSWORD`. It never drops tables, never downgrades migrations, never deletes existing data, and preserves existing admin accounts.

**Behavior**: It creates only the 8 `seed_demo=true` books, creates required authors/categories, imports PDFs through `BookFileService`, creates representative demo relationships, avoids live AI calls, and is idempotent.

Verified idempotency:
```text
Run 1:
Created: 65
Skipped: 0

Run 2:
Created: 0
Skipped: 65
```

## 10. Real Book Catalog Assets

`data/books/` contains 20 real public-domain book PDFs:
* 8 `seed_demo=true` (used by default seed/bootstrap)
* 12 `seed_demo=false` (reusable manual testing assets)

Metadata lives in `data/book_catalog.json`, authors in `data/authors.json`, categories in `data/categories.json`, and provenance in `data/sources.json`. Detailed mapping is in `docs/BOOK_CATALOG.md`.

Clarification:
* `data/books/` = repository-owned source assets
* `storage/books/` = runtime-managed application files

## 11. Runtime PDF Storage

The production path exactly: `/app/storage/books/`
The application-managed structure: `/app/storage/books/{book_id}/{storage_key}/canonical.pdf`

`BookFileService` manages PDF access. When a PDF is uploaded, it is assigned a SHA-256 checksum and a `storage_key`. It becomes the active BookFile and the `content_version` increments. PDF access control is based on user borrowing status. File replacement increments the `content_version`, invalidating cached AI summaries and flagging existing reading progress records as stale.

Runtime PDF storage must be persistent in production.

## 12. API Documentation

Full reference: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
Local Swagger: http://localhost:8000/docs
Production Swagger: https://e-library-backend-production.up.railway.app/docs
**OpenAPI JSON:** https://e-library-backend-production.up.railway.app/openapi.json

## 13. Running Tests

```bash
pytest -q
```
Current verified result: `107 passed`. Test isolation is maintained through `TEST_DATABASE_URL`. Tests do not run against production.

## 14. Production Deployment

```text
GitHub
   |
   v
Railway
   |
   +-------------------+
   |                   |
   v                   v
FastAPI Service     PostgreSQL
   |
   v
Persistent Volume
/app/storage/books
```

GitHub stores source, Railway hosts FastAPI, Railway PostgreSQL stores relational data, and a Railway Volume stores runtime PDFs.

## 15. Railway Deployment Step-by-Step

**Step 1: Create Railway account**
The Railway Google account does NOT need to be the same Google account used for GitHub. The GitHub account connected to Railway must have access to the repository.

**Step 2: Create a Railway project**
Use: `New Project → GitHub Repository → amanansari12/e-library-backend`

**Step 3: Deploy the repository**
Deploy the GitHub repository as the FastAPI service.

**Step 4: Configure Python**
Set: `RAILPACK_PYTHON_VERSION=3.11` for reproducible compatibility.

**Step 5: Configure start command**
Use: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
Do NOT use `python main.py`.

**Step 6: Add PostgreSQL**
In the same Railway project add: `PostgreSQL`

**Step 7: Connect the database**
Set the backend: `DATABASE_URL=${{Postgres.DATABASE_URL}}`

**Step 8: Configure production environment variables**
Document the required variables (see Section 16). Do not expose example production secrets. Do not configure `TEST_DATABASE_URL` for the live application.

**Step 9: Generate JWT secret**
Safe local command:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```
The result belongs only in Railway Variables.

**Step 10: Run migrations**
After connecting PostgreSQL, open the Railway service Console:
```bash
alembic upgrade head
alembic current
alembic check
```
Expected head: `20260814_0004 (head)`
Expected check: `No new upgrade operations detected.`
**IMPORTANT**: Never run `alembic downgrade base` against Railway.

**Step 11: Configure persistent PDF storage**
Create a Railway Volume attached to `e-library-backend`.
Use mount path: `/app/storage/books`
Set: `BOOK_STORAGE_ROOT=/app/storage/books`
This volume is required because runtime PDF files must survive container restarts/redeployments.

**Step 12: Verify volume**
Open Railway Console: `ls -la /app/storage/books` and verify it is writable. Do not keep temporary test files.

**Step 13: Create production admin**
Run: `python scripts/create_admin.py`
Use a production email, a strong unique password, and never commit those credentials. Production admin is created separately from demo users.

**Step 14: Add production demo password**
Set in Railway Variables: `DEMO_USERS_PASSWORD=<secure demo password>`. Do not put this value in GitHub.

**Step 15: Deploy the latest bootstrap script**
Push the repository containing `scripts/bootstrap_production_demo.py` and wait for Railway to deploy the latest commit.

**Step 16: Run production demo bootstrap**
In Railway Console: `python scripts/bootstrap_production_demo.py`
Expected: `Production demo bootstrap complete.`

**Step 17: Verify production statistics**
Open production Swagger, log in as production admin, and call `GET /api/v1/admin/statistics`. The response should show non-zero demo data.

**Step 18: Verify health**
Open `/health`. Expected HTTP 200.

**Step 19: Verify Swagger**
Open `/docs`. Verify all API groups are visible.

**Step 20: Verify real PDF flow**
Use a seeded book. Test: login → borrow → GET /books/{book_id}/file → receive PDF → update reading progress → return → GET /books/{book_id}/file → 403. This verifies PostgreSQL, authentication, borrowing, BookFileService, persistent storage, PDF access control, reading progress, and return behavior.

## 16. Production Environment Variables

| Variable | Required | Production Purpose |
|----------|----------|-------------------|
| `APP_ENV` | Yes | Enables production safeguards |
| `DEBUG` | Yes | Must be false |
| `DATABASE_URL` | Yes | Railway PostgreSQL |
| `JWT_SECRET_KEY` | Yes | JWT signing |
| `AI_API_TOKEN` | Yes if AI features enabled | Userfacet AI |
| `CORS_ORIGINS` | Yes | Allowed frontend |
| `BOOK_STORAGE_ROOT` | Yes | Persistent PDF location |
| `MAX_BOOK_FILE_SIZE_MB` | Configured | Upload protection |
| `DEMO_USERS_PASSWORD` | Only for bootstrap | Demo-user credentials |
| `TEST_DATABASE_URL` | No | Local/CI tests only |

## 17. Production Database Initialization
See Step 10 in Section 15.

## 18. Production Admin Setup
See Step 13 in Section 15.

## 19. Production Demo Data Setup
See Step 16 in Section 15.

## 20. Production PDF Storage
See Step 11 in Section 15.

## 21. Production Verification
See Steps 17-20 in Section 15.

## 22. Common Deployment Problems

**Missing JWT_SECRET_KEY**
Symptom: `pydantic ValidationError jwt_secret_key Field required`
Fix: Add `JWT_SECRET_KEY` to Railway Variables.

**Railway cannot detect/build the Python app**
Use: `RAILPACK_PYTHON_VERSION=3.11` and `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Database has no tables**
Run: `alembic upgrade head`. Do NOT manually create tables.

**PDF uploads disappear**
Cause: Runtime storage is not mounted persistently.
Fix: Attach a Railway Volume at `/app/storage/books` and set `BOOK_STORAGE_ROOT=/app/storage/books`.

**API starts but production database is empty**
Run: `python scripts/bootstrap_production_demo.py` after configuring `APP_ENV=production` and `DEMO_USERS_PASSWORD`. Do NOT use the development seed.

## 23. Security Rules

**Never do these in production:**
* DO NOT run: `alembic downgrade base`
* DO NOT run: `python scripts/seed.py`
* DO NOT commit: `.env`
* DO NOT commit: production credentials
* DO NOT use: `TEST_DATABASE_URL` for the live application
* DO NOT remove: persistent PDF volume
* DO NOT expose: `JWT_SECRET_KEY`, `AI_API_TOKEN`, `DEMO_USERS_PASSWORD`

## 24. Interviewer Quick Start

**For local:**
1. Create PostgreSQL
2. Configure `.env`
3. Install requirements
4. `alembic upgrade head`
5. `python scripts/create_admin.py`
6. `python scripts/seed.py`
7. `uvicorn app.main:app --reload`
8. Open `/docs`

**For the hosted demo:**
1. Open https://e-library-backend-production.up.railway.app
2. Open `/docs`
3. Login
4. Browse seeded books
5. Borrow a book
6. Retrieve the PDF
7. Update reading progress
8. Rate/review
9. Return the book
10. Verify PDF access is revoked
11. Open admin statistics

## 25. Important Files to Read

| File | Why it matters |
|------|----------------|
| `app/main.py` | FastAPI entrypoint |
| `app/core/config.py` | configuration |
| `app/core/security.py` | authentication/security |
| `app/api/` | HTTP endpoints |
| `app/services/book_file.py` | digital PDF workflow |
| `app/storage/` | runtime storage abstraction |
| `app/models/` | database models |
| `scripts/seed.py` | development bootstrap |
| `scripts/create_admin.py` | admin provisioning |
| `scripts/bootstrap_production_demo.py` | production demo bootstrap |
| `scripts/validate_catalog.py` | catalog validation |
| `data/book_catalog.json` | catalog source of truth |
| `docs/API_REFERENCE.md` | complete endpoint reference |
| `docs/BOOK_CATALOG.md` | 20 real books |
| `tests/` | integration tests |

## 26. Current Project Status

```text
Backend: LIVE
Platform: Railway
Database: Railway PostgreSQL
Migration: 20260814_0004
Tests: 107 passed
Catalog assets: 20
Default demo books: 8
Production demo bootstrap: verified
Persistent PDF storage: configured
Swagger: live
Health endpoint: live
```
The backend is currently deployed independently. A separate React/TypeScript frontend can consume the REST API.

## 27. Future Considerations

The following technologies were intentionally omitted to maintain focus on core library modeling and minimize deployment complexity: Docker, Redis, Celery / Kafka, Elasticsearch, WebSockets, Microservices.
