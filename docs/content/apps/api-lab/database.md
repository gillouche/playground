# Database

PostgreSQL database with a custom SQL-based migration system.

## Schema

### books

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | Primary key, auto-generated |
| `isbn` | VARCHAR(13) | Unique, not null |
| `title` | TEXT | Not null |
| `author` | TEXT | Not null |
| `genre` | VARCHAR(100) | Not null |
| `published_year` | INTEGER | Not null |
| `total_copies` | INTEGER | Not null |
| `available_copies` | INTEGER | Not null, >= 0 |
| `created_at` | TIMESTAMPTZ | Default: now() |
| `updated_at` | TIMESTAMPTZ | Default: now() |

Indexes: `isbn`, `author`

### reservations

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | Primary key, auto-generated |
| `book_id` | UUID | Foreign key to books.id |
| `user_id` | VARCHAR(255) | Not null |
| `reserved_at` | TIMESTAMPTZ | Default: now() |
| `due_date` | TIMESTAMPTZ | Not null |
| `returned_at` | TIMESTAMPTZ | Nullable |
| `status` | reservation_status | Default: ACTIVE |

Indexes: `user_id`, `status`, `book_id`

`reservation_status` enum: `ACTIVE`, `RETURNED`, `OVERDUE`

### schema_migrations

Used internally by the migration runner to track applied migrations with checksum validation.

## Migration System

The migration runner (`database/migrate.py`) applies SQL files from `database/migrations/` in order. Migrations follow the naming convention `V{version:03d}__{description}.sql`.

Features:

- Tracks applied migrations with SHA-256 checksums
- Prevents modification of already-applied migrations
- Supports `--check` mode for CI (exits 1 if pending migrations exist)
- Uses asyncpg for direct PostgreSQL connections

### Running Migrations

```bash
python apps/api-lab/database/migrate.py
```

Verify all migrations are applied:

```bash
python apps/api-lab/database/migrate.py --check
```

### Creating a New Migration

Add a SQL file to `apps/api-lab/database/migrations/`:

```
V002__add_categories_table.sql
```

The version number must be sequential. The migration runner will apply it on the next run.

## Connection Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_DATABASE` | `api_lab` | Database name |
| `POSTGRES_USER` | `postgres` | Username |
| `POSTGRES_PASSWORD` | `postgres` | Password |

## SQLAlchemy ORM

The Python services use SQLAlchemy with async support (`asyncpg` driver). Models are defined in `python-common/src/database/models.py`. Connection pooling is configured with `pool_size=5` and `max_overflow=10`.
