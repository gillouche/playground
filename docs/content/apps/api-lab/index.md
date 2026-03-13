# API Lab

A library book management system implemented across multiple API protocols and languages, exploring patterns for building distributed services.

## Architecture

![API Lab Architecture](../../assets/diagrams/api-lab-architecture.svg)

## Services

| Service | Protocol | Language | Port | Status |
|---------|----------|----------|------|--------|
| [Python REST API](python-rest-api.md) | REST (OpenAPI) | Python / FastAPI | 8080 | Implemented |
| [Python gRPC API](python-grpc-api.md) | gRPC | Python / asyncio | 50051 | Implemented |
| [GraphQL Gateway](graphql-gateway.md) | GraphQL | Python / Strawberry | 8083 | Implemented |
| [Go API](go-api.md) | REST | Go / Chi | 8081 | Planned |
| [TypeScript API](ts-api.md) | REST | TypeScript / Fastify | 8082 | Planned |
| [Rust Traffic Generator](rust-traffic-generator.md) | HTTP client | Rust | - | Planned |

## Shared Components

- **[Database](database.md):** PostgreSQL with custom SQL migration system
- **BookService:** Core business logic shared by Python REST and gRPC APIs
- **Redis Cache:** TTL-based caching with pattern invalidation
- **OpenAPI Spec:** Single spec generates models for all language implementations

## Key Design Decisions

**Shared business logic:** The Python REST and gRPC APIs share a `BookService` class that encapsulates all business operations. This prevents logic duplication and ensures consistency across protocols.

**GraphQL as gateway:** The GraphQL API does not access the database directly. It proxies the REST API via HTTP, demonstrating the gateway/BFF pattern.

**Row-level locking:** Book reservations use `SELECT ... FOR UPDATE` to prevent race conditions when decrementing available copies.

**Cache invalidation:** Write operations invalidate related cache keys using Redis pattern deletion. Read operations cache with varying TTLs (30s for lists, 60s for single items, 15s for inventory).
