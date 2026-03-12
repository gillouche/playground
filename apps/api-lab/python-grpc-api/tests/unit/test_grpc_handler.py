"""Unit tests for LibraryServiceHandler gRPC handler."""

import json
import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from grpc_server import SERVICE_NAME, LibraryServiceHandler

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_book(**overrides):
    """Create a mock book with sensible defaults."""
    book = MagicMock()
    book.id = overrides.get("id", uuid.uuid4())
    book.isbn = overrides.get("isbn", "978-0-13-468599-1")
    book.title = overrides.get("title", "The Pragmatic Programmer")
    book.author = overrides.get("author", "David Thomas")
    book.genre = overrides.get("genre", "Technology")
    book.published_year = overrides.get("published_year", 1999)
    book.total_copies = overrides.get("total_copies", 5)
    book.available_copies = overrides.get("available_copies", 3)
    book.created_at = overrides.get("created_at", datetime(2025, 1, 1, 0, 0, 0))
    book.updated_at = overrides.get("updated_at", datetime(2025, 6, 1, 0, 0, 0))
    return book


def _make_reservation(**overrides):
    """Create a mock reservation with sensible defaults."""
    res = MagicMock()
    res.id = overrides.get("id", uuid.uuid4())
    res.book_id = overrides.get("book_id", uuid.uuid4())
    res.user_id = overrides.get("user_id", "user-42")
    res.reserved_at = overrides.get("reserved_at", datetime(2025, 3, 1, 10, 0, 0))
    res.due_date = overrides.get("due_date", date(2025, 3, 15))
    res.returned_at = overrides.get("returned_at")
    res.status = overrides.get("status", "active")
    return res


@pytest.fixture
def book_service():
    return AsyncMock()


@pytest.fixture
def handler(book_service):
    return LibraryServiceHandler(book_service)


class _AbortError(Exception):
    """Simulates gRPC abort behavior (raises to stop handler execution)."""


@pytest.fixture
def context():
    ctx = AsyncMock()

    async def _abort(*args, **_kwargs):
        raise _AbortError(*args)

    ctx.abort = AsyncMock(side_effect=_abort)
    return ctx


def _req(data: dict) -> bytes:
    """Serialize a dict to JSON bytes (simulating a gRPC request)."""
    return json.dumps(data).encode("utf-8")


# ---------------------------------------------------------------------------
# Static helpers
# ---------------------------------------------------------------------------


