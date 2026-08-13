"""Catalog business workflows."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.author import Author
from app.models.book import Book
from app.models.category import Category
from app.repositories.catalog import CatalogRepository
from app.schemas.book import BookCreate, BookPageResponse, BookResponse, BookUpdate
from app.schemas.catalog import AuthorCreate, AuthorUpdate, CategoryCreate, CategoryUpdate


class CatalogService:
    """Coordinates catalog mutations and archive lifecycle rules."""

    def __init__(self, repository: CatalogRepository | None = None) -> None:
        self.repository = repository or CatalogRepository()

    def list_books(
        self,
        db: Session,
        *,
        q: str | None,
        author_id: int | None,
        category_id: int | None,
        available: bool | None,
        year_from: int | None,
        year_to: int | None,
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
    ) -> BookPageResponse:
        books, total = self.repository.search_books(
            db,
            q=q,
            author_id=author_id,
            category_id=category_id,
            available=available,
            year_from=year_from,
            year_to=year_to,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        return BookPageResponse.create(
            [self._book_response(db, book) for book in books], total, page, page_size
        )

    def get_book(self, db: Session, book_id: int) -> BookResponse:
        return self._book_response(db, self._require_book(db, book_id))

    def create_book(self, db: Session, payload: BookCreate) -> BookResponse:
        book = Book(
            title=payload.title.strip(),
            isbn=payload.isbn.strip(),
            description=payload.description,
            content=payload.content,
            publication_year=payload.publication_year,
            max_concurrent_borrows=payload.max_concurrent_borrows,
        )
        book.authors = self._require_authors(db, payload.author_ids)
        book.categories = self._require_categories(db, payload.category_ids)
        db.add(book)
        self._commit(db, "A book with this ISBN already exists")
        return self.get_book(db, book.id)

    def update_book(self, db: Session, book_id: int, payload: BookUpdate) -> BookResponse:
        book = self._require_book(db, book_id)
        updates = payload.model_dump(exclude_unset=True)
        if "max_concurrent_borrows" in updates and updates["max_concurrent_borrows"] < book.current_borrows_count:
            raise AppError(409, "BORROW_CAPACITY_TOO_LOW", "Borrow capacity cannot be below active borrows")
        for field in ("title", "isbn", "description", "content", "publication_year", "max_concurrent_borrows"):
            if field in updates:
                value = updates[field]
                setattr(book, field, value.strip() if field in {"title", "isbn"} else value)
        if "author_ids" in updates:
            book.authors = self._require_authors(db, updates["author_ids"])
        if "category_ids" in updates:
            book.categories = self._require_categories(db, updates["category_ids"])
        book.content_version += 1
        self._commit(db, "A book with this ISBN already exists")
        return self.get_book(db, book.id)

    def archive_book(self, db: Session, book_id: int) -> BookResponse:
        book = self._require_book(db, book_id)
        if not book.is_archived:
            book.is_archived = True
            self.repository.cancel_active_reservations(db, book.id)
            self._commit(db, "Unable to archive the book")
        return self.get_book(db, book.id)

    def restore_book(self, db: Session, book_id: int) -> BookResponse:
        book = self._require_book(db, book_id)
        if book.is_archived:
            book.is_archived = False
            self._commit(db, "Unable to restore the book")
        return self.get_book(db, book.id)

    def create_author(self, db: Session, payload: AuthorCreate) -> Author:
        author = Author(name=payload.name.strip(), biography=payload.biography)
        db.add(author)
        self._commit(db, "Unable to create author")
        db.refresh(author)
        return author

    def update_author(self, db: Session, author_id: int, payload: AuthorUpdate) -> Author:
        author = self._require_author(db, author_id)
        updates = payload.model_dump(exclude_unset=True)
        if "name" in updates:
            author.name = updates["name"].strip()
        if "biography" in updates:
            author.biography = updates["biography"]
        self._commit(db, "Unable to update author")
        db.refresh(author)
        return author

    def create_category(self, db: Session, payload: CategoryCreate) -> Category:
        category = Category(name=payload.name.strip(), description=payload.description)
        db.add(category)
        self._commit(db, "A category with this name already exists")
        db.refresh(category)
        return category

    def update_category(self, db: Session, category_id: int, payload: CategoryUpdate) -> Category:
        category = self._require_category(db, category_id)
        updates = payload.model_dump(exclude_unset=True)
        if "name" in updates:
            category.name = updates["name"].strip()
        if "description" in updates:
            category.description = updates["description"]
        self._commit(db, "A category with this name already exists")
        db.refresh(category)
        return category

    def _book_response(self, db: Session, book: Book) -> BookResponse:
        average_rating, rating_count = self.repository.rating_stats(db, book.id)
        return BookResponse(
            id=book.id,
            title=book.title,
            isbn=book.isbn,
            description=book.description,
            content=book.content,
            publication_year=book.publication_year,
            max_concurrent_borrows=book.max_concurrent_borrows,
            current_borrows_count=book.current_borrows_count,
            available_slots=book.max_concurrent_borrows - book.current_borrows_count,
            content_version=book.content_version,
            is_archived=book.is_archived,
            authors=book.authors,
            categories=book.categories,
            average_rating=average_rating,
            rating_count=rating_count,
            created_at=book.created_at,
            updated_at=book.updated_at,
        )

    def _require_book(self, db: Session, book_id: int) -> Book:
        book = self.repository.get_book(db, book_id)
        if book is None:
            raise AppError(404, "BOOK_NOT_FOUND", "Book not found")
        return book

    def _require_author(self, db: Session, author_id: int) -> Author:
        author = self.repository.get_author(db, author_id)
        if author is None:
            raise AppError(404, "AUTHOR_NOT_FOUND", "Author not found")
        return author

    def _require_category(self, db: Session, category_id: int) -> Category:
        category = self.repository.get_category(db, category_id)
        if category is None:
            raise AppError(404, "CATEGORY_NOT_FOUND", "Category not found")
        return category

    def _require_authors(self, db: Session, author_ids: list[int]) -> list[Author]:
        authors = self.repository.get_authors(db, author_ids)
        if len(authors) != len(author_ids):
            raise AppError(404, "AUTHOR_NOT_FOUND", "One or more authors were not found")
        return authors

    def _require_categories(self, db: Session, category_ids: list[int]) -> list[Category]:
        categories = self.repository.get_categories(db, category_ids)
        if len(categories) != len(category_ids):
            raise AppError(404, "CATEGORY_NOT_FOUND", "One or more categories were not found")
        return categories

    @staticmethod
    def _commit(db: Session, message: str) -> None:
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise AppError(409, "CONFLICT", message) from exc
