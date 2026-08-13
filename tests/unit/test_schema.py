from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.db.base import Base
from app.models.reservation import Reservation


def _unique_column_sets(table_name: str) -> set[frozenset[str]]:
    table = Base.metadata.tables[table_name]
    return {
        frozenset(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _check_expressions(table_name: str) -> set[str]:
    table = Base.metadata.tables[table_name]
    return {
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }


def test_metadata_contains_the_digital_file_table() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "books",
        "book_files",
        "book_reviews",
        "reading_progress",
        "authors",
        "categories",
        "book_authors",
        "book_categories",
        "borrowings",
        "reservations",
        "favorites",
        "ratings",
        "book_summaries",
        "refresh_tokens",
    }


def test_required_unique_constraints_are_defined() -> None:
    assert frozenset({"email"}) in _unique_column_sets("users")
    assert frozenset({"username"}) in _unique_column_sets("users")
    assert frozenset({"isbn"}) in _unique_column_sets("books")
    assert frozenset({"user_id", "book_id"}) in _unique_column_sets("favorites")
    assert frozenset({"user_id", "book_id"}) in _unique_column_sets("ratings")
    assert frozenset({"user_id", "book_id"}) in _unique_column_sets("book_reviews")
    assert frozenset({"user_id", "book_id"}) in _unique_column_sets("reading_progress")
    assert frozenset({"book_id", "content_version"}) in _unique_column_sets("book_summaries")


def test_required_check_constraints_and_absent_columns_are_defined() -> None:
    assert "score BETWEEN 1 AND 5" in _check_expressions("ratings")
    assert "status IN ('ACTIVE', 'RETURNED')" in _check_expressions("borrowings")
    assert "is_active" not in Base.metadata.tables["users"].columns
    assert "summary_type" not in Base.metadata.tables["book_summaries"].columns
    assert "content" not in Base.metadata.tables["books"].columns
    assert "file_size > 0" in _check_expressions("book_files")
    assert "current_page >= 1" in _check_expressions("reading_progress")
    assert "total_pages > 0" in _check_expressions("reading_progress")
    assert "current_page <= total_pages" in _check_expressions("reading_progress")


def test_review_foreign_keys_and_indexes_are_defined() -> None:
    table = Base.metadata.tables["book_reviews"]
    foreign_key_targets = {
        foreign_key.target_fullname
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        for foreign_key in constraint.elements
    }

    assert foreign_key_targets == {"users.id", "books.id"}
    assert {index.name for index in table.indexes} == {
        "ix_book_reviews_user_id",
        "ix_book_reviews_book_id",
    }


def test_reading_progress_foreign_keys_and_indexes_are_defined() -> None:
    table = Base.metadata.tables["reading_progress"]
    foreign_key_targets = {
        foreign_key.target_fullname
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        for foreign_key in constraint.elements
    }

    assert foreign_key_targets == {"users.id", "books.id"}
    assert {index.name for index in table.indexes} == {
        "ix_reading_progress_user_id",
        "ix_reading_progress_book_id",
    }


def test_active_reservation_index_is_postgresql_partial_and_unique() -> None:
    reservation_index = next(
        index for index in Reservation.__table__.indexes if index.name == "uq_active_reservation"
    )

    assert reservation_index.unique is True
    assert tuple(reservation_index.columns.keys()) == ("user_id", "book_id")
    assert str(reservation_index.dialect_options["postgresql"]["where"]) == "status IN ('PENDING', 'READY')"
