# GraphQL Gateway

A GraphQL API that proxies the REST API, built with Strawberry and FastAPI. Demonstrates the gateway/BFF (Backend for Frontend) pattern.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | Strawberry + FastAPI |
| Port | 8083 |
| Endpoint | `/graphql` |
| Source | `apps/api-lab/graphql-gateway/` |

## Architecture

The GraphQL gateway does not access the database directly. It uses an HTTP client (`LibraryClient`) to forward requests to the Python REST API.
This pattern allows the GraphQL layer to aggregate, reshape, and filter data for frontend consumers without duplicating business logic.

GraphiQL (interactive explorer) is enabled in non-production environments.

## Authentication

The gateway forwards the `Authorization` header from incoming GraphQL requests to the REST API.
Authentication and authorization are enforced by the REST API, not the gateway itself.
Clients must include a valid JWT in the `Authorization: Bearer <token>` header.

## Queries

| Query | Arguments | Returns |
|-------|-----------|---------|
| `books` | `available_only`, `genre`, `author`, `search` | `[BookType]` |
| `book` | `book_id` | `BookType` |
| `inventory` | - | `[BookType]` |
| `reservations` | `user_id`, `status`, `book_id` | `[ReservationType]` |
| `reservation` | `reservation_id` | `ReservationType` |

## Mutations

| Mutation | Arguments | Returns |
|----------|-----------|---------|
| `create_book` | `isbn`, `title`, `author`, `genre`, `published_year`, `total_copies` | `BookType` |
| `update_book` | `book_id`, optional fields | `BookType` |
| `delete_book` | `book_id` | `Boolean` |
| `reserve_books` | `user_id`, `book_ids` | `[ReservationType]` |
| `return_reservation` | `reservation_id` | `ReservationType` |

## Security

### Query Depth Limit

Maximum query depth is **10**. Deeply nested queries are rejected during validation.

### Query Complexity Limit

Maximum query complexity is **1000**. List fields cost 10 points, scalar fields cost 1 point. Queries exceeding the limit are rejected with a validation error.

### Introspection

Introspection is **disabled in production** (`ENVIRONMENT=prod`). In other environments, introspection and GraphiQL are available.

### Security Headers

Same security headers as the REST API are applied via shared middleware (X-Content-Type-Options, X-Frame-Options, Cache-Control, Referrer-Policy, Permissions-Policy).

### Body Size Limit

Request bodies exceeding 1 MB are rejected with 413.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REST_API_URL` | `http://localhost:8080` | Target REST API base URL |
| `ENVIRONMENT` | `dev` | Environment name (`prod` disables introspection) |
| `GATEWAY_HTTP_TIMEOUT` | `10` | HTTP timeout for REST API requests (seconds) |

## Running

```bash
bazel run //apps/api-lab/graphql-gateway:graphql-gateway
```

## Testing

```bash
bazel test //apps/api-lab/graphql-gateway:graphql-gateway_unit_test
```

For the full auto-generated API reference, see [GraphQL API Reference](api-reference/graphql-api.md).
