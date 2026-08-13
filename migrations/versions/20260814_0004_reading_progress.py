"""Add version-aware private reading progress.

Revision ID: 20260814_0004
Revises: 20260814_0003
Create Date: 2026-08-14 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260814_0004"
down_revision: str | None = "20260814_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reading_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("content_version", sa.Integer(), nullable=False),
        sa.Column("current_page", sa.Integer(), nullable=False),
        sa.Column("total_pages", sa.Integer(), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("current_page >= 1", name="ck_reading_progress_current_page_positive"),
        sa.CheckConstraint("total_pages > 0", name="ck_reading_progress_total_pages_positive"),
        sa.CheckConstraint("current_page <= total_pages", name="ck_reading_progress_current_page_within_total"),
        sa.CheckConstraint("content_version >= 1", name="ck_reading_progress_content_version_positive"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "book_id", name="uq_reading_progress_user_book"),
    )
    op.create_index("ix_reading_progress_book_id", "reading_progress", ["book_id"], unique=False)
    op.create_index("ix_reading_progress_user_id", "reading_progress", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reading_progress_user_id", table_name="reading_progress")
    op.drop_index("ix_reading_progress_book_id", table_name="reading_progress")
    op.drop_table("reading_progress")
