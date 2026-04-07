import logging
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger("api-lab.graphql-gateway.client")


@dataclass
class ListBooksParams:
    available_only: bool = False
    genre: str | None = None
    author: str | None = None
    search: str | None = None
    limit: int | None = None
    continuation_token: str | None = None
    sort_by: str | None = None
    sort_order: str | None = None

    def to_query(self) -> dict[str, str]:
        params: dict[str, str] = {}
        if self.available_only:
            params["available_only"] = "true"
        if self.genre:
            params["genre"] = self.genre
        if self.author:
            params["author"] = self.author
        if self.search:
            params["search"] = self.search
        if self.limit is not None:
            params["limit"] = str(self.limit)
        if self.continuation_token:
            params["continuation_token"] = self.continuation_token
        if self.sort_by:
            params["sort_by"] = self.sort_by
        if self.sort_order:
            params["sort_order"] = self.sort_order
        return params


@dataclass
class ListReservationsParams:
    user_id: str | None = None
    status: str | None = None
    book_id: str | None = None
    limit: int | None = None
    continuation_token: str | None = None
    sort_by: str | None = None
    sort_order: str | None = None

    def to_query(self) -> dict[str, str]:
        params: dict[str, str] = {}
        if self.user_id:
            params["user_id"] = self.user_id
        if self.status:
            params["status"] = self.status
        if self.book_id:
            params["book_id"] = self.book_id
        if self.limit is not None:
            params["limit"] = str(self.limit)
        if self.continuation_token:
            params["continuation_token"] = self.continuation_token
        if self.sort_by:
            params["sort_by"] = self.sort_by
        if self.sort_order:
            params["sort_order"] = self.sort_order
        return params


class LibraryClient:
    """HTTP client for the Library REST API."""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self._base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=10.0)
        logger.info("Connected to REST API at %s", self._base_url)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            logger.info("Disconnected from REST API")

    def _ensure_client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self._client

    async def list_books(self, params: ListBooksParams | None = None) -> dict[str, Any]:
        client = self._ensure_client()
        if params is None:
            params = ListBooksParams()
        response = await client.get("/api/v1/books", params=params.to_query())
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def get_book(self, book_id: uuid.UUID) -> dict[str, Any] | None:
        client = self._ensure_client()
        response = await client.get(f"/api/v1/books/{book_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def create_book(self, data: dict[str, Any]) -> dict[str, Any]:
        client = self._ensure_client()
        response = await client.post("/api/v1/books", json=data)
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def update_book(self, book_id: uuid.UUID, data: dict[str, Any]) -> dict[str, Any] | None:
        client = self._ensure_client()
        response = await client.put(f"/api/v1/books/{book_id}", json=data)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def delete_book(self, book_id: uuid.UUID) -> bool:
        client = self._ensure_client()
        response = await client.delete(f"/api/v1/books/{book_id}")
        return bool(response.status_code == 204)

    async def reserve_books(self, user_id: str, book_ids: list[str]) -> list[dict[str, Any]]:
        client = self._ensure_client()
        response = await client.post(
            "/api/v1/reservations",
            json={"user_id": user_id, "book_ids": book_ids},
        )
        response.raise_for_status()
        result: list[dict[str, Any]] = response.json()
        return result

    async def update_reservation(
        self, reservation_id: uuid.UUID, status: str
    ) -> dict[str, Any] | None:
        client = self._ensure_client()
        response = await client.patch(
            f"/api/v1/reservations/{reservation_id}",
            json={"status": status},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def list_reservations(
        self, params: ListReservationsParams | None = None
    ) -> dict[str, Any]:
        client = self._ensure_client()
        if params is None:
            params = ListReservationsParams()
        response = await client.get("/api/v1/reservations", params=params.to_query())
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def get_reservation(self, reservation_id: uuid.UUID) -> dict[str, Any] | None:
        client = self._ensure_client()
        response = await client.get(f"/api/v1/reservations/{reservation_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result
