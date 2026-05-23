# API Lab

A library book management system implemented across multiple API protocols and languages, exploring patterns for building distributed services.

## Architecture

![API Lab Architecture](../../assets/diagrams/api-lab-architecture.svg)

## Services

This branch covers the Python stack only. Go and TypeScript REST implementations are out of scope and will land in follow-up branches.

| Service | Protocol | Language | Port | Status |
|---------|----------|----------|------|--------|
| [Python REST API](python-rest-api.md) | REST (OpenAPI) | Python / FastAPI | 8080 | Implemented |
| [Python gRPC API](python-grpc-api.md) | gRPC | Python / asyncio | 50051 | Implemented |
| [GraphQL Gateway](graphql-gateway.md) | GraphQL | Python / Strawberry | 8083 | Implemented |
| [Python Auth API](python-auth-api.md) | REST | Python / FastAPI | 8084 | Implemented |
| [Rust Traffic Generator](rust-traffic-generator.md) | HTTP client | Rust | - | Planned |

## Authentication & Authorization

All API services are secured via **Keycloak** as the identity provider. The [Python Auth API](python-auth-api.md) handles user registration, login, and token management.

**JWT-based authentication:** Services validate JWTs issued by Keycloak. The `Authorization: Bearer <token>` header is required on all non-health endpoints.
The shared `auth` module (in python-common) provides JWT validation, role extraction, and FastAPI dependency injection.

**RBAC:** Two roles govern access:

| Role | Permissions |
|------|-------------|
| `admin` | Full CRUD on books, all reservations, user management |
| `user` | Read books, create/view own reservations |

## Security

All Python services apply a common set of security hardening:

- **Rate limiting** per IP with tiered windows (auth, write, read) backed by Redis. Configurable `RATE_LIMIT_FAIL_OPEN` flips between fail-open (default for dev) and fail-closed (503 when Redis is unreachable).
- **Idempotency** for POST endpoints via `Idempotency-Key` header, response cache capped at `IDEMPOTENCY_MAX_BODY_BYTES` (1 MiB default).
- **Security headers** on all responses (X-Content-Type-Options, X-Frame-Options, Cache-Control, Referrer-Policy, Permissions-Policy).
- **Request body size limit** (1 MB default) to prevent payload abuse.
- **Input validation** via Pydantic models with field constraints.
- **CORS** restricted to explicit origins, configurable via `CORS_ALLOWED_ORIGINS`.
- **OWASP compliance** across authentication, authorization, and input handling.
- **gRPC reflection** is enabled only for `local`/`sandbox`/`dev`; disabled for `test`/`prod` to avoid schema enumeration.
- **gRPC idempotency** is enforced via Redis-backed response caching keyed on `idempotency_key`.

## Shared Components

- **[Database](database.md):** PostgreSQL with custom SQL migration system
- **BookService:** Core business logic shared by Python REST and gRPC APIs
- **Redis Cache:** TTL-based caching with pattern invalidation
- **Auth module:** JWT validation, RBAC permissions, and authenticated user model (python-common)
- **OpenAPI Spec:** Single spec generates models for all language implementations

## Key Design Decisions

**Shared business logic:** The Python REST and gRPC APIs share a `BookService` class that encapsulates all business operations. This prevents logic duplication and ensures consistency across protocols.

**GraphQL as gateway:** The GraphQL API does not access the database directly. It proxies the REST API via HTTP, demonstrating the gateway/BFF pattern.

**Row-level locking:** Book reservations use `SELECT ... FOR UPDATE` to prevent race conditions when decrementing available copies.

**Cache invalidation:** Write operations invalidate related cache keys using Redis pattern deletion. Read operations cache with varying TTLs (30s for lists, 60s for single items, 15s for inventory).
