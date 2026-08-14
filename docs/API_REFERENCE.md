# API Reference

This document provides a comprehensive reference for the E-Library Management System API.

## API Documentation Coverage Matrix

| # | Method | Path | Domain | Auth | Role | Documented | OpenAPI Verified |
| - | ------ | ---- | ------ | ---- | ---- | ---------- | ---------------- |
| 1 | GET | `/health` | Health | Public | Any | Yes | Yes |
| 2 | POST | `/api/v1/auth/register` | Authentication | Public | Any | Yes | Yes |
| 3 | POST | `/api/v1/auth/login` | Authentication | Public | Any | Yes | Yes |
| 4 | POST | `/api/v1/auth/refresh` | Authentication | Public | Any | Yes | Yes |
| 5 | POST | `/api/v1/auth/logout` | Authentication | Public | Any | Yes | Yes |
| 6 | GET | `/api/v1/users/me` | Users | Bearer JWT | USER | Yes | Yes |
| 7 | PATCH | `/api/v1/users/me` | Users | Bearer JWT | USER | Yes | Yes |
| 8 | POST | `/api/v1/books/bulk` | Books | Bearer JWT | ADMIN | Yes | Yes |
| 9 | GET | `/api/v1/books` | Books | Public | Any | Yes | Yes |
| 10 | POST | `/api/v1/books` | Books | Bearer JWT | ADMIN | Yes | Yes |
| 11 | POST | `/api/v1/books/{book_id}/file` | Books | Bearer JWT | ADMIN | Yes | Yes |
| 12 | GET | `/api/v1/books/{book_id}/file` | Books | Bearer JWT | USER | Yes | Yes |
| 13 | GET | `/api/v1/books/{book_id}/progress` | Books | Bearer JWT | USER | Yes | Yes |
| 14 | PUT | `/api/v1/books/{book_id}/progress` | Books | Bearer JWT | USER | Yes | Yes |
| 15 | GET | `/api/v1/books/{book_id}` | Books | Public | Any | Yes | Yes |
| 16 | PATCH | `/api/v1/books/{book_id}` | Books | Bearer JWT | USER | Yes | Yes |
| 17 | POST | `/api/v1/books/{book_id}/archive` | Books | Bearer JWT | USER | Yes | Yes |
| 18 | POST | `/api/v1/books/{book_id}/restore` | Books | Bearer JWT | USER | Yes | Yes |
| 19 | GET | `/api/v1/ai/health` | Ai | Bearer JWT | USER | Yes | Yes |
| 20 | GET | `/api/v1/ai/usage` | Ai | Bearer JWT | USER | Yes | Yes |
| 21 | POST | `/api/v1/books/{book_id}/summary` | Summaries | Bearer JWT | USER | Yes | Yes |
| 22 | GET | `/api/v1/books/{book_id}/summary` | Summaries | Bearer JWT | USER | Yes | Yes |
| 23 | POST | `/api/v1/borrowings` | Borrowings | Bearer JWT | USER | Yes | Yes |
| 24 | POST | `/api/v1/borrowings/{borrowing_id}/return` | Borrowings | Bearer JWT | USER | Yes | Yes |
| 25 | GET | `/api/v1/borrowings/me` | Borrowings | Bearer JWT | USER | Yes | Yes |
| 26 | GET | `/api/v1/borrowings/me/active` | Borrowings | Bearer JWT | USER | Yes | Yes |
| 27 | POST | `/api/v1/reservations` | Reservations | Bearer JWT | USER | Yes | Yes |
| 28 | DELETE | `/api/v1/reservations/{reservation_id}` | Reservations | Bearer JWT | USER | Yes | Yes |
| 29 | GET | `/api/v1/reservations/me` | Reservations | Bearer JWT | USER | Yes | Yes |
| 30 | POST | `/api/v1/favorites` | Favorites | Bearer JWT | USER | Yes | Yes |
| 31 | DELETE | `/api/v1/favorites/{book_id}` | Favorites | Bearer JWT | USER | Yes | Yes |
| 32 | GET | `/api/v1/favorites/me` | Favorites | Bearer JWT | USER | Yes | Yes |
| 33 | GET | `/api/v1/favorites/check/{book_id}` | Favorites | Bearer JWT | USER | Yes | Yes |
| 34 | POST | `/api/v1/ratings` | Ratings | Bearer JWT | USER | Yes | Yes |
| 35 | DELETE | `/api/v1/ratings/{book_id}` | Ratings | Bearer JWT | USER | Yes | Yes |
| 36 | GET | `/api/v1/ratings/books/{book_id}` | Ratings | Public | Any | Yes | Yes |
| 37 | GET | `/api/v1/ratings/me` | Ratings | Bearer JWT | USER | Yes | Yes |
| 38 | GET | `/api/v1/reading-progress/me` | Reading Progress | Bearer JWT | USER | Yes | Yes |
| 39 | POST | `/api/v1/reviews` | Reviews | Bearer JWT | USER | Yes | Yes |
| 40 | GET | `/api/v1/reviews/books/{book_id}` | Reviews | Public | Any | Yes | Yes |
| 41 | GET | `/api/v1/reviews/me` | Reviews | Bearer JWT | USER | Yes | Yes |
| 42 | PATCH | `/api/v1/reviews/{review_id}` | Reviews | Bearer JWT | USER | Yes | Yes |
| 43 | DELETE | `/api/v1/reviews/{review_id}` | Reviews | Bearer JWT | USER | Yes | Yes |
| 44 | POST | `/api/v1/authors/bulk` | Authors | Bearer JWT | USER | Yes | Yes |
| 45 | GET | `/api/v1/authors` | Authors | Public | Any | Yes | Yes |
| 46 | POST | `/api/v1/authors` | Authors | Bearer JWT | USER | Yes | Yes |
| 47 | GET | `/api/v1/authors/{author_id}` | Authors | Public | Any | Yes | Yes |
| 48 | PATCH | `/api/v1/authors/{author_id}` | Authors | Bearer JWT | USER | Yes | Yes |
| 49 | POST | `/api/v1/categories/bulk` | Categories | Bearer JWT | USER | Yes | Yes |
| 50 | GET | `/api/v1/categories` | Categories | Public | Any | Yes | Yes |
| 51 | POST | `/api/v1/categories` | Categories | Bearer JWT | USER | Yes | Yes |
| 52 | GET | `/api/v1/categories/{category_id}` | Categories | Public | Any | Yes | Yes |
| 53 | PATCH | `/api/v1/categories/{category_id}` | Categories | Bearer JWT | USER | Yes | Yes |
| 54 | GET | `/api/v1/admin/statistics` | Admin Statistics | Bearer JWT | ADMIN | Yes | Yes |
| 55 | GET | `/api/v1/admin/statistics/popular-books` | Admin Statistics | Bearer JWT | ADMIN | Yes | Yes |
| 56 | GET | `/api/v1/admin/statistics/popular-categories` | Admin Statistics | Bearer JWT | ADMIN | Yes | Yes |
| 57 | GET | `/api/v1/admin/statistics/highest-rated` | Admin Statistics | Bearer JWT | ADMIN | Yes | Yes |

