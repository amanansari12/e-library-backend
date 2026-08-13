from concurrent.futures import ThreadPoolExecutor
from functools import partial
from threading import Barrier

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.api.v1.ai as ai_api
import app.api.v1.summaries as summaries_api
from app.clients.ai_client import AIClient, AIClientError
from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.rate_limit import limiter
from app.models.book import Book
from app.models.book_summary import BookSummary
from app.schemas.book import BookUpdate
from app.services.catalog import CatalogService
from app.services.summary import SummaryService
from tests.integration.test_borrowings import _create_book, _create_user, _headers


class _Response:
    def __init__(self, status_code: int, data: object) -> None:
        self.status_code = status_code
        self._data = data

    def json(self):
        if isinstance(self._data, Exception):
            raise self._data
        return self._data


class _HTTPClient:
    def __init__(self, response: _Response | Exception, **kwargs) -> None:
        self.response = response
        self.kwargs = kwargs
        self.calls: list[tuple[str, str, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def request(self, method: str, path: str, **kwargs):
        self.calls.append((method, path, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class _FakeAIClient:
    def __init__(self, summary_text: str = "A concise generated summary.") -> None:
        self.summary_text = summary_text
        self.generate_calls = 0
        self.fail_with: AIClientError | None = None
        self.prompts: list[str] = []

    def generate_summary(self, prompt: str) -> tuple[str, int | None, str]:
        self.generate_calls += 1
        self.prompts.append(prompt)
        assert "<book-data>" in prompt
        if self.fail_with is not None:
            raise self.fail_with
        return self.summary_text, 123, "gpt-4o-mini"

    def health(self) -> dict:
        return {"status": "ok"}

    def usage(self) -> dict:
        return {"remaining": 99}


def _settings() -> Settings:
    return Settings(jwt_secret_key="test-secret", ai_api_token="test-token")


def _ai_client_for(response: _Response | Exception) -> tuple[AIClient, list[_HTTPClient]]:
    clients: list[_HTTPClient] = []

    def factory(**kwargs):
        client = _HTTPClient(response, **kwargs)
        clients.append(client)
        return client

    return AIClient(_settings(), factory), clients


def _book_with_source(session_factory) -> Book:
    book = _create_book(session_factory)
    with session_factory() as session:
        stored_book = session.get(Book, book.id)
        assert stored_book is not None
        stored_book.description = "A test description suitable for an AI summary."
        stored_file = next(book_file for book_file in stored_book.files if book_file.is_active)
        stored_file.extracted_text = "Reference text extracted from this book file."
        session.commit()
        session.refresh(stored_book)
        session.expunge(stored_book)
        return stored_book


def test_ai_client_supports_generation_health_usage_and_bounded_request() -> None:
    client, clients = _ai_client_for(
        _Response(
            200,
            {
                "model": "gpt-4o-mini",
                "choices": [{"message": {"content": "Summary text"}}],
                "usage": {"total_tokens": 42},
            },
        )
    )

    summary, token_count, model = client.generate_summary("controlled prompt")
    health_client, _ = _ai_client_for(_Response(200, {"status": "ok"}))
    usage_client, _ = _ai_client_for(_Response(200, {"remaining": 99}))

    assert (summary, token_count, model) == ("Summary text", 42, "gpt-4o-mini")
    assert clients[0].calls[0][0:2] == ("POST", "/v1/chat/completions")
    assert clients[0].calls[0][2]["json"]["max_tokens"] == 1000
    assert clients[0].kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert health_client.health() == {"status": "ok"}
    assert usage_client.usage() == {"remaining": 99}


@pytest.mark.parametrize(
    ("response", "expected_code"),
    [
        (_Response(400, {}), "AI_PROVIDER_REJECTED"),
        (_Response(401, {}), "AI_PROVIDER_REJECTED"),
        (_Response(403, {}), "AI_PROVIDER_REJECTED"),
        (_Response(404, {}), "AI_PROVIDER_REJECTED"),
        (_Response(429, {}), "AI_QUOTA_EXHAUSTED"),
        (_Response(500, {}), "AI_PROVIDER_UNAVAILABLE"),
        (_Response(200, {}), "AI_PROVIDER_INVALID_RESPONSE"),
        (_Response(200, ValueError("invalid json")), "AI_PROVIDER_INVALID_RESPONSE"),
        (httpx.TimeoutException("timeout"), "AI_PROVIDER_TIMEOUT"),
    ],
)
def test_ai_client_maps_upstream_failures_safely(response, expected_code: str) -> None:
    client, _ = _ai_client_for(response)

    with pytest.raises(AIClientError) as exc_info:
        client.generate_summary("controlled prompt")

    assert exc_info.value.code == expected_code
    assert "test-token" not in exc_info.value.message


def test_summary_cache_hit_force_regeneration_and_failure_preservation(session_factory) -> None:
    book = _book_with_source(session_factory)
    fake_ai = _FakeAIClient("First valid summary")
    service = SummaryService(ai_client=fake_ai, settings=_settings())
    with session_factory() as session:
        first = service.generate(session, book.id, force_regenerate=False)
        cached = service.generate(session, book.id, force_regenerate=False)
        retrieved = service.get_cached(session, book.id)
        fake_ai.summary_text = "Regenerated valid summary"
        regenerated = service.generate(session, book.id, force_regenerate=True)
        fake_ai.fail_with = AIClientError(503, "AI_PROVIDER_UNAVAILABLE", "safe failure")
        with pytest.raises(AppError) as exc_info:
            service.generate(session, book.id, force_regenerate=True)
        fake_ai.fail_with = None
        preserved = service.generate(session, book.id, force_regenerate=False)

    assert first.id == cached.id == retrieved.id == regenerated.id == preserved.id
    assert first.summary_text == cached.summary_text == "First valid summary"
    assert regenerated.summary_text == preserved.summary_text == "Regenerated valid summary"
    assert fake_ai.generate_calls == 3
    assert "Reference text extracted from this book file." in fake_ai.prompts[0]
    assert exc_info.value.code == "AI_PROVIDER_UNAVAILABLE"


def test_book_content_version_naturally_invalidates_summary_cache(session_factory) -> None:
    book = _book_with_source(session_factory)
    fake_ai = _FakeAIClient("Version one")
    service = SummaryService(ai_client=fake_ai, settings=_settings())
    with session_factory() as session:
        first = service.generate(session, book.id, force_regenerate=False)
        CatalogService().update_book(session, book.id, BookUpdate(description="Changed source data."))
        fake_ai.summary_text = "Version two"
        second = service.generate(session, book.id, force_regenerate=False)

    assert first.content_version == 1
    assert second.content_version == 2
    assert first.id != second.id
    assert fake_ai.generate_calls == 2


def test_summary_rejects_insufficient_source_data(session_factory) -> None:
    book = _create_book(session_factory)
    service = SummaryService(ai_client=_FakeAIClient(), settings=_settings())
    with session_factory() as session:
        with pytest.raises(AppError) as exc_info:
            service.generate(session, book.id, force_regenerate=False)

    assert exc_info.value.code == "INSUFFICIENT_SUMMARY_SOURCE"


def test_concurrent_summary_generation_reuses_one_persisted_cache_row(session_factory) -> None:
    book = _book_with_source(session_factory)
    fake_ai = _FakeAIClient()
    start = Barrier(2)

    def generate() -> str:
        with session_factory() as session:
            start.wait()
            return SummaryService(ai_client=fake_ai, settings=_settings()).generate(
                session, book.id, force_regenerate=False
            ).summary_text

    with ThreadPoolExecutor(max_workers=2) as executor:
        summaries = list(executor.map(lambda _: generate(), range(2)))
    with session_factory() as session:
        count = session.scalar(
            select(func.count(BookSummary.id)).where(
                BookSummary.book_id == book.id,
                BookSummary.content_version == 1,
            )
        )

    assert summaries == ["A concise generated summary.", "A concise generated summary."]
    assert count == 1


def test_summary_and_ai_routes_use_mocked_client_and_rate_limit(client: TestClient, session_factory, monkeypatch) -> None:
    limiter._storage.reset()
    user = _create_user(session_factory)
    book = _book_with_source(session_factory)
    fake_ai = _FakeAIClient()
    service = SummaryService(ai_client=fake_ai, settings=_settings())
    monkeypatch.setattr(summaries_api, "summary_service", service)
    monkeypatch.setattr(ai_api, "summary_service", service)

    unauthenticated = client.post(f"/api/v1/books/{book.id}/summary")
    generated = client.post(f"/api/v1/books/{book.id}/summary", headers=_headers(user))
    retrieved = client.get(f"/api/v1/books/{book.id}/summary", headers=_headers(user))
    health = client.get("/api/v1/ai/health", headers=_headers(user))
    usage = client.get("/api/v1/ai/usage", headers=_headers(user))
    repeated = [client.post(f"/api/v1/books/{book.id}/summary", headers=_headers(user)) for _ in range(10)]

    assert unauthenticated.status_code == 401
    assert generated.status_code == 200
    assert generated.json()["summary_text"] == "A concise generated summary."
    assert retrieved.status_code == 200
    assert retrieved.json()["id"] == generated.json()["id"]
    assert fake_ai.generate_calls == 1
    assert health.json() == {"data": {"status": "ok"}}
    assert usage.json() == {"data": {"remaining": 99}}
    assert all("test-token" not in response.text for response in [generated, health, usage])
    assert any(response.status_code == 429 for response in repeated)
    limited = next(response for response in repeated if response.status_code == 429)
    assert limited.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
