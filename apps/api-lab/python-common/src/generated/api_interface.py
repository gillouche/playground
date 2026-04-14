# Generated from openapi.yaml — DO NOT EDIT MANUALLY
# Regenerated automatically by Bazel at build time.

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid

    from generated.models import (
        Book,
        BookCreate,
        BookUpdate,
        ErrorResponse,
        HealthResponse,
        InfoResponse,
        PaginatedBooks,
        PaginatedReservations,
        Reservation,
        ReservationCreate,
        ReservationStatus,
        ReservationUpdate,
        schema,
    )


class LibraryAPI(abc.ABC):
    """Abstract interface for the Library Book Management API.

    Each method corresponds to an operationId in the OpenAPI spec.
    Implement this class and wire the methods to your framework of choice
    (FastAPI, Flask, etc.).
    """

    # ----- Books --------------------------------------------------

    @abc.abstractmethod
    async def list_books(self, *, limit: int | None = None, continuation_token: str | None = None, sort_by: str | None = None, sort_order: str | None = None, available_only: bool | None = None, genre: str | None = None, author: str | None = None, search: str | None = None) -> PaginatedBooks:
        """GET /api/v1/books  (operationId: listBooks)"""
        ...

    @abc.abstractmethod
    async def create_book(self, *, body: BookCreate) -> Book:
        """POST /api/v1/books  (operationId: createBook)"""
        ...

    @abc.abstractmethod
    async def get_book(self, *, book_id: uuid.UUID) -> Book:
        """GET /api/v1/books/{book_id}  (operationId: getBook)"""
        ...

    @abc.abstractmethod
    async def update_book(self, *, book_id: uuid.UUID, body: BookUpdate) -> Book:
        """PUT /api/v1/books/{book_id}  (operationId: updateBook)"""
        ...

    @abc.abstractmethod
    async def delete_book(self, *, book_id: uuid.UUID) -> None:
        """DELETE /api/v1/books/{book_id}  (operationId: deleteBook)"""
        ...

    # ----- Reservations -------------------------------------------

    @abc.abstractmethod
    async def list_reservations(self, *, limit: int | None = None, continuation_token: str | None = None, sort_by: str | None = None, sort_order: str | None = None, user_id: uuid.UUID | None = None, status: ReservationStatus | None = None, book_id: uuid.UUID | None = None) -> PaginatedReservations:
        """GET /api/v1/reservations  (operationId: listReservations)"""
        ...

    @abc.abstractmethod
    async def create_reservations(self, *, body: ReservationCreate) -> list[Reservation]:
        """POST /api/v1/reservations  (operationId: createReservations)"""
        ...

    @abc.abstractmethod
    async def get_reservation(self, *, reservation_id: uuid.UUID) -> Reservation:
        """GET /api/v1/reservations/{reservation_id}  (operationId: getReservation)"""
        ...

    @abc.abstractmethod
    async def update_reservation(self, *, reservation_id: uuid.UUID, body: ReservationUpdate) -> Reservation:
        """PATCH /api/v1/reservations/{reservation_id}  (operationId: updateReservation)"""
        ...

    # ----- Health / Info ------------------------------------------

    @abc.abstractmethod
    async def health_check(self) -> HealthResponse:
        """GET /healthz  (operationId: healthCheck)"""
        ...

    @abc.abstractmethod
    async def readiness_check(self) -> HealthResponse:
        """GET /ready  (operationId: readinessCheck)"""
        ...

    @abc.abstractmethod
    async def service_info(self) -> InfoResponse:
        """GET /info  (operationId: serviceInfo)"""
        ...
