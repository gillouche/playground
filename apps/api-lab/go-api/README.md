# Go API - Library Book Management

Skeleton Go implementation of the Library Book Management API.

## Suggested Libraries

| Feature         | Library                               |
| --------------- | ------------------------------------- |
| HTTP Router     | `github.com/go-chi/chi/v5`            |
| PostgreSQL      | `github.com/jackc/pgx/v5`             |
| Redis           | `github.com/redis/go-redis/v9`        |
| gRPC            | `google.golang.org/grpc`              |
| GraphQL         | `github.com/99designs/gqlgen`         |
| OpenTelemetry   | `go.opentelemetry.io/otel`            |
| Prometheus      | `github.com/prometheus/client_golang` |
| Logging         | `log/slog` (stdlib)                   |
| Circuit Breaker | `github.com/sony/gobreaker`           |

## Implementation Guide

1. Set up PostgreSQL connection pool with pgx/v5
2. Implement Book and Reservation models
3. Create REST handlers with chi router
4. Add Redis caching layer
5. Implement gRPC server from library.proto
6. Add GraphQL schema with gqlgen
7. Wire up OpenTelemetry tracing
8. Add Prometheus metrics
9. Implement circuit breaker for external calls
10. Add graceful shutdown handling
