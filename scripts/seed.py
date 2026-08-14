"""Deterministic development/demo seed data for the E-Library backend.

DEVELOPMENT ONLY. Never run against a production database.

This script:
- refuses to run when any expected seed identity already exists (no silent duplicates);
- generates small, valid, book-specific PDFs locally (no internet access required);
- stores every PDF through the existing BookFileService pipeline so files are
  validated, checksums are generated, derived text is extracted, BookFile rows are
  created, and canonical bytes land under BOOK_STORAGE_ROOT;
- seeds 1 admin, 5 users, 10 authors, 8 categories, 20 books, borrowings
  (active/returned/overdue), reservations (PENDING and READY), favorites,
  ratings, reviews, reading progress, and cached summaries;
- never calls the AI provider and never inserts fake AI token usage.

Reset workflow (development only):
    alembic downgrade base && alembic upgrade head
    python scripts/seed.py

Usage:
    python scripts/seed.py
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from starlette.datastructures import Headers, UploadFile  # noqa: E402
from sqlalchemy import create_engine, func, inspect, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.models  # noqa: E402, F401 - registers all ORM tables
from app.core.config import get_settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.author import Author  # noqa: E402
from app.models.book import Book  # noqa: E402
from app.models.book_review import BookReview  # noqa: E402
from app.models.book_summary import BookSummary  # noqa: E402
from app.models.borrowing import Borrowing  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.favorite import Favorite  # noqa: E402
from app.models.rating import Rating  # noqa: E402
from app.models.reading_progress import ReadingProgress  # noqa: E402
from app.models.reservation import Reservation  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.book_file import BookFileService  # noqa: E402

# ---------------------------------------------------------------------------
# Seed identities. All passwords are LOCAL DEVELOPMENT ONLY values.
# ---------------------------------------------------------------------------

ADMIN_PASSWORD = "AdminPass!123"
USER_PASSWORD = "DevUser!123"

USERS = [
    {
        "username": "admin",
        "email": "admin@elibrary.dev",
        "full_name": "Admin User",
        "role": "ADMIN",
        "password": ADMIN_PASSWORD,
    },
    {
        "username": "alice",
        "email": "alice@elibrary.dev",
        "full_name": "Alice Reader",
        "role": "USER",
        "password": USER_PASSWORD,
    },
    {
        "username": "bob",
        "email": "bob@elibrary.dev",
        "full_name": "Bob Bibliophile",
        "role": "USER",
        "password": USER_PASSWORD,
    },
    {
        "username": "carol",
        "email": "carol@elibrary.dev",
        "full_name": "Carol Collector",
        "role": "USER",
        "password": USER_PASSWORD,
    },
    {
        "username": "dave",
        "email": "dave@elibrary.dev",
        "full_name": "Dave Devotee",
        "role": "USER",
        "password": USER_PASSWORD,
    },
    {
        "username": "erin",
        "email": "erin@elibrary.dev",
        "full_name": "Erin Enthusiast",
        "role": "USER",
        "password": USER_PASSWORD,
    },
]

AUTHORS = {
    "Jane Austen": "English novelist known for social comedy in the early nineteenth century.",
    "Charles Dickens": "Victorian novelist famous for memorable characters and social criticism.",
    "Mark Twain": "American humorist and author of classic adventure novels.",
    "Leo Tolstoy": "Russian author of epic realist novels.",
    "Mary Shelley": "English writer and pioneer of science fiction and Gothic fiction.",
    "H.G. Wells": "English writer and father of early science fiction.",
    "Bram Stoker": "Irish author best known for the Gothic horror novel Dracula.",
    "Oscar Wilde": "Irish playwright, novelist, and wit of the aesthetic movement.",
    "Edgar Allan Poe": "American writer and master of the Gothic short story and detective fiction.",
    "Herman Melville": "American novelist and poet of the sea and philosophical adventure.",
}

CATEGORIES = {
    "Classic Literature": "Enduring literary works of historical importance.",
    "Fiction": "Imaginative prose narrative.",
    "Gothic Fiction": "Dark fiction featuring mystery, horror, and the supernatural.",
    "Science Fiction": "Imaginative fiction exploring future science and technology.",
    "Adventure": "Stories of exciting journeys and action.",
    "Horror": "Fiction intended to frighten and unsettle.",
    "Drama": "Plays and emotionally charged fiction.",
    "Satire": "Fiction using humour to expose folly and vice.",
}

BOOKS = [
    {
        "title": "Pride and Prejudice",
        "isbn": "9780141439518",
        "author": "Jane Austen",
        "year": 1813,
        "categories": ["Classic Literature", "Fiction"],
        "max_concurrent_borrows": 3,
        "description": "The Bennet sisters navigate love, class, and manners in Georgian England.",
    },
    {
        "title": "Sense and Sensibility",
        "isbn": "9780141439662",
        "author": "Jane Austen",
        "year": 1811,
        "categories": ["Classic Literature", "Fiction"],
        "max_concurrent_borrows": 2,
        "description": "Two sisters balance reason and emotion while seeking happiness in love.",
    },
    {
        "title": "A Tale of Two Cities",
        "isbn": "9780141439600",
        "author": "Charles Dickens",
        "year": 1859,
        "categories": ["Classic Literature", "Fiction"],
        "max_concurrent_borrows": 3,
        "description": "A historical novel set in London and Paris during the French Revolution.",
    },
    {
        "title": "Great Expectations",
        "isbn": "9780141439563",
        "author": "Charles Dickens",
        "year": 1861,
        "categories": ["Classic Literature", "Fiction"],
        "max_concurrent_borrows": 2,
        "description": "The orphan Pip rises and falls through encounters with money, class, and loyalty.",
    },
    {
        "title": "The Adventures of Huckleberry Finn",
        "isbn": "9780142437179",
        "author": "Mark Twain",
        "year": 1884,
        "categories": ["Classic Literature", "Fiction", "Satire"],
        "max_concurrent_borrows": 3,
        "description": "A boy's river journey exposes the hypocrisy of antebellum American society.",
    },
    {
        "title": "The Adventures of Tom Sawyer",
        "isbn": "9780143039563",
        "author": "Mark Twain",
        "year": 1876,
        "categories": ["Classic Literature", "Adventure"],
        "max_concurrent_borrows": 2,
        "description": "A mischievous boy's escapades along the Mississippi in a small town.",
    },
    {
        "title": "War and Peace",
        "isbn": "9781400079988",
        "author": "Leo Tolstoy",
        "year": 1869,
        "categories": ["Classic Literature", "Fiction"],
        "max_concurrent_borrows": 3,
        "description": "An epic panorama of Russian society during the Napoleonic Wars.",
    },
    {
        "title": "Anna Karenina",
        "isbn": "9780143035008",
        "author": "Leo Tolstoy",
        "year": 1878,
        "categories": ["Classic Literature", "Fiction"],
        "max_concurrent_borrows": 2,
        "description": "A tragic story of love, fidelity, and society in Imperial Russia.",
    },
    {
        "title": "Frankenstein",
        "isbn": "9780486282114",
        "author": "Mary Shelley",
        "year": 1818,
        "categories": ["Gothic Fiction", "Science Fiction", "Horror"],
        "max_concurrent_borrows": 3,
        "description": "A scientist's creation confronts its maker and the limits of ambition.",
    },
    {
        "title": "The Last Man",
        "isbn": "9780803260951",
        "author": "Mary Shelley",
        "year": 1826,
        "categories": ["Gothic Fiction", "Science Fiction"],
        "max_concurrent_borrows": 2,
        "description": "A futuristic tale of a plague that nearly wipes out humanity.",
    },
    {
        "title": "The Time Machine",
        "isbn": "9780451530707",
        "author": "H.G. Wells",
        "year": 1895,
        "categories": ["Science Fiction", "Adventure"],
        "max_concurrent_borrows": 3,
        "description": "A Victorian inventor travels far into the future to a strange divided world.",
    },
    {
        "title": "The War of the Worlds",
        "isbn": "9780451530653",
        "author": "H.G. Wells",
        "year": 1898,
        "categories": ["Science Fiction", "Horror"],
        "max_concurrent_borrows": 2,
        "description": "Martian invaders descend on England in this classic invasion novel.",
    },
    {
        "title": "Dracula",
        "isbn": "9780486411095",
        "author": "Bram Stoker",
        "year": 1897,
        "categories": ["Gothic Fiction", "Horror"],
        "max_concurrent_borrows": 2,
        "description": "A vampire count moves to England in search of new blood.",
    },
    {
        "title": "The Jewel of Seven Stars",
        "isbn": "9781592241602",
        "author": "Bram Stoker",
        "year": 1903,
        "categories": ["Gothic Fiction", "Horror"],
        "max_concurrent_borrows": 2,
        "description": "An archaeologist's obsession with an ancient Egyptian mystery.",
    },
    {
        "title": "The Picture of Dorian Gray",
        "isbn": "9780486278070",
        "author": "Oscar Wilde",
        "year": 1890,
        "categories": ["Gothic Fiction", "Fiction", "Drama"],
        "max_concurrent_borrows": 3,
        "description": "A portrait ages while its subject pursues beauty without consequence.",
    },
    {
        "title": "The Importance of Being Earnest",
        "isbn": "9780486264783",
        "author": "Oscar Wilde",
        "year": 1895,
        "categories": ["Drama", "Satire"],
        "max_concurrent_borrows": 2,
        "description": "A comic farce of mistaken identity and courtship in Victorian society.",
    },
    {
        "title": "The Murders in the Rue Morgue",
        "isbn": "9780486811108",
        "author": "Edgar Allan Poe",
        "year": 1841,
        "categories": ["Fiction", "Horror"],
        "max_concurrent_borrows": 3,
        "description": "The detective C. Auguste Dupin solves a baffling double murder in Paris.",
    },
    {
        "title": "The Fall of the House of Usher",
        "isbn": "9780486267036",
        "author": "Edgar Allan Poe",
        "year": 1839,
        "categories": ["Gothic Fiction", "Horror"],
        "max_concurrent_borrows": 2,
        "description": "A decaying mansion mirrors the collapse of a troubled family.",
    },
    {
        "title": "Moby-Dick",
        "isbn": "9780142437247",
        "author": "Herman Melville",
        "year": 1851,
        "categories": ["Classic Literature", "Adventure"],
        "max_concurrent_borrows": 3,
        "description": "A whaling voyage becomes a captain's obsessive hunt for a white whale.",
    },
    {
        "title": "Billy Budd, Sailor",
        "isbn": "9780486421018",
        "author": "Herman Melville",
        "year": 1924,
        "categories": ["Classic Literature", "Drama"],
        "max_concurrent_borrows": 2,
        "description": "A guileless sailor faces a tragic confrontation aboard a warship.",
    },
]

# (book title, username, status, borrowed_days_ago, due_in_days, returned_days_ago)
BORROWINGS = [
    ("Pride and Prejudice", "alice", "ACTIVE", 0, 14, None),
    ("Pride and Prejudice", "bob", "ACTIVE", 0, 10, None),
    ("Sense and Sensibility", "carol", "ACTIVE", 0, 7, None),
    ("Sense and Sensibility", "dave", "ACTIVE", 0, -3, None),
    ("A Tale of Two Cities", "alice", "ACTIVE", 0, 5, None),
    ("A Tale of Two Cities", "carol", "ACTIVE", 0, 12, None),
    ("A Tale of Two Cities", "erin", "ACTIVE", 0, 9, None),
    ("Great Expectations", "bob", "ACTIVE", 0, 20, None),
    ("The Adventures of Huckleberry Finn", "carol", "ACTIVE", 0, 8, None),
    ("The Adventures of Huckleberry Finn", "dave", "ACTIVE", 0, -1, None),
    ("The Adventures of Tom Sawyer", "erin", "ACTIVE", 0, 6, None),
    ("Frankenstein", "alice", "ACTIVE", 0, 15, None),
    ("Frankenstein", "bob", "ACTIVE", 0, 11, None),
    ("The Time Machine", "erin", "ACTIVE", 0, 13, None),
    ("Dracula", "dave", "ACTIVE", 0, 4, None),
    ("Dracula", "bob", "ACTIVE", 0, 9, None),
    ("Moby-Dick", "dave", "ACTIVE", 0, 18, None),
    ("Moby-Dick", "alice", "ACTIVE", 0, 3, None),
    ("Sense and Sensibility", "bob", "RETURNED", 12, 0, 5),
    ("A Tale of Two Cities", "bob", "RETURNED", 15, 0, 8),
    ("The Adventures of Huckleberry Finn", "bob", "RETURNED", 6, 0, 2),
    ("Frankenstein", "carol", "RETURNED", 9, 0, 3),
    ("The Time Machine", "alice", "RETURNED", 12, 0, 6),
    ("Dracula", "alice", "RETURNED", 15, 0, 9),
    ("Moby-Dick", "bob", "RETURNED", 10, 0, 4),
]

# (book title, username, status, position, notified_hours_ago)
RESERVATIONS = [
    ("Pride and Prejudice", "carol", "READY", 1, 12),
    ("Pride and Prejudice", "dave", "PENDING", 2, None),
    ("Sense and Sensibility", "erin", "PENDING", 1, None),
    ("Sense and Sensibility", "alice", "PENDING", 2, None),
    ("The Adventures of Huckleberry Finn", "erin", "READY", 1, 10),
    ("The Adventures of Huckleberry Finn", "alice", "PENDING", 2, None),
    ("Frankenstein", "erin", "READY", 1, 20),
    ("Frankenstein", "carol", "PENDING", 2, None),
    ("Dracula", "alice", "PENDING", 1, None),
    ("Dracula", "carol", "PENDING", 2, None),
]

FAVORITES = [
    ("Pride and Prejudice", "alice"),
    ("The Adventures of Huckleberry Finn", "alice"),
    ("Frankenstein", "alice"),
    ("Dracula", "alice"),
    ("Sense and Sensibility", "bob"),
    ("The Adventures of Tom Sawyer", "bob"),
    ("The War of the Worlds", "bob"),
    ("A Tale of Two Cities", "carol"),
    ("The Time Machine", "carol"),
    ("The Murders in the Rue Morgue", "carol"),
    ("Pride and Prejudice", "dave"),
    ("Moby-Dick", "dave"),
    ("Frankenstein", "erin"),
    ("Billy Budd, Sailor", "erin"),
]

# (book title, username, score 1-5)
RATINGS = [
    ("Pride and Prejudice", "alice", 5),
    ("Pride and Prejudice", "bob", 4),
    ("Pride and Prejudice", "carol", 5),
    ("Sense and Sensibility", "bob", 5),
    ("Sense and Sensibility", "carol", 3),
    ("Sense and Sensibility", "dave", 4),
    ("Sense and Sensibility", "erin", 2),
    ("A Tale of Two Cities", "erin", 5),
    ("A Tale of Two Cities", "alice", 4),
    ("A Tale of Two Cities", "bob", 3),
    ("Great Expectations", "bob", 5),
    ("Great Expectations", "alice", 4),
    ("The Adventures of Huckleberry Finn", "carol", 5),
    ("The Adventures of Huckleberry Finn", "dave", 3),
    ("The Adventures of Huckleberry Finn", "alice", 4),
    ("The Adventures of Tom Sawyer", "erin", 4),
    ("War and Peace", "alice", 5),
    ("War and Peace", "bob", 4),
    ("Anna Karenina", "dave", 3),
    ("Frankenstein", "alice", 5),
    ("Frankenstein", "bob", 5),
    ("Frankenstein", "carol", 5),
    ("Frankenstein", "erin", 4),
    ("The Last Man", "erin", 4),
    ("The Last Man", "alice", 5),
    ("The Time Machine", "alice", 5),
    ("The Time Machine", "erin", 5),
    ("The Time Machine", "carol", 4),
    ("The War of the Worlds", "bob", 4),
    ("The War of the Worlds", "dave", 5),
    ("Dracula", "dave", 4),
    ("Dracula", "bob", 3),
    ("The Jewel of Seven Stars", "carol", 5),
    ("The Picture of Dorian Gray", "alice", 4),
    ("The Importance of Being Earnest", "bob", 5),
    ("The Importance of Being Earnest", "dave", 4),
    ("The Murders in the Rue Morgue", "carol", 4),
    ("The Murders in the Rue Morgue", "erin", 5),
    ("The Murders in the Rue Morgue", "bob", 3),
    ("The Fall of the House of Usher", "alice", 4),
    ("The Fall of the House of Usher", "dave", 5),
    ("Moby-Dick", "dave", 5),
    ("Moby-Dick", "bob", 4),
    ("Moby-Dick", "alice", 5),
    ("Billy Budd, Sailor", "erin", 4),
    ("Billy Budd, Sailor", "carol", 3),
]

# (book title, username, review text) - every reviewer has borrowed the book.
REVIEWS = [
    (
        "Pride and Prejudice",
        "alice",
        "A sharp, witty romance. The pacing is excellent and the dialogue still sparkles "
        "more than two centuries later.",
    ),
    (
        "A Tale of Two Cities",
        "carol",
        "The opening lines are unforgettable, and the final act is one of the most moving "
        "conclusions in literature.",
    ),
    (
        "Sense and Sensibility",
        "bob",
        "A quieter Austen novel, but the contrast between the two sisters makes it deeply "
        "thoughtful and rewarding.",
    ),
    (
        "The Time Machine",
        "erin",
        "Short, imaginative, and surprisingly dark for its age. A great introduction to "
        "early science fiction.",
    ),
    (
        "Frankenstein",
        "carol",
        "Far more philosophical than the popular image suggests. The monster's voice is "
        "genuinely moving.",
    ),
    (
        "Moby-Dick",
        "dave",
        "Part adventure, part encyclopaedia, part meditation. Demanding but worth the effort.",
    ),
    (
        "The Time Machine",
        "alice",
        "A compact classic that raises big questions about class and progress.",
    ),
    (
        "Great Expectations",
        "bob",
        "Dickens at his most controlled. Pip's growth feels real and earned.",
    ),
]

# (book title, username, current_page, total_pages, read_hours_ago)
READING_PROGRESS = [
    ("Pride and Prejudice", "alice", 42, 250, 2),
    ("Pride and Prejudice", "bob", 250, 250, 1),
    ("A Tale of Two Cities", "erin", 300, 300, 0.5),
    ("Sense and Sensibility", "carol", 88, 180, 3),
    ("Dracula", "dave", 120, 320, 24),
    ("Frankenstein", "alice", 60, 200, 5),
]

SUMMARY_MODEL = "gpt-4o-mini"
SUMMARIES = [
    "Pride and Prejudice",
    "A Tale of Two Cities",
    "The Adventures of Huckleberry Finn",
    "Frankenstein",
    "The Time Machine",
    "Dracula",
    "The Murders in the Rue Morgue",
    "Moby-Dick",
]


# ---------------------------------------------------------------------------
# Deterministic local PDF generation (no internet, no external assets).
# ---------------------------------------------------------------------------

def _pdf_escape(text: str) -> str:
    """Escape parentheses and backslashes for a PDF literal string."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_demo_pdf(book: dict) -> bytes:
    """Build a small, valid, deterministic PDF whose text layer is extractable."""
    lines = [
        f"Demo PDF: {book['title']}",
        f"Author: {book['author']}",
        f"Publication year: {book['year']}",
        "",
        "This PDF is a locally generated development-only placeholder. It is not a",
        "copy of the published work and exists so the digital-book pipeline can be",
        "demonstrated without external downloads or copyrighted files.",
        "",
        "The BookFile metadata, SHA-256 checksum, and derived extracted text are",
        "created through the same validation pipeline used for real uploads.",
    ]
    stream_parts = ["BT /F1 11 Tf 72 720 Td"]
    for index, line in enumerate(lines):
        if index:
            stream_parts.append("T*")
        stream_parts.append(f"({_pdf_escape(line)}) Tj")
    stream_parts.append("ET")
    stream = "\n".join(stream_parts).encode("latin-1")

    buffer = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = []
    object_count = 0

    def add_object(body: bytes) -> None:
        nonlocal object_count, buffer
        object_count += 1
        offsets.append(len(buffer))
        buffer += b"%d 0 obj\n" % object_count
        buffer += body
        buffer += b"\nendobj\n"

    add_object(b"<< /Type /Catalog /Pages 2 0 R >>")
    add_object(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add_object(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>"
    )
    add_object(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
    add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    xref_position = len(buffer)
    buffer += b"xref\n0 %d\n" % (object_count + 1)
    buffer += b"0000000000 65535 f \n"
    for offset in offsets:
        buffer += b"%010d 00000 n \n" % offset
    buffer += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (
        object_count + 1,
        xref_position,
    )
    return bytes(buffer)


def _upload_for(book: dict) -> UploadFile:
    slug = book["title"].lower().replace(" ", "-").replace(",", "")
    return UploadFile(
        filename=f"{slug}.pdf",
        file=BytesIO(build_demo_pdf(book)),
        headers=Headers({"content-type": "application/pdf"}),
    )


# ---------------------------------------------------------------------------
# Seed application.
# ---------------------------------------------------------------------------

def _count(db, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _table_exists(db) -> bool:
    return inspect(db.get_bind()).has_table("users")


def _validate_seed_shape() -> None:
    if len(AUTHORS) != 10:
        raise SystemExit("Seed data invariant failed: expected exactly 10 authors")
    if len(CATEGORIES) != 8:
        raise SystemExit("Seed data invariant failed: expected exactly 8 categories")
    if len(BOOKS) != 20:
        raise SystemExit("Seed data invariant failed: expected exactly 20 books")
    isbns = [book["isbn"] for book in BOOKS]
    if len(isbns) != len(set(isbns)):
        raise SystemExit("Seed data invariant failed: book ISBNs must be unique")
    if len({book["title"] for book in BOOKS}) != len(BOOKS):
        raise SystemExit("Seed data invariant failed: book titles must be unique")
    known_authors = set(AUTHORS)
    known_categories = set(CATEGORIES)
    for book in BOOKS:
        if book["author"] not in known_authors:
            raise SystemExit(f"Seed data invariant failed: unknown author {book['author']!r}")
        if not set(book["categories"]) <= known_categories:
            raise SystemExit(f"Seed data invariant failed: unknown category in {book['title']!r}")
    for _, user, status, *_ in BORROWINGS:
        if status not in {"ACTIVE", "RETURNED"}:
            raise SystemExit(f"Seed data invariant failed: bad borrowing status {status!r}")
    for _, _, score in RATINGS:
        if not 1 <= score <= 5:
            raise SystemExit(f"Seed data invariant failed: rating {score} out of range")


def _warn_if_existing(db) -> None:
    """Fail clearly instead of silently creating duplicates."""
    conflicts: list[str] = []
    usernames = [entry["username"] for entry in USERS]
    existing_users = set(
        db.scalars(select(User.username).where(User.username.in_(usernames)))
    )
    if existing_users:
        conflicts.append(f"users already present: {sorted(existing_users)}")
    isbns = [book["isbn"] for book in BOOKS]
    existing_isbns = set(db.scalars(select(Book.isbn).where(Book.isbn.in_(isbns))))
    if existing_isbns:
        conflicts.append(f"books already present with ISBNs: {sorted(existing_isbns)}")
    existing_categories = set(
        db.scalars(select(Category.name).where(Category.name.in_(list(CATEGORIES))))
    )
    if existing_categories:
        conflicts.append(f"categories already present: {sorted(existing_categories)}")
    existing_authors = set(
        db.scalars(select(Author.name).where(Author.name.in_(list(AUTHORS))))
    )
    if existing_authors:
        conflicts.append(f"authors already present: {sorted(existing_authors)}")
    if conflicts:
        message = "\n".join(conflicts)
        raise SystemExit(
            "Seed data already exists in the target database. Refusing to create "
            "duplicates.\nDetected:\n"
            + message
            + "\nFor a clean development reset run:\n"
            "    alembic downgrade base && alembic upgrade head\n"
            "then re-run this script."
        )


def _seed_users(db) -> dict[str, User]:
    users = {}
    for entry in USERS:
        user = User(
            email=entry["email"],
            username=entry["username"],
            hashed_password=hash_password(entry["password"]),
            full_name=entry["full_name"],
            role=entry["role"],
        )
        db.add(user)
        users[entry["username"]] = user
    db.flush()
    return users


def _seed_authors(db) -> dict[str, Author]:
    authors = {}
    for name, biography in AUTHORS.items():
        author = Author(name=name, biography=biography)
        db.add(author)
        authors[name] = author
    db.flush()
    return authors


def _seed_categories(db) -> dict[str, Category]:
    categories = {}
    for name, description in CATEGORIES.items():
        category = Category(name=name, description=description)
        db.add(category)
        categories[name] = category
    db.flush()
    return categories


def _seed_books(
    db, authors: dict[str, Author], categories: dict[str, Category], book_file_service: BookFileService
) -> dict[str, Book]:
    books = {}
    stored_keys: list[str] = []
    try:
        for definition in BOOKS:
            book = Book(
                title=definition["title"],
                isbn=definition["isbn"],
                description=definition["description"],
                publication_year=definition["year"],
                max_concurrent_borrows=definition["max_concurrent_borrows"],
            )
            book.authors = [authors[definition["author"]]]
            book.categories = [categories[name] for name in definition["categories"]]
            db.add(book)
            db.flush()
            prepared = book_file_service.prepare_upload(_upload_for(definition))
            book_file = book_file_service.add_prepared_file(db, book, prepared)
            stored_keys.append(book_file.storage_key)
            books[definition["title"]] = book
        return books
    except Exception:
        db.rollback()
        for storage_key in stored_keys:
            book_file_service.storage.delete(storage_key)
        raise


def _seed_borrowings(db, books: dict[str, Book], users: dict[str, User]) -> None:
    now = datetime.now(UTC)
    for title, username, status, borrowed_days_ago, due_in_days, returned_days_ago in BORROWINGS:
        borrowed_at = now - timedelta(days=borrowed_days_ago)
        if status == "ACTIVE":
            due_date = now + timedelta(days=due_in_days)
            returned_at = None
        else:
            due_date = borrowed_at + timedelta(days=7)
            returned_at = now - timedelta(days=returned_days_ago)
        db.add(
            Borrowing(
                user_id=users[username].id,
                book_id=books[title].id,
                borrowed_at=borrowed_at,
                due_date=due_date,
                returned_at=returned_at,
                status=status,
            )
        )
    for book in books.values():
        active_count = db.scalar(
            select(func.count()).select_from(Borrowing).where(
                Borrowing.book_id == book.id,
                Borrowing.status == "ACTIVE",
            )
        )
        book.current_borrows_count = int(active_count or 0)


def _seed_reservations(db, books: dict[str, Book], users: dict[str, User]) -> None:
    now = datetime.now(UTC)
    for title, username, status, position, notified_hours_ago in RESERVATIONS:
        notified_at = None
        expires_at = None
        if status == "READY":
            notified_at = now - timedelta(hours=notified_hours_ago)
            expires_at = notified_at + timedelta(hours=48)
        db.add(
            Reservation(
                user_id=users[username].id,
                book_id=books[title].id,
                position=position,
                status=status,
                notified_at=notified_at,
                expires_at=expires_at,
            )
        )


def _seed_favorites(db, books: dict[str, Book], users: dict[str, User]) -> None:
    for title, username in FAVORITES:
        db.add(Favorite(user_id=users[username].id, book_id=books[title].id))


def _seed_ratings(db, books: dict[str, Book], users: dict[str, User]) -> None:
    for title, username, score in RATINGS:
        db.add(Rating(user_id=users[username].id, book_id=books[title].id, score=score))


def _seed_reviews(db, books: dict[str, Book], users: dict[str, User]) -> None:
    for title, username, review_text in REVIEWS:
        db.add(
            BookReview(
                user_id=users[username].id,
                book_id=books[title].id,
                review_text=review_text,
            )
        )


def _seed_reading_progress(db, books: dict[str, Book], users: dict[str, User]) -> None:
    now = datetime.now(UTC)
    for title, username, current_page, total_pages, hours_ago in READING_PROGRESS:
        db.add(
            ReadingProgress(
                user_id=users[username].id,
                book_id=books[title].id,
                content_version=books[title].content_version,
                current_page=current_page,
                total_pages=total_pages,
                last_read_at=now - timedelta(hours=hours_ago),
            )
        )


def _seed_summaries(db, books: dict[str, Book]) -> None:
    for index, title in enumerate(SUMMARIES, start=1):
        book = books[title]
        db.add(
            BookSummary(
                book_id=book.id,
                content_version=book.content_version,
                model=SUMMARY_MODEL,
                summary_text=(
                    f"Standard development summary for {title!r}. "
                    f"{book.description} "
                    f"This cached summary is deterministic seed data and was not produced "
                    f"by a live AI call; it demonstrates the database-backed cache."
                ),
                token_count=280 + index * 10,
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    _validate_seed_shape()
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)

    with Session(engine) as db:
        if not _table_exists(db):
            raise SystemExit(
                "The target database schema is missing. Run 'alembic upgrade head' first."
            )

        _warn_if_existing(db)
        book_file_service = BookFileService()
        users = _seed_users(db)
        authors = _seed_authors(db)
        categories = _seed_categories(db)
        books = _seed_books(db, authors, categories, book_file_service)
        _seed_borrowings(db, books, users)
        _seed_reservations(db, books, users)
        _seed_favorites(db, books, users)
        _seed_ratings(db, books, users)
        _seed_reviews(db, books, users)
        _seed_reading_progress(db, books, users)
        _seed_summaries(db, books)
        db.commit()

    with Session(engine) as db:
        print("Seed complete (LOCAL DEVELOPMENT ONLY):")
        print(f"  users:                 {_count(db, User)}")
        print(f"  authors:               {_count(db, Author)}")
        print(f"  categories:            {_count(db, Category)}")
        print(f"  books:                 {_count(db, Book)}")
        print(f"  borrowings:            {_count(db, Borrowing)}")
        print(f"  reservations:          {_count(db, Reservation)}")
        print(f"  favorites:             {_count(db, Favorite)}")
        print(f"  ratings:               {_count(db, Rating)}")
        print(f"  reviews:               {_count(db, BookReview)}")
        print(f"  reading_progress:      {_count(db, ReadingProgress)}")
        print(f"  book_summaries:        {_count(db, BookSummary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
