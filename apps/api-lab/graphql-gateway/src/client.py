import logging
import uuid
from typing import Any

import httpx

logger = logging.getLogger("api-lab.graphql-gateway.client")


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

    async def list_books(
        self,
        available_only: bool = False,
        genre: str | None = None,
        author: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        client = self._ensure_client()
        params: dict[str, str] = {}
        if available_only:
            params["available_only"] = "true"
        if genre:
            params["genre"] = genre
        if author:
            params["author"] = author
        if search:
            params["search"] = search
        response = await client.get("/api/v1/books", params=params)
        response.raise_for_status()
        result: list[dict[str, Any]] = response.json()
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

    async def get_inventory(self) -> list[dict[str, Any]]:
        client = self._ensure_client()
        response = await client.get("/api/v1/inventory")
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        result: list[dict[str, Any]] = data.get("items", [])
        return result

    async def reserve_books(self, user_id: str, book_ids: list[str]) -> list[dict[str, Any]]:
        client = self._ensure_client()
        response = await client.post(
            "/api/v1/reservations",
            json={"user_id": user_id, "book_ids": book_ids},
        )
        response.raise_for_status()
        result: list[dict[str, Any]] = response.json()
        return result

    async def return_reservation(self, reservation_id: uuid.UUID) -> dict[str, Any] | None:
        client = self._ensure_client()
        response = await client.post(f"/api/v1/reservations/{reservation_id}/return")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def list_reservations(
        self,
        user_id: str | None = None,
        status: str | None = None,
        book_id: str | None = None,
    ) -> list[dict[str, Any]]:
        client = self._ensure_client()
        params: dict[str, str] = {}
        if user_id:
            params["user_id"] = user_id
        if status:
            params["status"] = status
        if book_id:
            params["book_id"] = book_id
        response = await client.get("/api/v1/reservations", params=params)
        response.raise_for_status()
        result: list[dict[str, Any]] = response.json()
        return result

    async def get_reservation(self, reservation_id: uuid.UUID) -> dict[str, Any] | None:
        client = self._ensure_client()
        response = await client.get(f"/api/v1/reservations/{reservation_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result
