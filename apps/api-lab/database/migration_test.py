"""Tests for database migrations.

Validates that:
- Migrations apply cleanly to a fresh database
- Running migrations twice is idempotent (checksum validation)
- The resulting schema matches expectations
- Check mode correctly reports migration status

Requires a running PostgreSQL instance. Skips if not available.
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

import asyncpg
import pytest

# Add the database directory to the path so we can import migrate
sys.path.insert(0, str(Path(__file__).parent))

from migrate import _discover_migrations, _file_checksum, migrate

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.environ.get("POSTGRES_USER", "playground")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "playground")

# Use a unique test database to avoid interfering with other tests
TEST_DB = f"api_lab_migration_test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def _admin_connect():
    return await asyncpg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database="playground",
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


async def _create_test_db():
    conn = await _admin_connect()
    try:
        await conn.execute(f'CREATE DATABASE "{TEST_DB}"')
    finally:
        await conn.close()


async def _drop_test_db():
    conn = await _admin_connect()
    try:
        # Terminate existing connections
        await conn.execute(
            f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{TEST_DB}' AND pid <> pg_backend_pid()
            """
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}"')
    finally:
        await conn.close()


async def _test_connect():
    return await asyncpg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=TEST_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Create a fresh test database, drop it after tests."""
    try:
        asyncio.get_event_loop().run_until_complete(_admin_connect()).close()
    except Exception:
        pytest.skip("PostgreSQL not reachable")

    asyncio.get_event_loop().run_until_complete(_create_test_db())
    yield
    asyncio.get_event_loop().run_until_complete(_drop_test_db())


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """Point migrate.py at the test database."""
    monkeypatch.setenv("POSTGRES_HOST", POSTGRES_HOST)
    monkeypatch.setenv("POSTGRES_PORT", str(POSTGRES_PORT))
    monkeypatch.setenv("POSTGRES_DATABASE", TEST_DB)
    monkeypatch.setenv("POSTGRES_USER", POSTGRES_USER)
    monkeypatch.setenv("POSTGRES_PASSWORD", POSTGRES_PASSWORD)

    # Reload module-level config
    import migrate

    migrate.POSTGRES_HOST = POSTGRES_HOST
    migrate.POSTGRES_PORT = POSTGRES_PORT
    migrate.POSTGRES_DATABASE = TEST_DB
    migrate.POSTGRES_USER = POSTGRES_USER
    migrate.POSTGRES_PASSWORD = POSTGRES_PASSWORD


def test_discover_migrations():
    """Migration files follow naming convention and are ordered."""
    migrations = _discover_migrations()
    assert len(migrations) > 0
    versions = [v for v, _n, _p in migrations]
    assert versions == sorted(versions), "Migrations must be ordered by version"
    assert all(v > 0 for v in versions), "Versions must be positive integers"


def test_migrations_have_checksums():
    """Each migration file produces a valid checksum."""
    for _version, _name, path in _discover_migrations():
        checksum = _file_checksum(path)
        assert len(checksum) == 64, f"Expected SHA-256 hex digest for {path.name}"


@pytest.mark.asyncio
async def test_apply_migrations_fresh():
    """Migrations apply cleanly to a fresh database."""
    count = await migrate()
    assert count > 0


@pytest.mark.asyncio
async def test_schema_migrations_table_populated():
    """After applying, schema_migrations tracks all versions."""
    conn = await _test_connect()
    try:
        rows = await conn.fetch(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        )
        migrations = _discover_migrations()
        assert len(rows) == len(migrations)
        for row, (version, name, path) in zip(rows, migrations, strict=False):
            assert row["version"] == version
            assert row["name"] == name
            assert row["checksum"] == _file_checksum(path)
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_idempotent():
    """Running migrations again applies nothing new."""
    count = await migrate()
    assert count == 0


@pytest.mark.asyncio
async def test_check_mode_after_apply():
    """Check mode reports no pending migrations after full apply."""
    count = await migrate(check_only=True)
    assert count == 0


@pytest.mark.asyncio
async def test_expected_tables_exist():
    """Verify the expected tables and columns exist after migration."""
    conn = await _test_connect()
    try:
        # Check books table
        books_cols = await conn.fetch(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'books' ORDER BY ordinal_position
            """
        )
        book_col_names = [r["column_name"] for r in books_cols]
        assert "id" in book_col_names
        assert "isbn" in book_col_names
        assert "title" in book_col_names
        assert "author" in book_col_names
        assert "genre" in book_col_names
        assert "published_year" in book_col_names
        assert "total_copies" in book_col_names
        assert "available_copies" in book_col_names
        assert "created_at" in book_col_names
        assert "updated_at" in book_col_names

        # Check reservations table
        res_cols = await conn.fetch(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'reservations' ORDER BY ordinal_position
            """
        )
        res_col_names = [r["column_name"] for r in res_cols]
        assert "id" in res_col_names
        assert "book_id" in res_col_names
        assert "user_id" in res_col_names
        assert "reserved_at" in res_col_names
        assert "due_date" in res_col_names
        assert "returned_at" in res_col_names
        assert "status" in res_col_names

        # Check reservation_status enum exists
        enum_vals = await conn.fetch(
            """
            SELECT enumlabel FROM pg_enum
            JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
            WHERE pg_type.typname = 'reservation_status'
            ORDER BY enumsortorder
            """
        )
        assert [r["enumlabel"] for r in enum_vals] == ["ACTIVE", "RETURNED", "OVERDUE"]

        # Check indexes exist
        indexes = await conn.fetch(
            """
            SELECT indexname FROM pg_indexes
            WHERE tablename IN ('books', 'reservations')
            ORDER BY indexname
            """
        )
        index_names = [r["indexname"] for r in indexes]
        assert "ix_books_isbn" in index_names
        assert "ix_books_author" in index_names
        assert "ix_reservations_user_id" in index_names
        assert "ix_reservations_status" in index_names
        assert "ix_reservations_book_id" in index_names

        # Check check constraint
        constraints = await conn.fetch(
            """
            SELECT conname FROM pg_constraint
            WHERE conrelid = 'books'::regclass AND contype = 'c'
            """
        )
        constraint_names = [r["conname"] for r in constraints]
        assert "check_available_copies_non_negative" in constraint_names

    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_foreign_key_constraint():
    """Verify FK from reservations.book_id to books.id is enforced."""
    conn = await _test_connect()
    try:
        fks = await conn.fetch(
            """
            SELECT conname FROM pg_constraint
            WHERE conrelid = 'reservations'::regclass AND contype = 'f'
            """
        )
        assert len(fks) > 0, "Expected foreign key constraint on reservations"
    finally:
        await conn.close()
