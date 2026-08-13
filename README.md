# e-library-backend
A modular FastAPI backend for an E-Library Management System with book management, borrowing, reservations, favorites, ratings, admin statistics, and AI-powered book summaries.

## Additional implemented feature

Bulk Catalog Creation is an operational, admin-only enhancement added separately from the official Phase 1–13 roadmap. It provides atomic catalog batches through:

```text
POST /api/v1/authors/bulk
POST /api/v1/categories/bulk
POST /api/v1/books/bulk
```

The configurable default limit is 50 items per batch. Bulk books retain the existing many-to-many author/category model, while the single-create endpoints and explicit AI-summary workflow remain unchanged.