## Common API Behavior

### Error Envelope
All errors are returned with a standard JSON envelope:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
  }
}
```

### Request ID
Every response includes an `X-Request-ID` header for tracing. Clients can also send an `X-Request-ID` in the request, and the server will use it if provided.

### CORS
Configured via `CORS_ORIGINS`. Preflight `OPTIONS` requests are supported for `GET`, `POST`, `PATCH`, `DELETE`.

### Rate Limiting
Abuse-sensitive endpoints are protected by slowapi based on client IP. Exceeded limits return `429 Too Many Requests`.

| Endpoint | Limit | Window | Error |
| -------- | ----- | ------ | ----- |
| `POST /api/v1/auth/register` | 5 | 1 minute | 429 Too Many Requests |
| `POST /api/v1/auth/login` | 5 | 1 minute | 429 Too Many Requests |
| `POST /api/v1/reviews` | 10 | 1 hour | 429 Too Many Requests |
| `POST /api/v1/books` | 10 | 1 hour | 429 Too Many Requests |
| `POST /api/v1/books/bulk` | 5 | 1 hour | 429 Too Many Requests |
| `POST /api/v1/books/{book_id}/file` | 10 | 1 hour | 429 Too Many Requests |
| `POST /api/v1/books/{book_id}/summary` | 10 | 1 hour | 429 Too Many Requests |

## Endpoints Detail

### Health Check
**`GET /health`**

**Authentication**: Public

**Headers**
- `X-Request-ID`: Optional client request ID

**Responses**
- **200**: Successful Response

---
### Register
**`POST /api/v1/auth/register`**

**Authentication**: Public
**Rate Limit**: 5/minute

**Headers**
- `X-Request-ID`: Optional client request ID

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `email` | string | Yes |  |
| `username` | string | Yes |  |
| `password` | string | Yes |  |
| `full_name` | string | Yes |  |

**Responses**
- **201**: Successful Response
- **422**: Validation Error

---
### Login
**`POST /api/v1/auth/login`**

**Authentication**: Public
**Rate Limit**: 5/minute

**Headers**
- `X-Request-ID`: Optional client request ID

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `email` | string | Yes |  |
| `password` | string | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Refresh
**`POST /api/v1/auth/refresh`**

**Authentication**: Public

**Headers**
- `X-Request-ID`: Optional client request ID

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `refresh_token` | string | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Logout
**`POST /api/v1/auth/logout`**

**Authentication**: Public

**Headers**
- `X-Request-ID`: Optional client request ID

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `refresh_token` | string | Yes |  |

**Responses**
- **204**: Successful Response
- **422**: Validation Error

---
### Get Me
**`GET /api/v1/users/me`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---
### Update Me
**`PATCH /api/v1/users/me`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `email` | object | No |  |
| `username` | object | No |  |
| `full_name` | object | No |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Create Books Bulk
**`POST /api/v1/books/bulk`**

**Authentication**: Bearer JWT
**Role**: ADMIN
**Rate Limit**: 5/hour

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Request Body**
Content-Type: `multipart/form-data`
Consult OpenAPI schema for exact field mappings. Commonly involves file uploads and metadata payloads.

**Responses**
- **201**: Successful Response
- **422**: Validation Error

---
### List Books
**`GET /api/v1/books`**

**Authentication**: Public

**Headers**
- `X-Request-ID`: Optional client request ID

**Query Parameters**
| Name | Type | Required | Default | Description |
| ---- | ---- | -------- | ------- | ----------- |
| `q` | string | No |  |  |
| `author_id` | string | No |  |  |
| `category_id` | string | No |  |  |
| `available` | string | No |  |  |
| `year_from` | string | No |  |  |
| `year_to` | string | No |  |  |
| `sort_by` | string | No | title |  |
| `sort_order` | string | No | asc |  |
| `page` | integer | No | 1 |  |
| `page_size` | integer | No | 20 |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Create Book
**`POST /api/v1/books`**

**Authentication**: Bearer JWT
**Role**: ADMIN
**Rate Limit**: 10/hour

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Request Body**
Content-Type: `multipart/form-data`
Consult OpenAPI schema for exact field mappings. Commonly involves file uploads and metadata payloads.

**Responses**
- **201**: Successful Response
- **422**: Validation Error

---
### Replace Book File
**`POST /api/v1/books/{book_id}/file`**

**Authentication**: Bearer JWT
**Role**: ADMIN
**Rate Limit**: 10/hour

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Request Body**
Content-Type: `multipart/form-data`
Consult OpenAPI schema for exact field mappings. Commonly involves file uploads and metadata payloads.

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Get Book File
**`GET /api/v1/books/{book_id}/file`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Responses**
- **200**: The active PDF binary for an authenticated active borrower.
- **422**: Validation Error

---
### Get Reading Progress
**`GET /api/v1/books/{book_id}/progress`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Set Reading Progress
**`PUT /api/v1/books/{book_id}/progress`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `current_page` | integer | Yes |  |
| `total_pages` | integer | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Get Book
**`GET /api/v1/books/{book_id}`**

**Authentication**: Public

**Headers**
- `X-Request-ID`: Optional client request ID

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Update Book
**`PATCH /api/v1/books/{book_id}`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `title` | object | No |  |
| `isbn` | object | No |  |
| `description` | object | No |  |
| `publication_year` | object | No |  |
| `max_concurrent_borrows` | object | No |  |
| `author_ids` | object | No |  |
| `category_ids` | object | No |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Archive Book
**`POST /api/v1/books/{book_id}/archive`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Restore Book
**`POST /api/v1/books/{book_id}/restore`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Ai Health
**`GET /api/v1/ai/health`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---
### Ai Usage
**`GET /api/v1/ai/usage`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---
### Generate Summary
**`POST /api/v1/books/{book_id}/summary`**

**Authentication**: Bearer JWT
**Role**: USER
**Rate Limit**: 10/hour

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Query Parameters**
| Name | Type | Required | Default | Description |
| ---- | ---- | -------- | ------- | ----------- |
| `force_regenerate` | boolean | No | False |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Get Summary
**`GET /api/v1/books/{book_id}/summary`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Create Borrowing
**`POST /api/v1/borrowings`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |
| `due_date` | string | Yes |  |

**Responses**
- **201**: Successful Response
- **422**: Validation Error

---
### Return Borrowing
**`POST /api/v1/borrowings/{borrowing_id}/return`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `borrowing_id` | integer | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### List My Borrowings
**`GET /api/v1/borrowings/me`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---
### List My Active Borrowings
**`GET /api/v1/borrowings/me/active`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---
### Create Reservation
**`POST /api/v1/reservations`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Responses**
- **201**: Successful Response
- **422**: Validation Error

---
### Cancel Reservation
**`DELETE /api/v1/reservations/{reservation_id}`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `reservation_id` | integer | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### List My Reservations
**`GET /api/v1/reservations/me`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---
### Create Favorite
**`POST /api/v1/favorites`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Responses**
- **201**: Successful Response
- **422**: Validation Error

---
### Remove Favorite
**`DELETE /api/v1/favorites/{book_id}`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Responses**
- **204**: Successful Response
- **422**: Validation Error

---
### List My Favorites
**`GET /api/v1/favorites/me`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---
### Check Favorite Status
**`GET /api/v1/favorites/check/{book_id}`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Create Or Update Rating
**`POST /api/v1/ratings`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |
| `score` | integer | Yes |  |

**Responses**
- **201**: Successful Response
- **422**: Validation Error

---
### Remove Rating
**`DELETE /api/v1/ratings/{book_id}`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Responses**
- **204**: Successful Response
- **422**: Validation Error

---
### List Book Ratings
**`GET /api/v1/ratings/books/{book_id}`**

**Authentication**: Public

**Headers**
- `X-Request-ID`: Optional client request ID

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### List My Ratings
**`GET /api/v1/ratings/me`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---
### List My Reading Progress
**`GET /api/v1/reading-progress/me`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---
### Create Review
**`POST /api/v1/reviews`**

**Authentication**: Bearer JWT
**Role**: USER
**Rate Limit**: 10/hour

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `review_text` | string | Yes |  |
| `book_id` | integer | Yes |  |

**Responses**
- **201**: Successful Response
- **422**: Validation Error

---
### List Book Reviews
**`GET /api/v1/reviews/books/{book_id}`**

**Authentication**: Public

**Headers**
- `X-Request-ID`: Optional client request ID

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `book_id` | integer | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### List My Reviews
**`GET /api/v1/reviews/me`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---
### Update Review
**`PATCH /api/v1/reviews/{review_id}`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `review_id` | integer | Yes |  |

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `review_text` | string | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Delete Review
**`DELETE /api/v1/reviews/{review_id}`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `review_id` | integer | Yes |  |

**Responses**
- **204**: Successful Response
- **422**: Validation Error

---
### Create Authors Bulk
**`POST /api/v1/authors/bulk`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `authors` | array | Yes |  |

**Responses**
- **201**: Successful Response
- **422**: Validation Error

---
### List Authors
**`GET /api/v1/authors`**

**Authentication**: Public

**Headers**
- `X-Request-ID`: Optional client request ID

**Responses**
- **200**: Successful Response

---
### Create Author
**`POST /api/v1/authors`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `name` | string | Yes |  |
| `biography` | object | No |  |

**Responses**
- **201**: Successful Response
- **422**: Validation Error

---
### Get Author
**`GET /api/v1/authors/{author_id}`**

**Authentication**: Public

**Headers**
- `X-Request-ID`: Optional client request ID

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `author_id` | integer | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Update Author
**`PATCH /api/v1/authors/{author_id}`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `author_id` | integer | Yes |  |

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `name` | object | No |  |
| `biography` | object | No |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Create Categories Bulk
**`POST /api/v1/categories/bulk`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `categories` | array | Yes |  |

**Responses**
- **201**: Successful Response
- **422**: Validation Error

---
### List Categories
**`GET /api/v1/categories`**

**Authentication**: Public

**Headers**
- `X-Request-ID`: Optional client request ID

**Responses**
- **200**: Successful Response

---
### Create Category
**`POST /api/v1/categories`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `name` | string | Yes |  |
| `description` | object | No |  |

**Responses**
- **201**: Successful Response
- **422**: Validation Error

---
### Get Category
**`GET /api/v1/categories/{category_id}`**

**Authentication**: Public

**Headers**
- `X-Request-ID`: Optional client request ID

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `category_id` | integer | Yes |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Update Category
**`PATCH /api/v1/categories/{category_id}`**

**Authentication**: Bearer JWT
**Role**: USER

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Path Parameters**
| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| `category_id` | integer | Yes |  |

**Request Body**
| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| `name` | object | No |  |
| `description` | object | No |  |

**Responses**
- **200**: Successful Response
- **422**: Validation Error

---
### Get Statistics
**`GET /api/v1/admin/statistics`**

**Authentication**: Bearer JWT
**Role**: ADMIN

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---
### Get Popular Books
**`GET /api/v1/admin/statistics/popular-books`**

**Authentication**: Bearer JWT
**Role**: ADMIN

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---
### Get Popular Categories
**`GET /api/v1/admin/statistics/popular-categories`**

**Authentication**: Bearer JWT
**Role**: ADMIN

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---
### Get Highest Rated
**`GET /api/v1/admin/statistics/highest-rated`**

**Authentication**: Bearer JWT
**Role**: ADMIN

**Headers**
- `X-Request-ID`: Optional client request ID
- `Authorization`: Bearer <token>

**Responses**
- **200**: Successful Response

---

## Client Examples

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email": "user@example.com", "username": "user1", "password": "secret123", "full_name": "Test User"}'

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=user1&password=secret123'

# 3. Get current user
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN"

# 4. List books
curl -X GET 'http://localhost:8000/api/v1/books?page=1&page_size=20'

# 5. Search books
curl -X GET 'http://localhost:8000/api/v1/books?q=python&available=true'

# 6. Create book (ADMIN)
curl -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F 'book_data={"title":"Python 101","isbn":"123456","category_id":1,"author_ids":[1]}' \
  -F 'file=@/path/to/book.pdf'

# 7. Replace PDF (ADMIN)
curl -X POST http://localhost:8000/api/v1/books/1/file \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F 'file=@/path/to/new_version.pdf'

# 8. Retrieve PDF
curl -X GET http://localhost:8000/api/v1/books/1/file \
  -H "Authorization: Bearer $TOKEN" -o downloaded_book.pdf

# 9. Borrow
curl -X POST http://localhost:8000/api/v1/borrowings \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"book_id": 1, "due_date": "2026-09-01T00:00:00Z"}'

# 10. Update progress
curl -X PUT http://localhost:8000/api/v1/books/1/progress \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"current_page": 42}'

# 11. Favorite
curl -X POST http://localhost:8000/api/v1/favorites \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"book_id": 1}'

# 12. Rating
curl -X POST http://localhost:8000/api/v1/ratings \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"book_id": 1, "score": 5}'

# 13. Review
curl -X POST http://localhost:8000/api/v1/reviews \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"book_id": 1, "text": "Great book!"}'

# 14. Reservation
curl -X POST http://localhost:8000/api/v1/reservations \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"book_id": 1}'

# 15. Return
curl -X POST http://localhost:8000/api/v1/borrowings/1/return \
  -H "Authorization: Bearer $TOKEN"

# 16. Admin statistics
curl -X GET http://localhost:8000/api/v1/admin/statistics \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 17. AI summary
curl -X POST http://localhost:8000/api/v1/books/1/summary \
  -H "Authorization: Bearer $TOKEN"

```
