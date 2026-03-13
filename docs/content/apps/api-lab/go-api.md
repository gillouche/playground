# Go API

!!! info "Planned"
    This service is scaffolded but not yet implemented. The generated server stubs return 501 Not Implemented for all endpoints.

REST API implementation in Go, targeting the same OpenAPI specification as the Python REST API.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | Chi router (planned) |
| Port | 8081 |
| Source | `apps/api-lab/go-api/` |

## Current State

- HTTP server with signal handling
- Generated models and server stubs from OpenAPI spec
- All endpoints return 501 Not Implemented

## Suggested Libraries

| Purpose | Library |
|---------|---------|
| HTTP Router | `go-chi/chi/v5` |
| PostgreSQL | `jackc/pgx/v5` |
| Redis | `redis/go-redis/v9` |
| gRPC | `google.golang.org/grpc` |
| GraphQL | `99designs/gqlgen` |
| Observability | `go.opentelemetry.io/otel` |
| Metrics | `prometheus/client_golang` |
| Logging | `log/slog` (stdlib) |
| Circuit Breaker | `sony/gobreaker` |

## Getting Started with Implementation

1. Implement the `BookService` interface with pgx for database access
2. Wire up Chi router handlers to call the service
3. Add Redis caching layer
4. Add Prometheus metrics and OpenTelemetry tracing
5. Write table-driven unit tests
6. Add integration tests with real PostgreSQL
