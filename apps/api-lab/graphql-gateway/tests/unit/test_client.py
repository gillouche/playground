"""Unit tests for LibraryClient HTTP client wrapper."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from client import LibraryClient

BOOK_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
RESERVATION_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")

SAMPLE_BOOK = {
    "id": str(BOOK_ID),
    "isbn": "978-0-13-468599-1",
    "title": "The Pragmatic Programmer",
    "author": "David Thomas",
    "genre": "Technology",
    "published_year": 1999,
    "total_copies": 5,
    "available_copies": 3,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
}

SAMPLE_RESERVATION = {
    "id": str(RESERVATION_ID),
    "book_id": str(BOOK_ID),
    "user_id": "user-1",
    "reserved_at": "2024-01-01T00:00:00",
    "due_date": "2024-01-15T00:00:00",
    "returned_at": None,
    "status": "active",
}


def _make_response(status_code: int = 200, json_data=None) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400 and status_code != 404:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    return resp


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestLibraryClientInit:
    def test_default_base_url(self):
        client = LibraryClient()
        assert client._base_url == "http://localhost:8080"

    def test_custom_base_url_strips_trailing_slash(self):
        client = LibraryClient(base_url="http://example.com:9090/")
        assert client._base_url == "http://example.com:9090"

    def test_client_initially_none(self):
        client = LibraryClient()
        assert client._client is None


# ---------------------------------------------------------------------------
# Connect / Disconnect lifecycle
# ---------------------------------------------------------------------------


class TestConnectDisconnect:
    @pytest.mark.asyncio
    async def test_connect_creates_async_client(self):
        lib = LibraryClient()
        await lib.connect()
        assert lib._client is not None
        assert isinstance(lib._client, httpx.AsyncClient)
        await lib.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_closes_client(self):
        lib = LibraryClient()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        lib._client = mock_client
        await lib.disconnect()
        mock_client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected_is_noop(self):
        lib = LibraryClient()
        # Should not raise
        await lib.disconnect()


# ---------------------------------------------------------------------------
# _ensure_client
# ---------------------------------------------------------------------------


class TestEnsureClient:
    def test_raises_when_not_connected(self):
        lib = LibraryClient()
        with pytest.raises(RuntimeError, match="Client not connected"):
            lib._ensure_client()

    @pytest.mark.asyncio
    async def test_returns_client_when_connected(self):
        lib = LibraryClient()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        lib._client = mock_client
        assert lib._ensure_client() is mock_client


# ---------------------------------------------------------------------------
# Helper: create a connected LibraryClient with mocked httpx.AsyncClient
# ---------------------------------------------------------------------------


@pytest.fixture
def connected_client():
    """Return a LibraryClient whose internal httpx client is an AsyncMock."""
    lib = LibraryClient(base_url="http://test-api:8080")
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    lib._client = mock_http
    return lib, mock_http


# ---------------------------------------------------------------------------
# list_books
# ---------------------------------------------------------------------------


class TestListBooks:
    @pytest.mark.asyncio
    async def test_list_books_no_filters(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, [SAMPLE_BOOK])
        result = await lib.list_books()
        mock_http.get.assert_awaited_once_with("/api/v1/books", params={})
        assert result == [SAMPLE_BOOK]

    @pytest.mark.asyncio
    async def test_list_books_with_all_filters(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, [])
        result = await lib.list_books(
            available_only=True, genre="Technology", author="Thomas", search="pragmatic"
        )
        mock_http.get.assert_awaited_once_with(
            "/api/v1/books",
            params={
                "available_only": "true",
                "genre": "Technology",
                "author": "Thomas",
                "search": "pragmatic",
            },
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_list_books_available_only(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, [SAMPLE_BOOK])
        await lib.list_books(available_only=True)
        mock_http.get.assert_awaited_once_with("/api/v1/books", params={"available_only": "true"})

    @pytest.mark.asyncio
    async def test_list_books_raises_on_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.list_books()

    @pytest.mark.asyncio
    async def test_list_books_not_connected(self):
        lib = LibraryClient()
        with pytest.raises(RuntimeError, match="Client not connected"):
            await lib.list_books()


# ---------------------------------------------------------------------------
# get_book
# ---------------------------------------------------------------------------


class TestGetBook:
    @pytest.mark.asyncio
    async def test_get_book_found(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, SAMPLE_BOOK)
        result = await lib.get_book(BOOK_ID)
        mock_http.get.assert_awaited_once_with(f"/api/v1/books/{BOOK_ID}")
        assert result == SAMPLE_BOOK

    @pytest.mark.asyncio
    async def test_get_book_not_found(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(404)
        result = await lib.get_book(BOOK_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_book_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.get_book(BOOK_ID)


# ---------------------------------------------------------------------------
# create_book
# ---------------------------------------------------------------------------


class TestCreateBook:
    @pytest.mark.asyncio
    async def test_create_book_success(self, connected_client):
        lib, mock_http = connected_client
        mock_http.post.return_value = _make_response(201, SAMPLE_BOOK)
        data = {
            "isbn": "978-0-13-468599-1",
            "title": "The Pragmatic Programmer",
            "author": "David Thomas",
            "genre": "Technology",
            "published_year": 1999,
            "total_copies": 5,
        }
        result = await lib.create_book(data)
        mock_http.post.assert_awaited_once_with("/api/v1/books", json=data)
        assert result == SAMPLE_BOOK

    @pytest.mark.asyncio
    async def test_create_book_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.post.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.create_book({"isbn": "123"})


# ---------------------------------------------------------------------------
# update_book
# ---------------------------------------------------------------------------


class TestUpdateBook:
    @pytest.mark.asyncio
    async def test_update_book_success(self, connected_client):
        lib, mock_http = connected_client
        updated = {**SAMPLE_BOOK, "title": "Updated Title"}
        mock_http.put.return_value = _make_response(200, updated)
        result = await lib.update_book(BOOK_ID, {"title": "Updated Title"})
        mock_http.put.assert_awaited_once_with(
            f"/api/v1/books/{BOOK_ID}", json={"title": "Updated Title"}
        )
        assert result == updated

    @pytest.mark.asyncio
    async def test_update_book_not_found(self, connected_client):
        lib, mock_http = connected_client
        mock_http.put.return_value = _make_response(404)
        result = await lib.update_book(BOOK_ID, {"title": "Nope"})
        assert result is None

    @pytest.mark.asyncio
    async def test_update_book_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.put.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.update_book(BOOK_ID, {"title": "Fail"})


# ---------------------------------------------------------------------------
# delete_book
# ---------------------------------------------------------------------------


class TestDeleteBook:
    @pytest.mark.asyncio
    async def test_delete_book_success(self, connected_client):
        lib, mock_http = connected_client
        mock_http.delete.return_value = _make_response(204)
        result = await lib.delete_book(BOOK_ID)
        mock_http.delete.assert_awaited_once_with(f"/api/v1/books/{BOOK_ID}")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_book_not_found_returns_false(self, connected_client):
        lib, mock_http = connected_client
        mock_http.delete.return_value = _make_response(404)
        result = await lib.delete_book(BOOK_ID)
        assert result is False


# ---------------------------------------------------------------------------
# get_inventory
# ---------------------------------------------------------------------------


class TestGetInventory:
    @pytest.mark.asyncio
    async def test_get_inventory_success(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, {"items": [SAMPLE_BOOK]})
        result = await lib.get_inventory()
        mock_http.get.assert_awaited_once_with("/api/v1/inventory")
        assert result == [SAMPLE_BOOK]

    @pytest.mark.asyncio
    async def test_get_inventory_empty_items(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, {"items": []})
        result = await lib.get_inventory()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_inventory_missing_items_key(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, {})
        result = await lib.get_inventory()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_inventory_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.get_inventory()


# ---------------------------------------------------------------------------
# reserve_books
# ---------------------------------------------------------------------------


class TestReserveBooks:
    @pytest.mark.asyncio
    async def test_reserve_books_success(self, connected_client):
        lib, mock_http = connected_client
        mock_http.post.return_value = _make_response(201, [SAMPLE_RESERVATION])
        result = await lib.reserve_books("user-1", [str(BOOK_ID)])
        mock_http.post.assert_awaited_once_with(
            "/api/v1/reservations",
            json={"user_id": "user-1", "book_ids": [str(BOOK_ID)]},
        )
        assert result == [SAMPLE_RESERVATION]

    @pytest.mark.asyncio
    async def test_reserve_books_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.post.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.reserve_books("user-1", [str(BOOK_ID)])


# ---------------------------------------------------------------------------
# Return reservation
# ---------------------------------------------------------------------------


class TestReturnReservation:
    @pytest.mark.asyncio
    async def test_return_reservation_success(self, connected_client):
        lib, mock_http = connected_client
        returned = {
            **SAMPLE_RESERVATION,
            "status": "returned",
            "returned_at": "2024-01-10T00:00:00",
        }
        mock_http.post.return_value = _make_response(200, returned)
        result = await lib.return_reservation(RESERVATION_ID)
        mock_http.post.assert_awaited_once_with(f"/api/v1/reservations/{RESERVATION_ID}/return")
        assert result == returned

    @pytest.mark.asyncio
    async def test_return_reservation_not_found(self, connected_client):
        lib, mock_http = connected_client
        mock_http.post.return_value = _make_response(404)
        result = await lib.return_reservation(RESERVATION_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_return_reservation_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.post.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.return_reservation(RESERVATION_ID)


# ---------------------------------------------------------------------------
# list_reservations
# ---------------------------------------------------------------------------


class TestListReservations:
    @pytest.mark.asyncio
    async def test_list_reservations_no_filters(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, [SAMPLE_RESERVATION])
        result = await lib.list_reservations()
        mock_http.get.assert_awaited_once_with("/api/v1/reservations", params={})
        assert result == [SAMPLE_RESERVATION]

    @pytest.mark.asyncio
    async def test_list_reservations_with_all_filters(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, [])
        result = await lib.list_reservations(
            user_id="user-1", status="active", book_id=str(BOOK_ID)
        )
        mock_http.get.assert_awaited_once_with(
            "/api/v1/reservations",
            params={
                "user_id": "user-1",
                "status": "active",
                "book_id": str(BOOK_ID),
            },
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_list_reservations_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.list_reservations()


# ---------------------------------------------------------------------------
# get_reservation
# ---------------------------------------------------------------------------


class TestGetReservation:
    @pytest.mark.asyncio
    async def test_get_reservation_found(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, SAMPLE_RESERVATION)
        result = await lib.get_reservation(RESERVATION_ID)
        mock_http.get.assert_awaited_once_with(f"/api/v1/reservations/{RESERVATION_ID}")
        assert result == SAMPLE_RESERVATION

    @pytest.mark.asyncio
    async def test_get_reservation_not_found(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(404)
        result = await lib.get_reservation(RESERVATION_ID)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_reservation_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.get_reservation(RESERVATION_ID)
