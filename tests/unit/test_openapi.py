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
