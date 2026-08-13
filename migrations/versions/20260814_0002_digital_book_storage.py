"""Replace database book content with local digital-file metadata.

Revision ID: 20260814_0002
Revises: 20260813_0001
Create Date: 2026-08-14 00:00:00

Existing development values in books.content were short demo text and cannot be
converted into authentic PDF/EPUB assets, so this migration removes that
non-canonical field rather than fabricating files.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260814_0002"
down_revision: str | None = "20260813_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # The prior schema could not contain genuine file records. Archive legacy
    # catalog rows rather than presenting them as borrowable digital resources;
    # active borrowings remain returnable under the existing domain behavior.
    op.execute("UPDATE reservations SET status = 'CANCELLED' WHERE status IN ('PENDING', 'READY')")
    op.execute("UPDATE books SET is_archived = true")
    op.create_table(
        "book_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("file_format", sa.String(length=20), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("file_size > 0", name="ck_book_files_file_size_positive"),
        sa.CheckConstraint("file_format IN ('PDF')", name="ck_book_files_file_format"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_book_files_book_id", "book_files", ["book_id"], unique=False)
    op.create_index(
        "uq_active_book_file",
        "book_files",
        ["book_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )
    op.drop_column("books", "content")


def downgrade() -> None:
    op.add_column("books", sa.Column("content", sa.Text(), nullable=True))
    op.drop_index("uq_active_book_file", table_name="book_files")
    op.drop_index("ix_book_files_book_id", table_name="book_files")
    op.drop_table("book_files")