class TestSerialize:
    def test_serialize_dict(self):
        result = LibraryServiceHandler._serialize({"key": "value"})
        assert isinstance(result, bytes)
        assert json.loads(result) == {"key": "value"}

    def test_serialize_with_uuid(self):
        uid = uuid.uuid4()
        result = LibraryServiceHandler._serialize({"id": uid})
        parsed = json.loads(result)
        assert parsed["id"] == str(uid)

    def test_serialize_with_datetime(self):
        dt = datetime(2025, 1, 1, 12, 0, 0)
        result = LibraryServiceHandler._serialize({"ts": dt})
        parsed = json.loads(result)
        assert parsed["ts"] == str(dt)

    def test_serialize_list(self):
        result = LibraryServiceHandler._serialize([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]


class TestDeserialize:
    def test_deserialize_dict(self):
        data = json.dumps({"a": 1}).encode("utf-8")
        assert LibraryServiceHandler._deserialize(data) == {"a": 1}

    def test_deserialize_empty_bytes(self):
        assert LibraryServiceHandler._deserialize(b"") == {}

    def test_deserialize_none(self):
        assert LibraryServiceHandler._deserialize(None) == {}

    def test_deserialize_nested(self):
        data = json.dumps({"a": {"b": [1, 2]}}).encode("utf-8")
        result = LibraryServiceHandler._deserialize(data)
        assert result == {"a": {"b": [1, 2]}}


class TestBookToDict:
    def test_basic(self):
        book = _make_book()
        result = LibraryServiceHandler._book_to_dict(book)
        assert result["id"] == str(book.id)
        assert result["isbn"] == book.isbn
        assert result["title"] == book.title
        assert result["author"] == book.author
        assert result["genre"] == book.genre
        assert result["published_year"] == book.published_year
        assert result["total_copies"] == book.total_copies
        assert result["available_copies"] == book.available_copies
        assert result["created_at"] == str(book.created_at)
        assert result["updated_at"] == str(book.updated_at)


class TestReservationToDict:
    def test_active_reservation(self):
        res = _make_reservation(status="active", returned_at=None)
        result = LibraryServiceHandler._reservation_to_dict(res)
        assert result["id"] == str(res.id)
        assert result["book_id"] == str(res.book_id)
        assert result["user_id"] == "user-42"
        assert result["returned_at"] is None
        assert result["status"] == "active"

    def test_returned_reservation(self):
        returned_at = datetime(2025, 3, 10, 15, 0, 0)
        res = _make_reservation(status="returned", returned_at=returned_at)
        result = LibraryServiceHandler._reservation_to_dict(res)
        assert result["returned_at"] == str(returned_at)
        assert result["status"] == "returned"

    def test_status_as_enum(self):
        """When status is an enum-like object with a .value attribute."""
        status_enum = MagicMock()
        status_enum.value = "active"
        # Make isinstance(..., str) return False for the mock
        res = _make_reservation(status=status_enum)
        result = LibraryServiceHandler._reservation_to_dict(res)
        assert result["status"] == "active"


# ---------------------------------------------------------------------------
# Service routing
# ---------------------------------------------------------------------------


class TestServiceRouting:
    def test_all_methods_registered(self, handler):
        expected = [
            "ListBooks",
            "GetBook",
            "CreateBook",
            "UpdateBook",
            "DeleteBook",
            "GetInventory",
            "ReserveBooks",
            "ReturnReservation",
            "ListReservations",
            "GetReservation",
        ]
        for method in expected:
            details = MagicMock()
            details.method = f"/{SERVICE_NAME}/{method}"
            assert handler.service(details) is not None, f"Missing handler for {method}"

    def test_unknown_method_returns_none(self, handler):
        details = MagicMock()
        details.method = "/library.v1.LibraryService/NonExistent"
        assert handler.service(details) is None

    def test_empty_method_returns_none(self, handler):
        details = MagicMock()
        details.method = ""
        assert handler.service(details) is None


# ---------------------------------------------------------------------------
# RPC methods - Books
# ---------------------------------------------------------------------------


class TestListBooks:
    @pytest.mark.asyncio
    async def test_returns_books(self, handler, book_service, context):
        books = [_make_book(), _make_book(title="Clean Code")]
        book_service.list_books.return_value = books

        result = await handler._list_books(b"", context)
        parsed = json.loads(result)

        assert len(parsed["books"]) == 2
        book_service.list_books.assert_awaited_once_with(
            available_only=False,
            genre=None,
            author=None,
            search=None,
        )

    @pytest.mark.asyncio
    async def test_with_filters(self, handler, book_service, context):
        book_service.list_books.return_value = []
        req = _req(
            {"available_only": True, "genre": "Fiction", "author": "Tolkien", "search": "ring"}
        )

        result = await handler._list_books(req, context)
        parsed = json.loads(result)

        assert parsed["books"] == []
        book_service.list_books.assert_awaited_once_with(
            available_only=True,
            genre="Fiction",
            author="Tolkien",
            search="ring",
        )

    @pytest.mark.asyncio
    async def test_empty_list(self, handler, book_service, context):
        book_service.list_books.return_value = []
        result = await handler._list_books(b"", context)
        assert json.loads(result) == {"books": []}


class TestGetBook:
    @pytest.mark.asyncio
    async def test_found(self, handler, book_service, context):
        book = _make_book()
        book_service.get_book.return_value = book

        result = await handler._get_book(_req({"book_id": str(book.id)}), context)
        parsed = json.loads(result)

        assert parsed["id"] == str(book.id)
        assert parsed["title"] == book.title
        context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_not_found(self, handler, book_service, context):
        book_service.get_book.return_value = None
        book_id = str(uuid.uuid4())

        with pytest.raises(_AbortError):
            await handler._get_book(_req({"book_id": book_id}), context)
        context.abort.assert_awaited_once_with(grpc.StatusCode.NOT_FOUND, "Book not found")


class TestCreateBook:
    @pytest.mark.asyncio
    async def test_create(self, handler, book_service, context):
        book = _make_book()
        book_service.create_book.return_value = book

        req = _req(
            {
                "isbn": "978-0-13-468599-1",
                "title": "New Book",
                "author": "Author",
                "genre": "Tech",
                "published_year": 2025,
                "total_copies": 10,
            }
        )
        result = await handler._create_book(req, context)
        parsed = json.loads(result)

        assert parsed["id"] == str(book.id)
        book_service.create_book.assert_awaited_once()
        call_arg = book_service.create_book.call_args[0][0]
        assert call_arg.isbn == "978-0-13-468599-1"
        assert call_arg.title == "New Book"
        assert call_arg.total_copies == 10


class TestUpdateBook:
    @pytest.mark.asyncio
    async def test_update_found(self, handler, book_service, context):
        book = _make_book(title="Updated Title")
        book_service.update_book.return_value = book
        book_id = str(uuid.uuid4())

        req = _req({"book_id": book_id, "title": "Updated Title"})
        result = await handler._update_book(req, context)
        parsed = json.loads(result)

        assert parsed["title"] == "Updated Title"
        context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_not_found(self, handler, book_service, context):
        book_service.update_book.return_value = None
        book_id = str(uuid.uuid4())

        with pytest.raises(_AbortError):
            await handler._update_book(_req({"book_id": book_id, "title": "X"}), context)
        context.abort.assert_awaited_once_with(grpc.StatusCode.NOT_FOUND, "Book not found")

    @pytest.mark.asyncio
    async def test_update_filters_none_values(self, handler, book_service, context):
        book = _make_book()
        book_service.update_book.return_value = book
        book_id = str(uuid.uuid4())

        req = _req({"book_id": book_id, "title": "New", "author": None})
        await handler._update_book(req, context)

        call_args = book_service.update_book.call_args
        update_data = call_args[0][1]
        # None values should be filtered out
        assert not hasattr(update_data, "author") or update_data.author is None


class TestDeleteBook:
    @pytest.mark.asyncio
    async def test_delete_success(self, handler, book_service, context):
        book_service.delete_book.return_value = True
        book_id = str(uuid.uuid4())

        result = await handler._delete_book(_req({"book_id": book_id}), context)
        parsed = json.loads(result)

        assert parsed["deleted"] is True
        context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, handler, book_service, context):
        book_service.delete_book.return_value = False
        book_id = str(uuid.uuid4())

        with pytest.raises(_AbortError):
            await handler._delete_book(_req({"book_id": book_id}), context)
        context.abort.assert_awaited_once_with(grpc.StatusCode.NOT_FOUND, "Book not found")


