# TypeScript API - Library Book Management

Skeleton TypeScript implementation of the Library Book Management API.

## Suggested Libraries

| Feature         | Library                                      |
| --------------- | -------------------------------------------- |
| HTTP Framework  | `fastify`                                    |
| PostgreSQL      | `pg` or `prisma`                             |
| Redis           | `ioredis`                                    |
| gRPC            | `@grpc/grpc-js` + `@grpc/proto-loader`       |
| GraphQL         | `apollo-server` + `@as-integrations/fastify` |
| OpenTelemetry   | `@opentelemetry/sdk-node`                    |
| Prometheus      | `prom-client`                                |
| Logging         | `pino` (built into Fastify)                  |
| Circuit Breaker | `opossum`                                    |

## Implementation Guide

1. Set up PostgreSQL connection with pg or Prisma
2. Implement Book and Reservation models/types
3. Create REST route handlers
4. Add Redis caching layer with ioredis
5. Implement gRPC server from library.proto
6. Add GraphQL schema with Apollo Server
7. Wire up OpenTelemetry tracing
8. Add Prometheus metrics
9. Implement circuit breaker with opossum
10. Add graceful shutdown handling
