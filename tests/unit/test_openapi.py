"""OpenAPI contracts that Swagger UI relies on for multipart controls."""

from app.main import app


def test_bulk_book_upload_openapi_uses_binary_file_items() -> None:
    schema = app.openapi()
    request_schema = schema["paths"]["/api/v1/books/bulk"]["post"]["requestBody"]["content"][
        "multipart/form-data"
    ]["schema"]
    component_name = request_schema["$ref"].rsplit("/", 1)[-1]
    file_items = schema["components"]["schemas"][component_name]["properties"]["files"]["items"]

    assert file_items == {"type": "string", "format": "binary"}


def test_review_routes_are_documented_in_openapi() -> None:
    schema = app.openapi()

    assert set(schema["paths"]["/api/v1/reviews"]) == {"post"}
    assert set(schema["paths"]["/api/v1/reviews/{review_id}"]) == {"patch", "delete"}
    assert set(schema["paths"]["/api/v1/reviews/books/{book_id}"]) == {"get"}
    assert set(schema["paths"]["/api/v1/reviews/me"]) == {"get"}
    assert "borrowed the book" in schema["paths"]["/api/v1/reviews"]["post"]["description"]


def test_book_file_streaming_openapi_uses_binary_pdf_representation() -> None:
    schema = app.openapi()
    content = schema["paths"]["/api/v1/books/{book_id}/file"]["get"]["responses"]["200"]["content"]

    assert content == {"application/pdf": {"schema": {"type": "string", "format": "binary"}}}


def test_reading_progress_routes_are_documented_in_openapi() -> None:
    schema = app.openapi()

    assert set(schema["paths"]["/api/v1/books/{book_id}/progress"]) == {"get", "put"}
    assert set(schema["paths"]["/api/v1/reading-progress/me"]) == {"get"}
    assert "ACTIVE borrowing" in schema["paths"]["/api/v1/books/{book_id}/progress"]["put"]["description"]
