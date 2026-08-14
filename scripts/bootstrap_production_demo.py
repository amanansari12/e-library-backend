"""Production Demo Bootstrap for the E-Library backend.

LIVE/INTERVIEWER PRODUCTION ENVIRONMENT ONLY.

This script safely initializes the production database with:
- Exactly 8 demo books and their PDFs (using existing BookFileService)
- Relevant authors and categories
- A set of demo users (alice, bob, carol, dave, erin)
- Representative borrowings, reservations, favorites, ratings, reviews, progress, and summaries.

It requires the following environment variables:
- APP_ENV=production
- DATABASE_URL=...
- DEMO_USERS_PASSWORD=... (to safely set the password for the demo users without hardcoding it)

Idempotency:
This script can be safely re-run. It will never drop tables, never downgrade migrations,
never delete data, and never duplicate data. It will skip creating any entity that already exists.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from starlette.datastructures import Headers, UploadFile
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

import app.models  # registers all ORM tables
from app.core.config import get_settings
from app.core.security import hash_password
from app.models.author import Author
from app.models.book import Book
from app.models.book_review import BookReview
from app.models.book_summary import BookSummary
from app.models.borrowing import Borrowing
from app.models.category import Category
from app.models.favorite import Favorite
from app.models.rating import Rating
from app.models.reading_progress import ReadingProgress
from app.models.reservation import Reservation
from app.models.user import User
from app.services.book_file import BookFileService


DATA_DIR = Path(__file__).resolve().parent.parent / 'data'

# Users to create
DEMO_USERS = [
    {"username": "alice", "email": "alice@elibrary.demo", "full_name": "Alice Reader", "role": "USER"},
    {"username": "bob", "email": "bob@elibrary.demo", "full_name": "Bob Bibliophile", "role": "USER"},
    {"username": "carol", "email": "carol@elibrary.demo", "full_name": "Carol Collector", "role": "USER"},
    {"username": "dave", "email": "dave@elibrary.demo", "full_name": "Dave Devotee", "role": "USER"},
    {"username": "erin", "email": "erin@elibrary.demo", "full_name": "Erin Enthusiast", "role": "USER"},
]

# (book title, username, status, borrowed_days_ago, due_in_days, returned_days_ago)
BORROWINGS = [
    ("Pride and Prejudice", "alice", "ACTIVE", 0, 14, None),
    ("Frankenstein; or, The Modern Prometheus", "bob", "ACTIVE", 0, 10, None),
    ("The Adventures of Sherlock Holmes", "carol", "ACTIVE", 0, 7, None),
    ("Dracula", "dave", "ACTIVE", 0, -3, None),
    ("The Wonderful Wizard of Oz", "alice", "ACTIVE", 0, 5, None),
    ("Pride and Prejudice", "bob", "RETURNED", 12, 0, 5),
    ("Frankenstein; or, The Modern Prometheus", "bob", "RETURNED", 15, 0, 8),
    ("The Adventures of Sherlock Holmes", "bob", "RETURNED", 6, 0, 2),
]

# (book title, username, status, position, notified_hours_ago)
RESERVATIONS = [
    ("A Tale of Two Cities", "carol", "READY", 1, 12),
    ("A Tale of Two Cities", "dave", "PENDING", 2, None),
    ("Treasure Island", "erin", "PENDING", 1, None),
]

FAVORITES = [
    ("Pride and Prejudice", "alice"),
    ("Frankenstein; or, The Modern Prometheus", "alice"),
    ("The Adventures of Sherlock Holmes", "bob"),
]

# (book title, username, score 1-5)
RATINGS = [
    ("Pride and Prejudice", "alice", 5),
    ("Pride and Prejudice", "bob", 4),
    ("Frankenstein; or, The Modern Prometheus", "carol", 5),
    ("The Adventures of Sherlock Holmes", "bob", 5),
]

# (book title, username, review text)
REVIEWS = [
    ("Pride and Prejudice", "alice", "A sharp, witty romance. The pacing is excellent."),
    ("Frankenstein; or, The Modern Prometheus", "carol", "The opening lines are unforgettable."),
]

# (book title, username, current_page, total_pages, read_hours_ago)
READING_PROGRESS = [
    ("Pride and Prejudice", "alice", 42, 250, 2),
    ("Frankenstein; or, The Modern Prometheus", "bob", 250, 250, 1),
    ("The Adventures of Sherlock Holmes", "erin", 300, 300, 0.5),
]

SUMMARY_MODEL = "gpt-4o-mini"
SUMMARIES = [
    "Pride and Prejudice",
    "Frankenstein; or, The Modern Prometheus",
    "The Adventures of Sherlock Holmes",
]

class BootstrapContext:
    def __init__(self, db: Session):
        self.db = db
        self.created = 0
        self.skipped = 0
        self.users: dict[str, User] = {}
        self.authors: dict[str, Author] = {}
        self.categories: dict[str, Category] = {}
        self.books: dict[str, Book] = {}
        self.book_file_service = BookFileService()


def _upload_for(book: dict) -> UploadFile:
    pdf_path = DATA_DIR / book["file"]
    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing PDF: {pdf_path}")
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
    return UploadFile(
        filename=Path(book["file"]).name,
        file=BytesIO(file_bytes),
        headers=Headers({"content-type": "application/pdf"}),
    )


def load_catalog_data():
    with open(DATA_DIR / 'authors.json', 'r', encoding='utf-8') as f:
        authors = json.load(f)
    with open(DATA_DIR / 'categories.json', 'r', encoding='utf-8') as f:
        categories = json.load(f)
    with open(DATA_DIR / 'book_catalog.json', 'r', encoding='utf-8') as f:
        books = json.load(f)

    demo_books = []
    for i, b in enumerate(books):
        if not b.get('seed_demo'):
            continue
        b['isbn'] = f'97800000{i:04d}'
        b['description'] = 'No description'
        b['year'] = b['publication_year']
        b['max_concurrent_borrows'] = 3
        demo_books.append(b)

    return authors, categories, demo_books


def bootstrap_users(ctx: BootstrapContext, password: str):
    print("Bootstrapping Users...")
    for user_def in DEMO_USERS:
        existing = ctx.db.scalar(
            select(User).where((User.username == user_def["username"]) | (User.email == user_def["email"]))
        )
        if existing:
            ctx.users[existing.username] = existing
            ctx.skipped += 1
            continue
        user = User(
            email=user_def["email"],
            username=user_def["username"],
            hashed_password=hash_password(password),
            full_name=user_def["full_name"],
            role=user_def["role"],
        )
        ctx.db.add(user)
        ctx.db.flush()
        ctx.users[user.username] = user
        ctx.created += 1


def bootstrap_authors(ctx: BootstrapContext, raw_authors: list):
    print("Bootstrapping Authors...")
    for a in raw_authors:
        existing = ctx.db.scalar(select(Author).where(Author.name == a["name"]))
        if existing:
            ctx.authors[existing.name] = existing
            ctx.skipped += 1
            continue
        author = Author(name=a["name"], biography=a["biography"])
        ctx.db.add(author)
        ctx.db.flush()
        ctx.authors[author.name] = author
        ctx.created += 1


def bootstrap_categories(ctx: BootstrapContext, raw_categories: list):
    print("Bootstrapping Categories...")
    for c in raw_categories:
        existing = ctx.db.scalar(select(Category).where(Category.name == c["name"]))
        if existing:
            ctx.categories[existing.name] = existing
            ctx.skipped += 1
            continue
        category = Category(name=c["name"], description=c["description"])
        ctx.db.add(category)
        ctx.db.flush()
        ctx.categories[category.name] = category
        ctx.created += 1


def bootstrap_books(ctx: BootstrapContext, raw_demo_books: list):
    print("Bootstrapping Books...")
    if len(raw_demo_books) != 8:
        raise ValueError(f"Expected exactly 8 demo books, found {len(raw_demo_books)}")
        
    for definition in raw_demo_books:
        existing = ctx.db.scalar(select(Book).where(Book.isbn == definition["isbn"]))
        if existing:
            ctx.books[existing.title] = existing
            ctx.skipped += 1
            continue

        book = Book(
            title=definition["title"],
            isbn=definition["isbn"],
            description=definition["description"],
            publication_year=definition["year"],
            max_concurrent_borrows=definition["max_concurrent_borrows"],
        )
        book.authors = [ctx.authors[definition["author"]]]
        book.categories = [ctx.categories[name] for name in definition["categories"]]
        ctx.db.add(book)
        ctx.db.flush()
        
        prepared = ctx.book_file_service.prepare_upload(_upload_for(definition))
        ctx.book_file_service.add_prepared_file(ctx.db, book, prepared)
        
        ctx.books[definition["title"]] = book
        ctx.created += 1


def bootstrap_borrowings(ctx: BootstrapContext):
    print("Bootstrapping Borrowings...")
    now = datetime.now(UTC)
    for title, username, status, borrowed_days_ago, due_in_days, returned_days_ago in BORROWINGS:
        if title not in ctx.books or username not in ctx.users:
            continue
        user = ctx.users[username]
        book = ctx.books[title]
        borrowed_at = now - timedelta(days=borrowed_days_ago)
        
        existing = ctx.db.scalar(select(Borrowing).where(Borrowing.user_id == user.id, Borrowing.book_id == book.id, Borrowing.status == status))
        if existing:
            ctx.skipped += 1
            continue

        if status == "ACTIVE":
            due_date = now + timedelta(days=due_in_days)
            returned_at = None
        else:
            due_date = borrowed_at + timedelta(days=7)
            returned_at = now - timedelta(days=returned_days_ago)

        ctx.db.add(
            Borrowing(
                user_id=user.id,
                book_id=book.id,
                borrowed_at=borrowed_at,
                due_date=due_date,
                returned_at=returned_at,
                status=status,
            )
        )
        ctx.db.flush()
        ctx.created += 1

    # Re-calculate active borrows
    for book in ctx.books.values():
        active_count = ctx.db.scalar(
            select(func.count()).select_from(Borrowing).where(
                Borrowing.book_id == book.id,
                Borrowing.status == "ACTIVE",
            )
        )
        book.current_borrows_count = int(active_count or 0)


def bootstrap_reservations(ctx: BootstrapContext):
    print("Bootstrapping Reservations...")
    now = datetime.now(UTC)
    for title, username, status, position, notified_hours_ago in RESERVATIONS:
        if title not in ctx.books or username not in ctx.users:
            continue
        user = ctx.users[username]
        book = ctx.books[title]
        
        existing = ctx.db.scalar(select(Reservation).where(Reservation.user_id == user.id, Reservation.book_id == book.id, Reservation.status == status))
        if existing:
            ctx.skipped += 1
            continue

        notified_at = None
        expires_at = None
        if status == "READY":
            notified_at = now - timedelta(hours=notified_hours_ago)
            expires_at = notified_at + timedelta(hours=48)
            
        ctx.db.add(
            Reservation(
                user_id=user.id,
                book_id=book.id,
                position=position,
                status=status,
                notified_at=notified_at,
                expires_at=expires_at,
            )
        )
        ctx.created += 1


def bootstrap_favorites(ctx: BootstrapContext):
    print("Bootstrapping Favorites...")
    for title, username in FAVORITES:
        if title not in ctx.books or username not in ctx.users:
            continue
        user = ctx.users[username]
        book = ctx.books[title]
        
        existing = ctx.db.scalar(select(Favorite).where(Favorite.user_id == user.id, Favorite.book_id == book.id))
        if existing:
            ctx.skipped += 1
            continue

        ctx.db.add(Favorite(user_id=user.id, book_id=book.id))
        ctx.created += 1


def bootstrap_ratings(ctx: BootstrapContext):
    print("Bootstrapping Ratings...")
    for title, username, score in RATINGS:
        if title not in ctx.books or username not in ctx.users:
            continue
        user = ctx.users[username]
        book = ctx.books[title]
        
        existing = ctx.db.scalar(select(Rating).where(Rating.user_id == user.id, Rating.book_id == book.id))
        if existing:
            ctx.skipped += 1
            continue

        ctx.db.add(Rating(user_id=user.id, book_id=book.id, score=score))
        ctx.created += 1


def bootstrap_reviews(ctx: BootstrapContext):
    print("Bootstrapping Reviews...")
    for title, username, review_text in REVIEWS:
        if title not in ctx.books or username not in ctx.users:
            continue
        user = ctx.users[username]
        book = ctx.books[title]
        
        existing = ctx.db.scalar(select(BookReview).where(BookReview.user_id == user.id, BookReview.book_id == book.id))
        if existing:
            ctx.skipped += 1
            continue

        ctx.db.add(BookReview(user_id=user.id, book_id=book.id, review_text=review_text))
        ctx.created += 1


def bootstrap_reading_progress(ctx: BootstrapContext):
    print("Bootstrapping Reading Progress...")
    now = datetime.now(UTC)
    for title, username, current_page, total_pages, hours_ago in READING_PROGRESS:
        if title not in ctx.books or username not in ctx.users:
            continue
        user = ctx.users[username]
        book = ctx.books[title]
        
        existing = ctx.db.scalar(select(ReadingProgress).where(ReadingProgress.user_id == user.id, ReadingProgress.book_id == book.id))
        if existing:
            ctx.skipped += 1
            continue

        ctx.db.add(
            ReadingProgress(
                user_id=user.id,
                book_id=book.id,
                content_version=book.content_version,
                current_page=current_page,
                total_pages=total_pages,
                last_read_at=now - timedelta(hours=hours_ago),
            )
        )
        ctx.created += 1


def bootstrap_summaries(ctx: BootstrapContext):
    print("Bootstrapping Summaries...")
    for index, title in enumerate(SUMMARIES, start=1):
        if title not in ctx.books:
            continue
        book = ctx.books[title]
        
        existing = ctx.db.scalar(select(BookSummary).where(BookSummary.book_id == book.id))
        if existing:
            ctx.skipped += 1
            continue

        ctx.db.add(
            BookSummary(
                book_id=book.id,
                content_version=book.content_version,
                model=SUMMARY_MODEL,
                summary_text=(
                    f"Production demo summary for {title!r}. "
                    f"{book.description} "
                    f"This cached summary was prepared for the demo and was not produced "
                    f"by a live AI call to conserve quota."
                ),
                token_count=280 + index * 10,
            )
        )
        ctx.created += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    # Safety checks
    env = os.getenv("APP_ENV")
    if env != "production":
        raise SystemExit("Safety abort: APP_ENV must be set to 'production' to run this script.")
    
    # We enforce DEMO_USERS_PASSWORD to avoid plaintext secrets
    demo_password = os.getenv("DEMO_USERS_PASSWORD")
    if not demo_password:
        raise SystemExit("Safety abort: DEMO_USERS_PASSWORD environment variable is required to securely bootstrap demo users.")

    settings = get_settings()
    if not settings.database_url:
        raise SystemExit("Safety abort: DATABASE_URL environment variable is missing.")

    engine = create_engine(settings.database_url, pool_pre_ping=True)

    authors_data, categories_data, books_data = load_catalog_data()

    with Session(engine) as db:
        ctx = BootstrapContext(db)
        
        try:
            bootstrap_users(ctx, demo_password)
            bootstrap_authors(ctx, authors_data)
            bootstrap_categories(ctx, categories_data)
            bootstrap_books(ctx, books_data)
            bootstrap_borrowings(ctx)
            bootstrap_reservations(ctx)
            bootstrap_favorites(ctx)
            bootstrap_ratings(ctx)
            bootstrap_reviews(ctx)
            bootstrap_reading_progress(ctx)
            bootstrap_summaries(ctx)
            
            db.commit()
            
            print("\nProduction demo bootstrap complete.\n")
            print(f"Created: {ctx.created}")
            print(f"Already existed (Skipped): {ctx.skipped}")
            
            admin_count = db.scalar(select(func.count()).select_from(User).where(User.role == "ADMIN"))
            if admin_count:
                print(f"\nConfirmed {admin_count} existing ADMIN user(s) remain untouched.")
            else:
                print("\nNo ADMIN user found. Please run scripts/create_admin.py if one is required.")
                
        except Exception as e:
            db.rollback()
            print(f"\nBootstrap failed: {e}")
            raise

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
