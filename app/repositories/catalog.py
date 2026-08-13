"""Database queries for books, authors, and categories."""

from sqlalchemy import or_, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.models.author import Author
from app.models.book import Book
from app.models.category import Category
from app.models.rating import Rating
from app.models.reservation import Reservation


class CatalogRepository:
    """Catalog persistence queries without business policy."""

    _book_options = (selectinload(Book.authors), selectinload(Book.categories))

    def search_books(
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
    ) -> tuple[list[Book], int]:
        """Search the active catalog with PostgreSQL ILIKE fallback support."""
        filters = [Book.is_archived.is_(False)]
        if q:
            pattern = f"%{q.strip()}%"
            filters.append(
                or_(
                    Book.title.ilike(pattern),
                    Book.description.ilike(pattern),
                    Author.name.ilike(pattern),
                    Category.name.ilike(pattern),
                )
            )
        if author_id is not None:
            filters.append(Author.id == author_id)
        if category_id is not None:
            filters.append(Category.id == category_id)
        if available is True:
            filters.append(Book.current_borrows_count < Book.max_concurrent_borrows)
        if available is False:
            filters.append(Book.current_borrows_count >= Book.max_concurrent_borrows)
        if year_from is not None:
            filters.append(Book.publication_year >= year_from)
        if year_to is not None:
            filters.append(Book.publication_year <= year_to)

        query = select(Book).outerjoin(Book.authors).outerjoin(Book.categories).where(*filters).distinct()
        total = db.scalar(
            select(func.count(func.distinct(Book.id)))
            .select_from(Book)
            .outerjoin(Book.authors)
            .outerjoin(Book.categories)
            .where(*filters)
        )
        sort_column = {
            "title": Book.title,
            "publication_year": Book.publication_year,
            "created_at": Book.created_at,
        }[sort_by]
        ordering = (
            (sort_column.desc(), Book.id.desc())
            if sort_order == "desc"
            else (sort_column.asc(), Book.id.asc())
        )
        books = list(
            db.scalars(
                query.options(*self._book_options)
                .order_by(*ordering)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return books, int(total or 0)

    def get_book(self, db: Session, book_id: int) -> Book | None:
        return db.scalar(select(Book).options(*self._book_options).where(Book.id == book_id))

    def list_authors(self, db: Session) -> list[Author]:
        return list(db.scalars(select(Author).order_by(Author.name, Author.id)))

    def get_author(self, db: Session, author_id: int) -> Author | None:
        return db.get(Author, author_id)

    def list_categories(self, db: Session) -> list[Category]:
        return list(db.scalars(select(Category).order_by(Category.name, Category.id)))

    def get_category(self, db: Session, category_id: int) -> Category | None:
        return db.get(Category, category_id)

    def get_authors(self, db: Session, author_ids: list[int]) -> list[Author]:
        if not author_ids:
            return []
        return list(db.scalars(select(Author).where(Author.id.in_(author_ids))))

    def get_categories(self, db: Session, category_ids: list[int]) -> list[Category]:
        if not category_ids:
            return []
        return list(db.scalars(select(Category).where(Category.id.in_(category_ids))))

    def get_books_by_isbns(self, db: Session, isbns: list[str]) -> list[Book]:
        if not isbns:
            return []
        return list(db.scalars(select(Book).where(Book.isbn.in_(isbns))))

    def rating_stats(self, db: Session, book_id: int) -> tuple[float | None, int]:
        average, count = db.execute(
            select(func.avg(Rating.score), func.count(Rating.id)).where(Rating.book_id == book_id)
        ).one()
        return (float(average) if average is not None else None, int(count))

    def cancel_active_reservations(self, db: Session, book_id: int) -> None:
        db.execute(
            update(Reservation)
            .where(
                Reservation.book_id == book_id,
                Reservation.status.in_(("PENDING", "READY")),
            )
            .values(status="CANCELLED")
        )
