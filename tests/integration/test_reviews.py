"""Integration coverage for optional, borrowing-history-gated book reviews."""

from sqlalchemy import select

from app.models.book import Book
from app.models.book_review import BookReview
from app.models.reservation import Reservation
from tests.integration.test_borrowings import _borrow, _create_book, _create_user, _headers


def _review(client, user, book_id: int, review_text: str = "A thoughtful and useful book."):
    return client.post(
        "/api/v1/reviews",
        headers=_headers(user),
        json={"book_id": book_id, "review_text": review_text},
    )


def _borrow_then_return(client, user, book_id: int) -> None:
    borrowing = _borrow(client, user, book_id)
    assert borrowing.status_code == 201
    assert client.post(
        f"/api/v1/borrowings/{borrowing.json()['id']}/return", headers=_headers(user)
    ).status_code == 200


def test_review_creation_requires_authentication_book_and_borrowing_history(client, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)

    unauthenticated = client.post(
        "/api/v1/reviews", json={"book_id": book.id, "review_text": "Good book."}
    )
    nonexistent = _review(client, user, 99999)
    never_borrowed = _review(client, user, book.id)
    assert _borrow(client, user, book.id).status_code == 201
    valid = _review(client, user, book.id)

    assert unauthenticated.status_code == 401
    assert nonexistent.status_code == 404
    assert nonexistent.json()["error"]["code"] == "BOOK_NOT_FOUND"
    assert never_borrowed.status_code == 403
    assert never_borrowed.json()["error"]["code"] == "REVIEW_NOT_ALLOWED"
    assert valid.status_code == 201
    assert valid.json()["review_text"] == "A thoughtful and useful book."
    assert valid.json()["user"] == {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
    }


def test_returned_borrowing_qualifies_but_reservation_alone_does_not(client, session_factory) -> None:
    returned_user = _create_user(session_factory)
    reservation_only_user = _create_user(session_factory)
    book = _create_book(session_factory)
    _borrow_then_return(client, returned_user, book.id)
    with session_factory() as session:
        session.add(Reservation(user_id=reservation_only_user.id, book_id=book.id, position=1))
        session.commit()

    after_return = _review(client, returned_user, book.id)
    reservation_only = _review(client, reservation_only_user, book.id)

    assert after_return.status_code == 201
    assert reservation_only.status_code == 403
    assert reservation_only.json()["error"]["code"] == "REVIEW_NOT_ALLOWED"


def test_review_text_and_duplicate_validation(client, session_factory) -> None:
    user = _create_user(session_factory)
    book = _create_book(session_factory)
    assert _borrow(client, user, book.id).status_code == 201

    blank = _review(client, user, book.id, " \t\n ")
    too_long = _review(client, user, book.id, "a" * 2001)
    first = _review(client, user, book.id)
    duplicate = _review(client, user, book.id, "A second review is not allowed.")
    with session_factory() as session:
        stored = list(
            session.scalars(
                select(BookReview).where(BookReview.user_id == user.id, BookReview.book_id == book.id)
            )
        )

    assert blank.status_code == 422
    assert too_long.status_code == 422
    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "REVIEW_ALREADY_EXISTS"
    assert len(stored) == 1


