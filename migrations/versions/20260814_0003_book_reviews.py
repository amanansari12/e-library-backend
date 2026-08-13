"""Add optional written book reviews.

Revision ID: 20260814_0003
Revises: 20260814_0002
Create Date: 2026-08-14 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260814_0003"
down_revision: str | None = "20260814_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "book_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "book_id", name="uq_book_reviews_user_book"),
    )
    op.create_index("ix_book_reviews_book_id", "book_reviews", ["book_id"], unique=False)
    op.create_index("ix_book_reviews_user_id", "book_reviews", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_book_reviews_user_id", table_name="book_reviews")
    op.drop_index("ix_book_reviews_book_id", table_name="book_reviews")
    op.drop_table("book_reviews")
