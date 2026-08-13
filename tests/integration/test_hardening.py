"""Phase 12 cross-cutting security, observability, and HTTP-contract tests."""

from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from tests.integration.test_borrowings import _borrow, _create_book, _create_user, _headers


def _registration_payload() -> dict[str, str]:
    identifier = uuid4().hex
    return {
        "email": f"reader-{identifier}@example.com",
        "username": f"reader{identifier[:16]}",
        "password": "secure-password-123",
        "full_name": "Library Reader",
    }


def test_request_ids_are_generated_accepted_and_returned_for_errors(client) -> None:
    generated = client.get("/health")
    accepted = client.get("/health", headers={"X-Request-ID": "client-correlation_42"})
    invalid = client.get("/health", headers={"X-Request-ID": "invalid id with spaces"})
    validation_error = client.get("/api/v1/books", params={"page": 0})
    missing = client.get("/not-a-route")

    assert len(generated.headers["X-Request-ID"]) == 32
    assert accepted.headers["X-Request-ID"] == "client-correlation_42"
    assert invalid.headers["X-Request-ID"] != "invalid id with spaces"
    assert validation_error.status_code == 422
    assert validation_error.json()["error"]["code"] == "VALIDATION_ERROR"
    assert validation_error.headers["X-Request-ID"]
    assert missing.status_code == 404
    assert missing.json() == {"error": {"code": "NOT_FOUND", "message": "Resource not found"}}
    assert missing.headers["X-Request-ID"]


def test_unexpected_errors_are_safe_and_correlated() -> None:
    application = create_app()

    @application.get("/test-unexpected-error")
    def test_unexpected_error() -> None:
        raise RuntimeError("database password must never be returned")

    with TestClient(application, raise_server_exceptions=False) as test_client:
        response = test_client.get("/test-unexpected-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected server error occurred",
        }
    }
    assert response.headers["X-Request-ID"]
    assert "password" not in response.text


def test_cors_allows_only_configured_origin_methods_and_headers(client) -> None:
    allowed = client.options(
        "/api/v1/books",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type,X-Request-ID",
        },
    )
    denied = client.options(
        "/api/v1/books",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert "PATCH" in allowed.headers["access-control-allow-methods"]
    assert "Authorization" in allowed.headers["access-control-allow-headers"]
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


def test_registration_and_login_rate_limits_return_consistent_errors(client) -> None:
    registration_responses = [client.post("/api/v1/auth/register", json=_registration_payload()) for _ in range(6)]
    login_responses = [
        client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "wrong-password"},
        )
        for _ in range(6)
    ]

    for responses in (registration_responses, login_responses):
        assert all(response.status_code != 429 for response in responses[:5])
        limited = responses[5]
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert limited.headers["X-Request-ID"]


def test_review_creation_is_rate_limited_without_changing_ownership_or_eligibility(client, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    assert _borrow(client, user, book.id).status_code == 201

    responses = [
        client.post(
            "/api/v1/reviews",
            headers=_headers(user),
            json={"book_id": book.id, "review_text": f"Review attempt {attempt}."},
        )
        for attempt in range(11)
    ]

    assert responses[0].status_code == 201
    assert all(response.status_code == 409 for response in responses[1:10])
    assert responses[10].status_code == 429
    assert responses[10].json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