def test_review_update_and_delete_are_owner_only(client, session_factory) -> None:
    owner = _create_user(session_factory)
    other_user = _create_user(session_factory)
    book = _create_book(session_factory)
    assert _borrow(client, owner, book.id).status_code == 201
    review_id = _review(client, owner, book.id).json()["id"]

    forbidden_update = client.patch(
        f"/api/v1/reviews/{review_id}", headers=_headers(other_user), json={"review_text": "Not mine."}
    )
    invalid_update = client.patch(
        f"/api/v1/reviews/{review_id}", headers=_headers(owner), json={"review_text": "  "}
    )
    updated = client.patch(
        f"/api/v1/reviews/{review_id}", headers=_headers(owner), json={"review_text": "Updated review."}
    )
    forbidden_delete = client.delete(f"/api/v1/reviews/{review_id}", headers=_headers(other_user))
    deleted = client.delete(f"/api/v1/reviews/{review_id}", headers=_headers(owner))
    missing_delete = client.delete(f"/api/v1/reviews/{review_id}", headers=_headers(owner))

    assert forbidden_update.status_code == 403
    assert forbidden_update.json()["error"]["code"] == "FORBIDDEN"
    assert invalid_update.status_code == 422
    assert updated.status_code == 200
    assert updated.json()["review_text"] == "Updated review."
    assert updated.json()["user_id"] == owner.id
    assert forbidden_delete.status_code == 403
    assert deleted.status_code == 204
    assert missing_delete.status_code == 404
    assert missing_delete.json()["error"]["code"] == "REVIEW_NOT_FOUND"


def test_review_lists_are_book_scoped_safe_and_current_user_scoped(client, session_factory) -> None:
    first_user = _create_user(session_factory)
    second_user = _create_user(session_factory)
    first_book = _create_book(session_factory)
    second_book = _create_book(session_factory)
    assert client.get(f"/api/v1/reviews/books/{first_book.id}").json() == []
    assert client.get("/api/v1/reviews/books/99999").status_code == 404
    assert _borrow(client, first_user, first_book.id).status_code == 201
    assert _borrow(client, second_user, second_book.id).status_code == 201
    assert _review(client, first_user, first_book.id).status_code == 201
    assert _review(client, second_user, second_book.id).status_code == 201

    book_reviews = client.get(f"/api/v1/reviews/books/{first_book.id}")
    first_users_reviews = client.get("/api/v1/reviews/me", headers=_headers(first_user))
    second_users_reviews = client.get("/api/v1/reviews/me", headers=_headers(second_user))

    assert book_reviews.status_code == 200
    assert [review["book_id"] for review in book_reviews.json()] == [first_book.id]
    assert "email" not in book_reviews.json()[0]["user"]
    assert "hashed_password" not in book_reviews.json()[0]
    assert [review["book_id"] for review in first_users_reviews.json()] == [first_book.id]
    assert [review["book_id"] for review in second_users_reviews.json()] == [second_book.id]


def test_reviews_are_independent_from_ratings_and_remain_after_archive(client, session_factory) -> None:
    user = _create_user(session_factory)
    rating_only_book = _create_book(session_factory)
    review_only_book = _create_book(session_factory)
    both_book = _create_book(session_factory)
    assert client.post(
        "/api/v1/ratings", headers=_headers(user), json={"book_id": rating_only_book.id, "score": 5}
    ).status_code == 201
    assert _borrow(client, user, review_only_book.id).status_code == 201
    assert _review(client, user, review_only_book.id).status_code == 201
    assert _borrow(client, user, both_book.id).status_code == 201
    review_id = _review(client, user, both_book.id).json()["id"]
    assert client.post(
        "/api/v1/ratings", headers=_headers(user), json={"book_id": both_book.id, "score": 4}
    ).status_code == 201

    assert client.delete(f"/api/v1/reviews/{review_id}", headers=_headers(user)).status_code == 204
    assert client.get(f"/api/v1/ratings/books/{both_book.id}").json()["rating_count"] == 1
    assert client.delete(f"/api/v1/ratings/{both_book.id}", headers=_headers(user)).status_code == 204
    assert client.get(f"/api/v1/reviews/books/{both_book.id}").json() == []
    with session_factory() as session:
        archived_book = session.get(Book, review_only_book.id)
        assert archived_book is not None
        archived_book.is_archived = True
        session.commit()

    archived_reviews = client.get(f"/api/v1/reviews/books/{review_only_book.id}")

    assert client.get(f"/api/v1/ratings/books/{rating_only_book.id}").json()["rating_count"] == 1
    assert [review["book_id"] for review in archived_reviews.json()] == [review_only_book.id]
