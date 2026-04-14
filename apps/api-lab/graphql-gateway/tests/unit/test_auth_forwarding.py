import uuid
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from client import LibraryClient

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

PAGINATED_BOOKS_RESPONSE = {
    "items": [SAMPLE_BOOK],
    "continuation_token": None,
    "has_more": False,
}


def _make_response(status_code: int = 200, json_data=None, headers=None) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture
def connected_client():
    lib = LibraryClient(base_url="http://test-api:8080")
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    lib._client = mock_http
    return lib, mock_http


class TestBuildHeaders:
    def test_returns_empty_when_none(self):
        lib = LibraryClient()
        assert lib._build_headers(None) == {}

    def test_returns_empty_when_empty_dict(self):
        lib = LibraryClient()
        assert lib._build_headers({}) == {}

    def test_extracts_authorization_lowercase(self):
        lib = LibraryClient()
        result = lib._build_headers({"authorization": "Bearer abc123"})
        assert result == {"Authorization": "Bearer abc123"}

    def test_extracts_authorization_titlecase(self):
        lib = LibraryClient()
        result = lib._build_headers({"Authorization": "Bearer xyz789"})
        assert result == {"Authorization": "Bearer xyz789"}

    def test_ignores_non_auth_headers(self):
        lib = LibraryClient()
        result = lib._build_headers(
            {"authorization": "Bearer token", "content-type": "application/json"}
        )
        assert result == {"Authorization": "Bearer token"}

    def test_returns_empty_when_no_auth_header(self):
        lib = LibraryClient()
        result = lib._build_headers({"content-type": "application/json"})
        assert result == {}


class TestAuthHeaderForwarding:
    @pytest.mark.asyncio
    async def test_list_books_forwards_auth(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, PAGINATED_BOOKS_RESPONSE)
        headers = {"authorization": "Bearer test-token"}

        await lib.list_books(headers=headers)

        call_kwargs = mock_http.get.call_args
        assert call_kwargs.kwargs["headers"] == {"Authorization": "Bearer test-token"}

    @pytest.mark.asyncio
    async def test_list_books_no_headers(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, PAGINATED_BOOKS_RESPONSE)

        await lib.list_books()

        call_kwargs = mock_http.get.call_args
        assert call_kwargs.kwargs["headers"] == {}

    @pytest.mark.asyncio
    async def test_get_book_forwards_auth(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, SAMPLE_BOOK)
        headers = {"authorization": "Bearer get-token"}

        await lib.get_book(BOOK_ID, headers=headers)

        call_kwargs = mock_http.get.call_args
        assert call_kwargs.kwargs["headers"] == {"Authorization": "Bearer get-token"}

    @pytest.mark.asyncio
    async def test_create_book_forwards_auth(self, connected_client):
        lib, mock_http = connected_client
        mock_http.post.return_value = _make_response(201, SAMPLE_BOOK)
        headers = {"authorization": "Bearer create-token"}

        await lib.create_book({"isbn": "123"}, headers=headers)

        call_kwargs = mock_http.post.call_args
        assert call_kwargs.kwargs["headers"] == {"Authorization": "Bearer create-token"}

    @pytest.mark.asyncio
    async def test_update_book_forwards_auth(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, SAMPLE_BOOK, headers={"ETag": '"1"'})
        mock_http.put.return_value = _make_response(200, SAMPLE_BOOK)
        headers = {"authorization": "Bearer update-token"}

        await lib.update_book(BOOK_ID, {"title": "New"}, headers=headers)

        call_kwargs = mock_http.put.call_args
        assert call_kwargs.kwargs["headers"] == {
            "Authorization": "Bearer update-token",
            "If-Match": '"1"',
        }

    @pytest.mark.asyncio
    async def test_delete_book_forwards_auth(self, connected_client):
        lib, mock_http = connected_client
        mock_http.delete.return_value = _make_response(204)
        headers = {"authorization": "Bearer delete-token"}

        await lib.delete_book(BOOK_ID, headers=headers)

        call_kwargs = mock_http.delete.call_args
        assert call_kwargs.kwargs["headers"] == {"Authorization": "Bearer delete-token"}

    @pytest.mark.asyncio
    async def test_reserve_books_forwards_auth(self, connected_client):
        lib, mock_http = connected_client
        mock_http.post.return_value = _make_response(201, [])
        headers = {"authorization": "Bearer reserve-token"}

        await lib.reserve_books(str(USER_ID), [str(BOOK_ID)], headers=headers)

        call_kwargs = mock_http.post.call_args
        assert call_kwargs.kwargs["headers"] == {"Authorization": "Bearer reserve-token"}

    @pytest.mark.asyncio
    async def test_update_reservation_forwards_auth(self, connected_client):
        lib, mock_http = connected_client
        mock_http.patch.return_value = _make_response(200, {"status": "RETURNED"})
        headers = {"authorization": "Bearer return-token"}

        await lib.update_reservation(RESERVATION_ID, "RETURNED", headers=headers)

        call_kwargs = mock_http.patch.call_args
        assert call_kwargs.kwargs["headers"] == {"Authorization": "Bearer return-token"}

    @pytest.mark.asyncio
    async def test_list_reservations_forwards_auth(self, connected_client):
        lib, mock_http = connected_client
        paginated = {"items": [], "continuation_token": None, "has_more": False}
        mock_http.get.return_value = _make_response(200, paginated)
        headers = {"authorization": "Bearer list-token"}

        await lib.list_reservations(headers=headers)

        call_kwargs = mock_http.get.call_args
        assert call_kwargs.kwargs["headers"] == {"Authorization": "Bearer list-token"}

    @pytest.mark.asyncio
    async def test_get_reservation_forwards_auth(self, connected_client):
        lib, mock_http = connected_client
        mock_http.get.return_value = _make_response(200, {"id": str(RESERVATION_ID)})
        headers = {"authorization": "Bearer get-res-token"}

        await lib.get_reservation(RESERVATION_ID, headers=headers)

        call_kwargs = mock_http.get.call_args
        assert call_kwargs.kwargs["headers"] == {"Authorization": "Bearer get-res-token"}
