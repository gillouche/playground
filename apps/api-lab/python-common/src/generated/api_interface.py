# Generated from openapi.yaml - DO NOT EDIT MANUALLY
# Run: ./apps/api-lab/openapi/generate.sh python

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uuid

    from generated.models import (
        BookCreate,
        BookResponse,
        BookUpdate,
        HealthResponse,
        InfoResponse,
        InventoryResponse,
        ReservationCreate,
        ReservationResponse,
    )


class LibraryAPI(abc.ABC):
    """Abstract interface for the Library Book Management API.

    Each method corresponds to an operationId in the OpenAPI spec.
    Implement this class and wire the methods to your framework of choice
    (FastAPI, Flask, etc.).
    """

    # ----- Books ----------------------------------------------------------

    @abc.abstractmethod
    async def list_books(
        self,
        *,
        available_only: bool | None = None,
        genre: str | None = None,
        author: str | None = None,
        search: str | None = None,
    ) -> list[BookResponse]:
        """GET /api/v1/books  (operationId: listBooks)"""
        ...

    @abc.abstractmethod
    async def create_book(self, *, body: BookCreate) -> BookResponse:
        """POST /api/v1/books  (operationId: createBook)"""
        ...

    @abc.abstractmethod
    async def get_book(self, *, book_id: uuid.UUID) -> BookResponse:
        """GET /api/v1/books/{book_id}  (operationId: getBook)"""
        ...

    @abc.abstractmethod
    async def update_book(self, *, book_id: uuid.UUID, body: BookUpdate) -> BookResponse:
        """PUT /api/v1/books/{book_id}  (operationId: updateBook)"""
        ...

    @abc.abstractmethod
    async def delete_book(self, *, book_id: uuid.UUID) -> None:
        """DELETE /api/v1/books/{book_id}  (operationId: deleteBook)"""
        ...

    # ----- Inventory ------------------------------------------------------

    @abc.abstractmethod
    async def get_inventory(self) -> InventoryResponse:
        """GET /api/v1/inventory  (operationId: getInventory)"""
        ...

    # ----- Reservations ---------------------------------------------------

    @abc.abstractmethod
    async def create_reservations(self, *, body: ReservationCreate) -> list[ReservationResponse]:
        """POST /api/v1/reservations  (operationId: createReservations)"""
        ...

    @abc.abstractmethod
    async def list_reservations(
        self,
        *,
        user_id: str | None = None,
        status: str | None = None,
        book_id: str | None = None,
    ) -> list[ReservationResponse]:
        """GET /api/v1/reservations  (operationId: listReservations)"""
        ...

    @abc.abstractmethod
    async def get_reservation(self, *, id: uuid.UUID) -> ReservationResponse:
        """GET /api/v1/reservations/{id}  (operationId: getReservation)"""
        ...

    @abc.abstractmethod
    async def return_reservation(self, *, id: uuid.UUID) -> ReservationResponse:
        """POST /api/v1/reservations/{id}/return  (operationId: returnReservation)"""
        ...

    # ----- Health / Info --------------------------------------------------

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