class TestGetInventory:
    @pytest.mark.asyncio
    async def test_returns_all_books(self, handler, book_service, context):
        books = [_make_book(), _make_book(available_copies=0)]
        book_service.get_inventory.return_value = books

        result = await handler._get_inventory(b"", context)
        parsed = json.loads(result)

        assert len(parsed["books"]) == 2
        book_service.get_inventory.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_inventory(self, handler, book_service, context):
        book_service.get_inventory.return_value = []
        result = await handler._get_inventory(b"", context)
        assert json.loads(result) == {"books": []}


# ---------------------------------------------------------------------------
# RPC methods - Reservations
# ---------------------------------------------------------------------------


class TestReserveBooks:
    @pytest.mark.asyncio
    async def test_reserve_success(self, handler, book_service, context):
        reservations = [_make_reservation(), _make_reservation()]
        book_service.reserve_books.return_value = reservations

        book_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        req = _req({"user_id": "user-1", "book_ids": book_ids})
        result = await handler._reserve_books(req, context)
        parsed = json.loads(result)

        assert len(parsed["reservations"]) == 2
        context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_reserve_unavailable(self, handler, book_service, context):
        book_service.reserve_books.side_effect = ValueError("Book not available")

        book_ids = [str(uuid.uuid4())]
        req = _req({"user_id": "user-1", "book_ids": book_ids})
        with pytest.raises(_AbortError):
            await handler._reserve_books(req, context)

        context.abort.assert_awaited_once_with(
            grpc.StatusCode.FAILED_PRECONDITION, "Book not available"
        )


