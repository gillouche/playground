"""Database migration runner for api-lab.

Language-agnostic SQL migration tool that applies versioned SQL files
to PostgreSQL. Tracks applied migrations in a schema_migrations table.

Usage:
    python migrate.py [--check]

Options:
    --check   Validate that all migrations have been applied (exit 1 if pending).
              Useful in CI to verify the database is up-to-date.

Environment variables:
    POSTGRES_HOST      (default: localhost)
    POSTGRES_PORT      (default: 5432)
    POSTGRES_DATABASE  (default: api_lab)
    POSTGRES_USER      (default: playground)
    POSTGRES_PASSWORD  (default: playground)
"""

import asyncio
import hashlib
import os
import sys
from pathlib import Path

import asyncpg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_DATABASE = os.environ.get("POSTGRES_DATABASE", "api_lab")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "playground")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "playground")

SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT now()
);
"""


def _discover_migrations() -> list[tuple[int, str, Path]]:
    """Discover and sort migration files by version number."""
    migrations = []
    for path in sorted(MIGRATIONS_DIR.glob("V*__*.sql")):
        # Parse version from filename: V001__description.sql -> 1
        version_str = path.stem.split("__")[0]
        version = int(version_str[1:])
        migrations.append((version, path.stem, path))
    return migrations


def _file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def _get_applied(conn: asyncpg.Connection) -> dict[int, str]:
    """Return {version: checksum} for all applied migrations."""
    rows = await conn.fetch("SELECT version, checksum FROM schema_migrations ORDER BY version")
    return {row["version"]: row["checksum"] for row in rows}


async def migrate(*, check_only: bool = False) -> int:
    """Apply pending migrations. Returns number of migrations applied."""
    conn = await asyncpg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DATABASE,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )
    try:
        await conn.execute(SCHEMA_MIGRATIONS_SQL)

        applied = await _get_applied(conn)
        migrations = _discover_migrations()

        # Validate checksums of already-applied migrations
        for version, name, path in migrations:
            if version in applied:
                expected = _file_checksum(path)
                if applied[version] != expected:
                    print(
                        f"ERROR: Checksum mismatch for V{version:03d} ({name}). "
                        "Migration file was modified after being applied.",
                        file=sys.stderr,
                    )
                    sys.exit(1)

        pending = [(v, n, p) for v, n, p in migrations if v not in applied]

        if check_only:
            if pending:
                print(f"PENDING: {len(pending)} migration(s) not yet applied:")
                for version, name, _path in pending:
                    print(f"  V{version:03d}: {name}")
                return len(pending)
            print("OK: All migrations applied.")
            return 0

        if not pending:
            print("No pending migrations.")
            return 0

        for version, name, path in pending:
            sql = path.read_text()
            checksum = _file_checksum(path)
            print(f"Applying V{version:03d}: {name}...")
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version, name, checksum) VALUES ($1, $2, $3)",
                    version,
                    name,
                    checksum,
                )
            print(f"  Applied V{version:03d} successfully.")

        print(f"Applied {len(pending)} migration(s).")
        return len(pending)

    finally:
        await conn.close()


def main():
    check_only = "--check" in sys.argv
    count = asyncio.run(migrate(check_only=check_only))
    if check_only and count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
