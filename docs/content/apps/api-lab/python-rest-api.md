# Python REST API

The primary REST API implementation, built with FastAPI and following the OpenAPI specification.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | FastAPI |
| Port | 8080 |
| Path prefix | `/api/v1` |
| Source | `apps/api-lab/python-rest-api/` |

## Endpoints

### Books

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/books` | List books with optional filters |
| GET | `/api/v1/books/{book_id}` | Get a single book |
| POST | `/api/v1/books` | Create a new book |
| PUT | `/api/v1/books/{book_id}` | Update a book |
| DELETE | `/api/v1/books/{book_id}` | Delete a book |

**Query filters** on `GET /api/v1/books`: `available_only` (bool), `genre` (string), `author` (string), `search` (string).

### Reservations

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/reservations` | Create reservations (single or batch) |
| GET | `/api/v1/reservations` | List reservations with filters |
| GET | `/api/v1/reservations/{id}` | Get a single reservation |
| POST | `/api/v1/reservations/{id}/return` | Return a borrowed book |

**Query filters** on `GET /api/v1/reservations`: `user_id`, `status`, `book_id`.

### Inventory

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/inventory` | Get all books with available copies > 0 |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Liveness probe |
| GET | `/ready` | Readiness probe (checks DB and Redis) |
| GET | `/info` | Service metadata (version, environment, git commit) |

## Configuration

All configuration is via environment variables (Pydantic Settings):

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DATABASE` | `api_lab` | Database name |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `LOG_LEVEL` | `INFO` | Log level |
| `ENABLE_TRACING` | `false` | Enable OpenTelemetry tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | - | OTLP collector endpoint |

## Error Handling

| HTTP Status | Condition |
|-------------|-----------|
| 404 | Resource not found |
| 409 | Duplicate ISBN or unavailable book for reservation |
| 500 | Internal server error |

## Observability

**Metrics** (Prometheus, via `/metrics`):

- `books_created_total` - Counter
- `reservations_created_total` - Counter
- `reservations_returned_total` - Counter
- `cache_hits_total{operation}` - Counter per operation
- `cache_misses_total{operation}` - Counter per operation
- `db_query_duration_seconds{operation}` - Histogram
- `cache_op_duration_seconds{operation}` - Histogram
- `books_available` - Gauge (total available copies)
- `active_reservations` - Gauge

**Logging:** Structured JSON with trace context (trace_id, span_id) via loguru.

**Tracing:** Optional OpenTelemetry with OTLP exporter, FastAPI auto-instrumentation.

## Resilience

- **Retry:** Tenacity-based exponential backoff (3 attempts, 0.5s-5s) for transient errors
- **Circuit Breaker:** Three-state FSM (closed/open/half-open) with configurable thresholds (5 failures, 30s recovery)

## Running

```bash
bazel run //apps/api-lab/python-rest-api:python-rest-api
```

## Testing

```bash
bazel test //apps/api-lab/python-rest-api:python-rest-api_unit_test
```

For the full auto-generated API reference, see [REST API Reference](api-reference/rest-api.md).
