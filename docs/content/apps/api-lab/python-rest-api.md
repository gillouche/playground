# Python REST API

The primary REST API implementation, built with FastAPI and following the OpenAPI specification.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | FastAPI |
| Port | 8080 |
| Path prefix | `/api/v1` |
| Source | `apps/api-lab/python-rest-api/` |

## Authentication

All endpoints except health probes require a valid JWT in the `Authorization: Bearer <token>` header. Tokens are issued by the [Auth API](python-auth-api.md) (backed by Keycloak).

**Roles:**

| Role | Access |
|------|--------|
| `admin` | Full CRUD on books, all reservations |
| `user` | Read books, create and view own reservations |

Write operations on books (create, update, delete) require the `admin` role. Reservation listing is scoped to the authenticated user unless the caller is an admin.

## Endpoints

### Books

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/books` | Any authenticated | List books with optional filters |
| GET | `/api/v1/books/{book_id}` | Any authenticated | Get a single book |
| POST | `/api/v1/books` | Admin only | Create a new book |
| PUT | `/api/v1/books/{book_id}` | Admin only | Update a book (requires `If-Match` header) |
| DELETE | `/api/v1/books/{book_id}` | Admin only | Delete a book |

**Query filters** on `GET /api/v1/books`: `available_only` (bool), `genre` (string), `author` (string), `search` (string).

### Reservations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/reservations` | Any authenticated | Create reservations (single or batch) |
| GET | `/api/v1/reservations` | Any authenticated | List reservations (scoped to own unless admin) |
| GET | `/api/v1/reservations/{id}` | Any authenticated | Get a single reservation (own or admin) |
| PATCH | `/api/v1/reservations/{id}` | Any authenticated | Return a borrowed book (own or admin) |

**Query filters** on `GET /api/v1/reservations`: `user_id`, `status`, `book_id`.

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/healthz` | Public | Liveness probe |
| GET | `/ready` | Public | Readiness probe (checks DB and Redis) |
| GET | `/info` | Public | Service metadata (version, environment, git commit) |

## Configuration

All configuration is via environment variables (Pydantic Settings):

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DATABASE` | `api_lab` | Database name |
| `POSTGRES_USER` | `api_lab` | Database user |
| `POSTGRES_PASSWORD` | `api_lab` | Database password |
| `POSTGRES_POOL_SIZE` | `20` | Connection pool size |
| `POSTGRES_MAX_OVERFLOW` | `10` | Max overflow connections beyond pool size |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | - | Redis password |
| `KEYCLOAK_SERVER_URL` | `http://localhost:8180` | Keycloak server base URL |
| `KEYCLOAK_REALM` | `api-lab` | Keycloak realm name |
| `KEYCLOAK_CLIENT_ID` | `api-lab` | Keycloak client ID for user tokens |
| `KEYCLOAK_CLIENT_SECRET` | `api-lab-secret` | Keycloak client secret |
| `CACHE_BOOKS_ALL_TTL` | `30` | TTL in seconds for book list cache |
| `CACHE_BOOK_TTL` | `60` | TTL in seconds for single book cache |
| `CACHE_INVENTORY_TTL` | `15` | TTL in seconds for inventory cache |
| `RATE_LIMIT_AUTH_LIMIT` | `10` | Max auth-tier requests per window |
| `RATE_LIMIT_AUTH_WINDOW` | `60` | Auth-tier window in seconds |
| `RATE_LIMIT_WRITE_LIMIT` | `50` | Max write-tier requests per window |
| `RATE_LIMIT_WRITE_WINDOW` | `60` | Write-tier window in seconds |
| `RATE_LIMIT_READ_LIMIT` | `200` | Max read-tier requests per window |
| `RATE_LIMIT_READ_WINDOW` | `60` | Read-tier window in seconds |
| `RATE_LIMIT_TRUSTED_PROXIES` | `10.0.0.0/8,...` | CIDR ranges for trusted proxies |
| `LOG_LEVEL` | `INFO` | Log level |
| `ENABLE_TRACING` | `false` | Enable OpenTelemetry tracing |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | - | OTLP collector endpoint |

## Error Handling

| HTTP Status | Condition |
|-------------|-----------|
| 400 | Bad request (invalid If-Match header, invalid input) |
| 401 | Missing or invalid JWT |
| 403 | Insufficient permissions (wrong role or not resource owner) |
| 404 | Resource not found |
| 409 | Duplicate ISBN or unavailable book for reservation |
| 412 | Version conflict (stale ETag on update) |
| 413 | Request body exceeds size limit (1 MB) |
| 422 | Request validation error |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

All error responses include an `error` code, `detail` message, and `request_id` for correlation.

## Security

### Security Headers

Applied to all responses via middleware:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `Cache-Control` | `no-store` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=()` |

### Body Size Limit

Requests with `Content-Length` exceeding 1 MB are rejected with 413.

### CORS

- Origins: restricted (empty allow list by default)
- Allowed headers: `Authorization`, `Content-Type`, `Idempotency-Key`, `If-Match`, `X-Request-Id`
- Exposed headers: `ETag`, `Location`, `X-Request-Id`, rate limit headers

### Input Validation

All request bodies are validated via Pydantic models with field-level constraints (min/max length, patterns, enums).

## Rate Limiting

Requests are rate-limited per client IP using Redis-backed sliding windows. Rate limit headers are included on all responses.

| Tier | Applies to | Limit | Window |
|------|-----------|-------|--------|
| auth | `/api/v1/auth/login`, `/api/v1/auth/register` | 10 | 60s |
| write | POST, PUT, PATCH, DELETE requests | 50 | 60s |
| read | GET requests | 200 | 60s |
| exempt | `/healthz`, `/ready`, `/metrics` | Unlimited | - |

Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After` (on 429).

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
- `auth_failures_total{reason}` - Counter per failure reason
- `authz_failures_total{endpoint,role}` - Counter per endpoint and role
- `rate_limit_rejections_total{endpoint,tier}` - Counter per endpoint and tier

**Logging:** Structured JSON with trace context (trace_id, span_id) via loguru.

**Tracing:** Optional OpenTelemetry with OTLP exporter, FastAPI auto-instrumentation.

## Resilience

- **Retry:** Tenacity-based exponential backoff (3 attempts, 0.5s-5s) for transient errors
- **Circuit Breaker:** Three-state FSM (closed/open/half-open) with configurable thresholds (5 failures, 30s recovery)
- **Idempotency:** Write endpoints support `Idempotency-Key` header for safe retries via Redis-backed middleware
- **Pagination:** Signed continuation tokens prevent tampering with cursor state

## Running

```bash
bazel run //apps/api-lab/python-rest-api:python-rest-api
```

## Testing

```bash
bazel test //apps/api-lab/python-rest-api:python-rest-api_unit_test
```

For the full auto-generated API reference, see [REST API Reference](api-reference/rest-api.md).
