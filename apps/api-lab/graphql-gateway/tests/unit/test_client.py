"""Unit tests for LibraryClient HTTP client wrapper."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from client import LibraryClient, ListBooksParams, ListReservationsParams

BOOK_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
RESERVATION_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")

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
    "user_id": str(USER_ID),
    "reserved_at": "2024-01-01T00:00:00",
    "due_date": "2024-01-15T00:00:00",
    "returned_at": None,
    "status": "ACTIVE",
}

PAGINATED_BOOKS_RESPONSE = {
    "items": [SAMPLE_BOOK],
    "continuation_token": None,
    "has_more": False,
}

PAGINATED_RESERVATIONS_RESPONSE = {
    "items": [SAMPLE_RESERVATION],
    "continuation_token": None,
    "has_more": False,
}


def _make_response(status_code: int = 200, json_data=None, headers=None) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400 and status_code != 404:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    return resp


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
        await lib.disconnect()


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


@pytest.fixture
def connected_client():
    lib = LibraryClient(base_url="http://test-api:8080")
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    lib._client = mock_http
    return lib, mock_http


class TestListBooks:
    @pytest.mark.asyncio
    async def test_list_books_no_filters(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, PAGINATED_BOOKS_RESPONSE)
        result = await lib.list_books()
        mock_http.get.assert_awaited_once_with("/api/v1/books", params={}, headers={})
        assert result["items"] == [SAMPLE_BOOK]
        assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_list_books_with_all_filters(self, connected_client):
        lib, mock_http = connected_client
        empty_paginated = {"items": [], "continuation_token": None, "has_more": False}
        mock_http.get.return_value = _make_response(200, empty_paginated)
        result = await lib.list_books(
            ListBooksParams(
                available_only=True, genre="Technology", author="Thomas", search="pragmatic"
            )
        )
        mock_http.get.assert_awaited_once_with(
            "/api/v1/books",
            params={
                "available_only": "true",
                "genre": "Technology",
                "author": "Thomas",
                "search": "pragmatic",
            },
            headers={},
        )
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_list_books_available_only(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, PAGINATED_BOOKS_RESPONSE)
        await lib.list_books(ListBooksParams(available_only=True))
        mock_http.get.assert_awaited_once_with(
            "/api/v1/books", params={"available_only": "true"}, headers={}
        )

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

    @pytest.mark.asyncio
    async def test_list_books_with_pagination_params(self, connected_client):
        lib, mock_http = connected_client
        paginated = {"items": [], "continuation_token": "next", "has_more": True}
        mock_http.get.return_value = _make_response(200, paginated)
        result = await lib.list_books(ListBooksParams(limit=10, continuation_token="prev"))
        mock_http.get.assert_awaited_once_with(
            "/api/v1/books",
            params={"limit": "10", "continuation_token": "prev"},
            headers={},
        )
        assert result["continuation_token"] == "next"
        assert result["has_more"] is True

    @pytest.mark.asyncio
    async def test_list_books_with_sorting(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, PAGINATED_BOOKS_RESPONSE)
        await lib.list_books(ListBooksParams(sort_by="title", sort_order="desc"))
        mock_http.get.assert_awaited_once_with(
            "/api/v1/books",
            params={"sort_by": "title", "sort_order": "desc"},
            headers={},
        )


class TestGetBook:
    @pytest.mark.asyncio
    async def test_get_book_found(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, SAMPLE_BOOK)
        result = await lib.get_book(BOOK_ID)
        mock_http.get.assert_awaited_once_with(f"/api/v1/books/{BOOK_ID}", headers={})
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
        mock_http.post.assert_awaited_once_with("/api/v1/books", json=data, headers={})
        assert result == SAMPLE_BOOK

    @pytest.mark.asyncio
    async def test_create_book_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.post.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.create_book({"isbn": "123"})


class TestUpdateBook:
    @pytest.mark.asyncio
    async def test_update_book_success(self, connected_client):
        lib, mock_http = connected_client
        updated = {**SAMPLE_BOOK, "title": "Updated Title"}
        mock_http.get.return_value = _make_response(200, SAMPLE_BOOK, headers={"ETag": '"1"'})
        mock_http.put.return_value = _make_response(200, updated)
        result = await lib.update_book(BOOK_ID, {"title": "Updated Title"})
        mock_http.put.assert_awaited_once_with(
            f"/api/v1/books/{BOOK_ID}",
            json={"title": "Updated Title"},
            headers={"If-Match": '"1"'},
        )
        assert result == updated

    @pytest.mark.asyncio
    async def test_update_book_not_found(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(404)
        result = await lib.update_book(BOOK_ID, {"title": "Nope"})
        assert result is None

    @pytest.mark.asyncio
    async def test_update_book_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, SAMPLE_BOOK, headers={"ETag": '"1"'})
        mock_http.put.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.update_book(BOOK_ID, {"title": "Fail"})


class TestDeleteBook:
    @pytest.mark.asyncio
    async def test_delete_book_success(self, connected_client):
        lib, mock_http = connected_client
        mock_http.delete.return_value = _make_response(204)
        result = await lib.delete_book(BOOK_ID)
        mock_http.delete.assert_awaited_once_with(f"/api/v1/books/{BOOK_ID}", headers={})
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_book_not_found_returns_false(self, connected_client):
        lib, mock_http = connected_client
        mock_http.delete.return_value = _make_response(404)
        result = await lib.delete_book(BOOK_ID)
        assert result is False


class TestReserveBooks:
    @pytest.mark.asyncio
    async def test_reserve_books_success(self, connected_client):
        lib, mock_http = connected_client
        mock_http.post.return_value = _make_response(201, [SAMPLE_RESERVATION])
        result = await lib.reserve_books(str(USER_ID), [str(BOOK_ID)])
        mock_http.post.assert_awaited_once_with(
            "/api/v1/reservations",
            json={"book_ids": [str(BOOK_ID)]},
            headers={},
        )
        assert result == [SAMPLE_RESERVATION]

    @pytest.mark.asyncio
    async def test_reserve_books_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.post.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.reserve_books(str(USER_ID), [str(BOOK_ID)])


class TestUpdateReservation:
    @pytest.mark.asyncio
    async def test_update_reservation_success(self, connected_client):
        lib, mock_http = connected_client
        returned = {
            **SAMPLE_RESERVATION,
            "status": "RETURNED",
            "returned_at": "2024-01-10T00:00:00",
        }
        mock_http.patch.return_value = _make_response(200, returned)
        result = await lib.update_reservation(RESERVATION_ID, "RETURNED")
        mock_http.patch.assert_awaited_once_with(
            f"/api/v1/reservations/{RESERVATION_ID}",
            json={"status": "RETURNED"},
            headers={},
        )
        assert result == returned

    @pytest.mark.asyncio
    async def test_update_reservation_not_found(self, connected_client):
        lib, mock_http = connected_client
        mock_http.patch.return_value = _make_response(404)
        result = await lib.update_reservation(RESERVATION_ID, "RETURNED")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_reservation_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.patch.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.update_reservation(RESERVATION_ID, "RETURNED")


class TestListReservations:
    @pytest.mark.asyncio
    async def test_list_reservations_no_filters(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, PAGINATED_RESERVATIONS_RESPONSE)
        result = await lib.list_reservations()
        mock_http.get.assert_awaited_once_with("/api/v1/reservations", params={}, headers={})
        assert result["items"] == [SAMPLE_RESERVATION]
        assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_list_reservations_with_all_filters(self, connected_client):
        lib, mock_http = connected_client
        empty_paginated = {"items": [], "continuation_token": None, "has_more": False}
        mock_http.get.return_value = _make_response(200, empty_paginated)
        result = await lib.list_reservations(
            ListReservationsParams(user_id=str(USER_ID), status="ACTIVE", book_id=str(BOOK_ID))
        )
        mock_http.get.assert_awaited_once_with(
            "/api/v1/reservations",
            params={
                "user_id": str(USER_ID),
                "status": "ACTIVE",
                "book_id": str(BOOK_ID),
            },
            headers={},
        )
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_list_reservations_server_error(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(500)
        with pytest.raises(httpx.HTTPStatusError):
            await lib.list_reservations()

    @pytest.mark.asyncio
    async def test_list_reservations_with_pagination(self, connected_client):
        lib, mock_http = connected_client
        paginated = {"items": [], "continuation_token": "next", "has_more": True}
        mock_http.get.return_value = _make_response(200, paginated)
        result = await lib.list_reservations(
            ListReservationsParams(limit=5, continuation_token="prev")
        )
        mock_http.get.assert_awaited_once_with(
            "/api/v1/reservations",
            params={"limit": "5", "continuation_token": "prev"},
            headers={},
        )
        assert result["continuation_token"] == "next"
        assert result["has_more"] is True


class TestGetReservation:
    @pytest.mark.asyncio
    async def test_get_reservation_found(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, SAMPLE_RESERVATION)
        result = await lib.get_reservation(RESERVATION_ID)
        mock_http.get.assert_awaited_once_with(f"/api/v1/reservations/{RESERVATION_ID}", headers={})
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
