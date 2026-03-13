# Python gRPC API

A gRPC server implementing the same library service as the REST API, using asyncio and JSON serialization.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | grpc.aio (asyncio) |
| Port | 50051 |
| Service | `library.v1.LibraryService` |
| Source | `apps/api-lab/python-grpc-api/` |

## RPC Methods

| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `ListBooks` | `ListBooksRequest` | `ListBooksResponse` | List with filters |
| `GetBook` | `GetBookRequest` | `BookResponse` | Single book |
| `CreateBook` | `CreateBookRequest` | `BookResponse` | Create new book |
| `UpdateBook` | `UpdateBookRequest` | `BookResponse` | Partial update |
| `DeleteBook` | `DeleteBookRequest` | `Empty` | Delete book |
| `GetInventory` | `Empty` | `InventoryResponse` | Available books |
| `ReserveBooks` | `ReserveBooksRequest` | `ReserveBooksResponse` | Create reservations |
| `ReturnReservation` | `ReturnReservationRequest` | `ReservationResponse` | Return borrowed book |
| `ListReservations` | `ListReservationsRequest` | `ListReservationsResponse` | List with filters |
| `GetReservation` | `GetReservationRequest` | `ReservationResponse` | Single reservation |

## Implementation Details

The gRPC server uses a `GenericRpcHandler` with JSON serialization rather than generated protobuf stubs. Request and response bodies are JSON-encoded, allowing the same `BookService` business logic layer to be shared with the REST API.

gRPC reflection is enabled for service discovery.

## Error Handling

| gRPC Status | Condition |
|-------------|-----------|
| `NOT_FOUND` | Resource does not exist |
| `FAILED_PRECONDITION` | Business rule violation (e.g., unavailable book) |
| `INTERNAL` | Unexpected server error |

## Configuration

Same environment variables as the REST API (shared `Config` class from python-common).

The gRPC port is controlled by `GRPC_PORT` (default: `50051`).

## Running

```bash
bazel run //apps/api-lab/python-grpc-api:python-grpc-api
```

## Testing

```bash
bazel test //apps/api-lab/python-grpc-api:python-grpc-api_unit_test
```

For the full auto-generated API reference, see [gRPC API Reference](api-reference/grpc-api.md).
