"""Initial migration - create books and reservations tables.

Revision ID: 001
Revises:
Create Date: 2026-03-11
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("isbn", sa.String(13), unique=True, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("author", sa.Text, nullable=False),
        sa.Column("genre", sa.String(100), nullable=False),
        sa.Column("published_year", sa.Integer, nullable=False),
        sa.Column("total_copies", sa.Integer, nullable=False),
        sa.Column("available_copies", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("available_copies >= 0", name="check_available_copies_non_negative"),
    )
    op.create_index("ix_books_isbn", "books", ["isbn"])
    op.create_index("ix_books_author", "books", ["author"])

    op.execute("CREATE TYPE reservation_status AS ENUM ('ACTIVE', 'RETURNED', 'OVERDUE')")

    op.create_table(
        "reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "book_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("books.id"), nullable=False
        ),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("reserved_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "RETURNED", "OVERDUE", name="reservation_status", create_type=False),
            nullable=False,
            server_default="ACTIVE",
        ),
    )
    op.create_index("ix_reservations_user_id", "reservations", ["user_id"])
    op.create_index("ix_reservations_status", "reservations", ["status"])
    op.create_index("ix_reservations_book_id", "reservations", ["book_id"])


def downgrade() -> None:
    op.drop_table("reservations")
    op.execute("DROP TYPE reservation_status")
    op.drop_table("books")
