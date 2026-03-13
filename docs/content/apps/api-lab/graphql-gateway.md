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

The GraphQL gateway does not access the database directly. It uses an HTTP client (`LibraryClient`) to forward requests to the Python REST API. This pattern allows the GraphQL layer to aggregate, reshape, and filter data for frontend consumers without duplicating business logic.

GraphiQL (interactive explorer) is enabled in non-production environments.

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

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REST_API_URL` | `http://localhost:8080` | Target REST API base URL |

## Running

```bash
bazel run //apps/api-lab/graphql-gateway:graphql-gateway
```

## Testing

```bash
bazel test //apps/api-lab/graphql-gateway:graphql-gateway_unit_test
```

For the full auto-generated API reference, see [GraphQL API Reference](api-reference/graphql-api.md).