class TestReturnReservation:
    @pytest.mark.asyncio
    async def test_return_success(self, handler, book_service, context):
        reservation = _make_reservation(
            status="returned",
            returned_at=datetime(2025, 3, 10, 15, 0, 0),
        )
        book_service.return_reservation.return_value = reservation
        res_id = str(uuid.uuid4())

        result = await handler._return_reservation(_req({"reservation_id": res_id}), context)
        parsed = json.loads(result)

        assert parsed["status"] == "returned"
        assert parsed["returned_at"] is not None
        context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_return_not_found(self, handler, book_service, context):
        book_service.return_reservation.return_value = None
        res_id = str(uuid.uuid4())

        with pytest.raises(_AbortError):
            await handler._return_reservation(_req({"reservation_id": res_id}), context)
        context.abort.assert_awaited_once_with(grpc.StatusCode.NOT_FOUND, "Reservation not found")

    @pytest.mark.asyncio
    async def test_return_already_returned(self, handler, book_service, context):
        book_service.return_reservation.side_effect = ValueError("Already returned")
        res_id = str(uuid.uuid4())

        with pytest.raises(_AbortError):
            await handler._return_reservation(_req({"reservation_id": res_id}), context)
        context.abort.assert_awaited_once_with(
            grpc.StatusCode.FAILED_PRECONDITION, "Already returned"
        )


class TestListReservations:
    @pytest.mark.asyncio
    async def test_list_all(self, handler, book_service, context):
        reservations = [_make_reservation()]
        book_service.list_reservations.return_value = reservations

        result = await handler._list_reservations(b"", context)
        parsed = json.loads(result)

        assert len(parsed["reservations"]) == 1
        book_service.list_reservations.assert_awaited_once_with(
            user_id=None,
            status=None,
            book_id=None,
        )

    @pytest.mark.asyncio
    async def test_list_with_filters(self, handler, book_service, context):
        book_service.list_reservations.return_value = []
        book_id = str(uuid.uuid4())

        req = _req({"user_id": "user-1", "status": "active", "book_id": book_id})
        result = await handler._list_reservations(req, context)
        parsed = json.loads(result)

        assert parsed["reservations"] == []
        call_kwargs = book_service.list_reservations.call_args[1]
        assert call_kwargs["user_id"] == "user-1"
        assert call_kwargs["status"] == "active"
        assert call_kwargs["book_id"] == uuid.UUID(book_id)

    @pytest.mark.asyncio
    async def test_list_without_book_id(self, handler, book_service, context):
        book_service.list_reservations.return_value = []

        req = _req({"user_id": "user-1"})
        await handler._list_reservations(req, context)

        call_kwargs = book_service.list_reservations.call_args[1]
        assert call_kwargs["book_id"] is None


class TestGetReservation:
    @pytest.mark.asyncio
    async def test_found(self, handler, book_service, context):
        reservation = _make_reservation()
        book_service.get_reservation.return_value = reservation
        res_id = str(reservation.id)

        result = await handler._get_reservation(_req({"reservation_id": res_id}), context)
        parsed = json.loads(result)

        assert parsed["id"] == str(reservation.id)
        context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_not_found(self, handler, book_service, context):
        book_service.get_reservation.return_value = None
        res_id = str(uuid.uuid4())

        with pytest.raises(_AbortError):
            await handler._get_reservation(_req({"reservation_id": res_id}), context)
        context.abort.assert_awaited_once_with(grpc.StatusCode.NOT_FOUND, "Reservation not found")
