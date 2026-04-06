import uuid
from datetime import UTC, datetime
from enum import Enum
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from google.protobuf import timestamp_pb2
from grpc_server import (
    LibraryServiceServicer,
    _book_to_proto,
    _datetime_to_timestamp,
    _reservation_to_proto,
)
from library.v1 import library_pb2
from services.book_service import DuplicateISBNError

anyio_backend = "asyncio"


def _make_book(**overrides):
    book = MagicMock()
    book.id = overrides.get("id", uuid.uuid4())
    book.isbn = overrides.get("isbn", "978-0-13-468599-1")
    book.title = overrides.get("title", "The Pragmatic Programmer")
    book.author = overrides.get("author", "David Thomas")
    book.genre = overrides.get("genre", "Technology")
    book.published_year = overrides.get("published_year", 1999)
    book.total_copies = overrides.get("total_copies", 5)
    book.available_copies = overrides.get("available_copies", 3)
    book.created_at = overrides.get("created_at", datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC))
    book.updated_at = overrides.get("updated_at", datetime(2025, 6, 1, 0, 0, 0, tzinfo=UTC))
    return book


def _make_reservation(**overrides):
    res = MagicMock()
    res.id = overrides.get("id", uuid.uuid4())
    res.book_id = overrides.get("book_id", uuid.uuid4())
    res.user_id = overrides.get("user_id", "user-42")
    res.reserved_at = overrides.get("reserved_at", datetime(2025, 3, 1, 10, 0, 0, tzinfo=UTC))
    res.due_date = overrides.get("due_date", datetime(2025, 3, 15, 0, 0, 0, tzinfo=UTC))
    res.returned_at = overrides.get("returned_at")
    res.status = overrides.get("status", "ACTIVE")
    return res


class _AbortError(Exception):
    pass


@pytest.fixture
def mock_book_service():
    return AsyncMock()


@pytest.fixture
def servicer(mock_book_service):
    return LibraryServiceServicer(mock_book_service)


@pytest.fixture
def context():
    ctx = AsyncMock()

    async def _abort(*args, **_kwargs):
        raise _AbortError(*args)

    ctx.abort = AsyncMock(side_effect=_abort)
    return ctx


class TestDatetimeToTimestamp:
    def test_converts_utc_datetime(self):
        dt = datetime(2025, 1, 15, 12, 30, 0, tzinfo=UTC)
        ts = _datetime_to_timestamp(dt)
        assert isinstance(ts, timestamp_pb2.Timestamp)
        assert ts.seconds > 0

    def test_epoch_datetime(self):
        dt = datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)
        ts = _datetime_to_timestamp(dt)
        assert ts.seconds == 0

    def test_roundtrip_consistency(self):
        dt = datetime(2025, 6, 15, 8, 0, 0, tzinfo=UTC)
        ts = _datetime_to_timestamp(dt)
        recovered = ts.ToDatetime(tzinfo=UTC)
        assert recovered == dt


class TestBookToProto:
    def test_all_fields_mapped(self):
        book = _make_book()
        proto = _book_to_proto(book)

        assert proto.id == str(book.id)
        assert proto.isbn == book.isbn
        assert proto.title == book.title
        assert proto.author == book.author
        assert proto.genre == book.genre
        assert proto.published_year == book.published_year
        assert proto.total_copies == book.total_copies
        assert proto.available_copies == book.available_copies

    def test_timestamps_present(self):
        book = _make_book()
        proto = _book_to_proto(book)
        assert proto.HasField("created_at")
        assert proto.HasField("updated_at")

    def test_returns_library_book_type(self):
        proto = _book_to_proto(_make_book())
        assert isinstance(proto, library_pb2.Book)

    def test_id_is_string_representation(self):
        book_id = uuid.uuid4()
        book = _make_book(id=book_id)
        proto = _book_to_proto(book)
        assert proto.id == str(book_id)


class TestReservationToProto:
    def test_active_status_string(self):
        res = _make_reservation(status="ACTIVE")
        proto = _reservation_to_proto(res)
        assert proto.status == library_pb2.RESERVATION_STATUS_ACTIVE

    def test_returned_status_string(self):
        res = _make_reservation(status="RETURNED")
        proto = _reservation_to_proto(res)
        assert proto.status == library_pb2.RESERVATION_STATUS_RETURNED

    def test_overdue_status_string(self):
        res = _make_reservation(status="OVERDUE")
        proto = _reservation_to_proto(res)
        assert proto.status == library_pb2.RESERVATION_STATUS_OVERDUE

    def test_unknown_status_maps_to_unspecified(self):
        res = _make_reservation(status="UNKNOWN")
        proto = _reservation_to_proto(res)
        assert proto.status == library_pb2.RESERVATION_STATUS_UNSPECIFIED

    def test_status_as_enum_object(self):
        class _FakeStatus(str, Enum):
            ACTIVE = "ACTIVE"

        res = _make_reservation(status=_FakeStatus.ACTIVE)
        proto = _reservation_to_proto(res)
        assert proto.status == library_pb2.RESERVATION_STATUS_ACTIVE

    def test_returned_at_set_when_present(self):
        returned = datetime(2025, 3, 10, 15, 0, 0, tzinfo=UTC)
        res = _make_reservation(status="RETURNED", returned_at=returned)
        proto = _reservation_to_proto(res)
        assert proto.HasField("returned_at")

    def test_returned_at_absent_when_none(self):
        res = _make_reservation(returned_at=None)
        proto = _reservation_to_proto(res)
        assert not proto.HasField("returned_at")

    def test_all_fields_mapped(self):
        book_id = uuid.uuid4()
        res_id = uuid.uuid4()
        res = _make_reservation(id=res_id, book_id=book_id, user_id="user-99")
        proto = _reservation_to_proto(res)

        assert proto.id == str(res_id)
        assert proto.book_id == str(book_id)
        assert proto.user_id == "user-99"
        assert proto.HasField("reserved_at")
        assert proto.HasField("due_date")

    def test_returns_reservation_type(self):
        proto = _reservation_to_proto(_make_reservation())
        assert isinstance(proto, library_pb2.Reservation)


class TestListBooks:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, servicer, mock_book_service, context):
        mock_book_service.list_books.return_value = []
        req = library_pb2.ListBooksRequest()

        resp = await servicer.ListBooks(req, context)

        assert isinstance(resp, library_pb2.ListBooksResponse)
        assert len(resp.books) == 0

    @pytest.mark.asyncio
    async def test_returns_multiple_books(self, servicer, mock_book_service, context):
        books = [_make_book(), _make_book(title="Clean Code")]
        mock_book_service.list_books.return_value = books
        req = library_pb2.ListBooksRequest()

        resp = await servicer.ListBooks(req, context)

        assert len(resp.books) == 2
        assert resp.books[0].title == "The Pragmatic Programmer"
        assert resp.books[1].title == "Clean Code"

    @pytest.mark.asyncio
    async def test_passes_filters_to_service(self, servicer, mock_book_service, context):
        mock_book_service.list_books.return_value = []
        req = library_pb2.ListBooksRequest(
            available_only=True,
            genre="Fiction",
            author="Tolkien",
            search="ring",
        )

        await servicer.ListBooks(req, context)

        mock_book_service.list_books.assert_awaited_once_with(
            available_only=True,
            genre="Fiction",
            author="Tolkien",
            search="ring",
        )

    @pytest.mark.asyncio
    async def test_empty_string_filters_become_none(self, servicer, mock_book_service, context):
        mock_book_service.list_books.return_value = []
        req = library_pb2.ListBooksRequest(genre="", author="", search="")

        await servicer.ListBooks(req, context)

        mock_book_service.list_books.assert_awaited_once_with(
            available_only=False,
            genre=None,
            author=None,
            search=None,
        )


class TestGetBook:
    @pytest.mark.asyncio
    async def test_found(self, servicer, mock_book_service, context):
        book = _make_book()
        mock_book_service.get_book.return_value = book
        req = library_pb2.GetBookRequest(book_id=str(book.id))

        resp = await servicer.GetBook(req, context)

        assert isinstance(resp, library_pb2.Book)
        assert resp.id == str(book.id)
        assert resp.title == book.title
        context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_not_found_aborts_with_not_found(self, servicer, mock_book_service, context):
        mock_book_service.get_book.return_value = None
        req = library_pb2.GetBookRequest(book_id=str(uuid.uuid4()))

        with pytest.raises(_AbortError):
            await servicer.GetBook(req, context)

        context.abort.assert_awaited_once_with(grpc.StatusCode.NOT_FOUND, "Book not found")

    @pytest.mark.asyncio
    async def test_passes_uuid_to_service(self, servicer, mock_book_service, context):
        book = _make_book()
        book_id = book.id
        mock_book_service.get_book.return_value = book
        req = library_pb2.GetBookRequest(book_id=str(book_id))

        await servicer.GetBook(req, context)

        mock_book_service.get_book.assert_awaited_once_with(uuid.UUID(str(book_id)))


class TestCreateBook:
    @pytest.mark.asyncio
    async def test_creates_book_successfully(self, servicer, mock_book_service, context):
        book = _make_book()
        mock_book_service.create_book.return_value = book
        req = library_pb2.CreateBookRequest(
            isbn="978-0-13-468599-1",
            title="New Book",
            author="Author Name",
            genre="Technology",
            published_year=2025,
            total_copies=10,
        )

        resp = await servicer.CreateBook(req, context)

        assert isinstance(resp, library_pb2.Book)
        assert resp.id == str(book.id)
        context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_duplicate_isbn_aborts_with_already_exists(
        self, servicer, mock_book_service, context
    ):
        mock_book_service.create_book.side_effect = DuplicateISBNError("978-0-13-468599-1")
        req = library_pb2.CreateBookRequest(
            isbn="978-0-13-468599-1",
            title="Duplicate",
            author="Author",
            genre="Tech",
            published_year=2020,
            total_copies=1,
        )

        with pytest.raises(_AbortError):
            await servicer.CreateBook(req, context)

        context.abort.assert_awaited_once()
        call_args = context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.ALREADY_EXISTS

    @pytest.mark.asyncio
    async def test_book_create_data_passed_correctly(self, servicer, mock_book_service, context):
        book = _make_book()
        mock_book_service.create_book.return_value = book
        req = library_pb2.CreateBookRequest(
            isbn="978-0-13-468599-1",
            title="Test Book",
            author="Test Author",
            genre="Fiction",
            published_year=2024,
            total_copies=5,
        )

        await servicer.CreateBook(req, context)

        mock_book_service.create_book.assert_awaited_once()
        call_data = mock_book_service.create_book.call_args[0][0]
        assert call_data.isbn == "978-0-13-468599-1"
        assert call_data.title == "Test Book"
        assert call_data.author == "Test Author"
        assert call_data.genre == "Fiction"
        assert call_data.published_year == 2024
        assert call_data.total_copies == 5


class TestUpdateBook:
    @pytest.mark.asyncio
    async def test_updates_title_only(self, servicer, mock_book_service, context):
        updated_book = _make_book(title="Updated Title")
        mock_book_service.update_book.return_value = updated_book
        book_id = str(uuid.uuid4())
        req = library_pb2.UpdateBookRequest(book_id=book_id, title="Updated Title")

        resp = await servicer.UpdateBook(req, context)

        assert resp.title == "Updated Title"
        context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_not_found_aborts_with_not_found(self, servicer, mock_book_service, context):
        mock_book_service.update_book.return_value = None
        req = library_pb2.UpdateBookRequest(book_id=str(uuid.uuid4()), title="X")

        with pytest.raises(_AbortError):
            await servicer.UpdateBook(req, context)

        context.abort.assert_awaited_once_with(grpc.StatusCode.NOT_FOUND, "Book not found")

    @pytest.mark.asyncio
    async def test_duplicate_isbn_aborts_with_already_exists(
        self, servicer, mock_book_service, context
    ):
        mock_book_service.update_book.side_effect = DuplicateISBNError("978-0-13-468599-1")
        req = library_pb2.UpdateBookRequest(book_id=str(uuid.uuid4()), isbn="978-0-13-468599-1")

        with pytest.raises(_AbortError):
            await servicer.UpdateBook(req, context)

        call_args = context.abort.call_args
        assert call_args[0][0] == grpc.StatusCode.ALREADY_EXISTS

    @pytest.mark.asyncio
    async def test_only_set_optional_fields_included(self, servicer, mock_book_service, context):
        book = _make_book()
        mock_book_service.update_book.return_value = book
        req = library_pb2.UpdateBookRequest(book_id=str(uuid.uuid4()), title="New Title")

        await servicer.UpdateBook(req, context)

        call_data = mock_book_service.update_book.call_args[0][1]
        assert call_data.title == "New Title"
        assert call_data.isbn is None
        assert call_data.author is None

    @pytest.mark.asyncio
    async def test_multiple_optional_fields(self, servicer, mock_book_service, context):
        book = _make_book()
        mock_book_service.update_book.return_value = book
        req = library_pb2.UpdateBookRequest(
            book_id=str(uuid.uuid4()),
            title="New Title",
            author="New Author",
            total_copies=20,
        )

        await servicer.UpdateBook(req, context)

        call_data = mock_book_service.update_book.call_args[0][1]
        assert call_data.title == "New Title"
        assert call_data.author == "New Author"
        assert call_data.total_copies == 20


class TestDeleteBook:
    @pytest.mark.asyncio
    async def test_deletes_successfully(self, servicer, mock_book_service, context):
        mock_book_service.delete_book.return_value = True
        req = library_pb2.DeleteBookRequest(book_id=str(uuid.uuid4()))

        resp = await servicer.DeleteBook(req, context)

        assert isinstance(resp, library_pb2.DeleteBookResponse)
        context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_not_found_aborts_with_not_found(self, servicer, mock_book_service, context):
        mock_book_service.delete_book.return_value = False
        req = library_pb2.DeleteBookRequest(book_id=str(uuid.uuid4()))

        with pytest.raises(_AbortError):
            await servicer.DeleteBook(req, context)

        context.abort.assert_awaited_once_with(grpc.StatusCode.NOT_FOUND, "Book not found")

    @pytest.mark.asyncio
    async def test_passes_uuid_to_service(self, servicer, mock_book_service, context):
        mock_book_service.delete_book.return_value = True
        book_id = uuid.uuid4()
        req = library_pb2.DeleteBookRequest(book_id=str(book_id))

        await servicer.DeleteBook(req, context)

        mock_book_service.delete_book.assert_awaited_once_with(uuid.UUID(str(book_id)))


class TestGetInventory:
    @pytest.mark.asyncio
    async def test_returns_available_books(self, servicer, mock_book_service, context):
        books = [_make_book(), _make_book(available_copies=2)]
        mock_book_service.get_inventory.return_value = books
        req = library_pb2.GetInventoryRequest()

        resp = await servicer.GetInventory(req, context)

        assert isinstance(resp, library_pb2.GetInventoryResponse)
        assert len(resp.books) == 2

    @pytest.mark.asyncio
    async def test_empty_inventory(self, servicer, mock_book_service, context):
        mock_book_service.get_inventory.return_value = []
        req = library_pb2.GetInventoryRequest()

        resp = await servicer.GetInventory(req, context)

        assert len(resp.books) == 0
        mock_book_service.get_inventory.assert_awaited_once()


class TestReserveBooks:
    @pytest.mark.asyncio
    async def test_reserves_successfully(self, servicer, mock_book_service, context):
        reservations = [_make_reservation(), _make_reservation()]
        mock_book_service.reserve_books.return_value = reservations
        book_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        req = library_pb2.ReserveBooksRequest(user_id="user-1", book_ids=book_ids)

        resp = await servicer.ReserveBooks(req, context)

        assert isinstance(resp, library_pb2.ReserveBooksResponse)
        assert len(resp.reservations) == 2
        context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_value_error_aborts_with_failed_precondition(
        self, servicer, mock_book_service, context
    ):
        mock_book_service.reserve_books.side_effect = ValueError("Book not available")
        book_ids = [str(uuid.uuid4())]
        req = library_pb2.ReserveBooksRequest(user_id="user-1", book_ids=book_ids)

        with pytest.raises(_AbortError):
            await servicer.ReserveBooks(req, context)

        context.abort.assert_awaited_once_with(
            grpc.StatusCode.FAILED_PRECONDITION, "Book not available"
        )

    @pytest.mark.asyncio
    async def test_reservation_create_data_correct(self, servicer, mock_book_service, context):
        mock_book_service.reserve_books.return_value = []
        book_id = uuid.uuid4()
        req = library_pb2.ReserveBooksRequest(user_id="user-99", book_ids=[str(book_id)])

        await servicer.ReserveBooks(req, context)

        call_data = mock_book_service.reserve_books.call_args[0][0]
        assert call_data.user_id == "user-99"
        assert uuid.UUID(str(book_id)) in call_data.book_ids


class TestReturnReservation:
    @pytest.mark.asyncio
    async def test_returns_successfully(self, servicer, mock_book_service, context):
        returned_at = datetime(2025, 3, 10, 15, 0, 0, tzinfo=UTC)
        reservation = _make_reservation(status="RETURNED", returned_at=returned_at)
        mock_book_service.return_reservation.return_value = reservation
        req = library_pb2.ReturnReservationRequest(reservation_id=str(uuid.uuid4()))

        resp = await servicer.ReturnReservation(req, context)

        assert isinstance(resp, library_pb2.Reservation)
        assert resp.status == library_pb2.RESERVATION_STATUS_RETURNED
        assert resp.HasField("returned_at")
        context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_not_found_aborts_with_not_found(self, servicer, mock_book_service, context):
        mock_book_service.return_reservation.return_value = None
        req = library_pb2.ReturnReservationRequest(reservation_id=str(uuid.uuid4()))

        with pytest.raises(_AbortError):
            await servicer.ReturnReservation(req, context)

        context.abort.assert_awaited_once_with(grpc.StatusCode.NOT_FOUND, "Reservation not found")

    @pytest.mark.asyncio
    async def test_already_returned_aborts_with_failed_precondition(
        self, servicer, mock_book_service, context
    ):
        mock_book_service.return_reservation.side_effect = ValueError("Already returned")
        req = library_pb2.ReturnReservationRequest(reservation_id=str(uuid.uuid4()))

        with pytest.raises(_AbortError):
            await servicer.ReturnReservation(req, context)

        context.abort.assert_awaited_once_with(
            grpc.StatusCode.FAILED_PRECONDITION, "Already returned"
        )

    @pytest.mark.asyncio
    async def test_passes_uuid_to_service(self, servicer, mock_book_service, context):
        reservation = _make_reservation()
        mock_book_service.return_reservation.return_value = reservation
        res_id = uuid.uuid4()
        req = library_pb2.ReturnReservationRequest(reservation_id=str(res_id))

        await servicer.ReturnReservation(req, context)

        mock_book_service.return_reservation.assert_awaited_once_with(uuid.UUID(str(res_id)))


class TestListReservations:
    @pytest.mark.asyncio
    async def test_returns_all_when_no_filters(self, servicer, mock_book_service, context):
        reservations = [_make_reservation()]
        mock_book_service.list_reservations.return_value = reservations
        req = library_pb2.ListReservationsRequest()

        resp = await servicer.ListReservations(req, context)

        assert isinstance(resp, library_pb2.ListReservationsResponse)
        assert len(resp.reservations) == 1
        mock_book_service.list_reservations.assert_awaited_once_with(
            user_id=None,
            status=None,
            book_id=None,
        )

    @pytest.mark.asyncio
    async def test_passes_user_id_filter(self, servicer, mock_book_service, context):
        mock_book_service.list_reservations.return_value = []
        req = library_pb2.ListReservationsRequest(user_id="user-5")

        await servicer.ListReservations(req, context)

        call_kwargs = mock_book_service.list_reservations.call_args[1]
        assert call_kwargs["user_id"] == "user-5"

    @pytest.mark.asyncio
    async def test_passes_status_filter(self, servicer, mock_book_service, context):
        mock_book_service.list_reservations.return_value = []
        req = library_pb2.ListReservationsRequest(status="ACTIVE")

        await servicer.ListReservations(req, context)

        call_kwargs = mock_book_service.list_reservations.call_args[1]
        assert call_kwargs["status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_passes_book_id_filter(self, servicer, mock_book_service, context):
        mock_book_service.list_reservations.return_value = []
        book_id = uuid.uuid4()
        req = library_pb2.ListReservationsRequest(book_id=str(book_id))

        await servicer.ListReservations(req, context)

        call_kwargs = mock_book_service.list_reservations.call_args[1]
        assert call_kwargs["book_id"] == uuid.UUID(str(book_id))

    @pytest.mark.asyncio
    async def test_empty_book_id_becomes_none(self, servicer, mock_book_service, context):
        mock_book_service.list_reservations.return_value = []
        req = library_pb2.ListReservationsRequest(user_id="user-1")

        await servicer.ListReservations(req, context)

        call_kwargs = mock_book_service.list_reservations.call_args[1]
        assert call_kwargs["book_id"] is None

    @pytest.mark.asyncio
    async def test_empty_strings_become_none(self, servicer, mock_book_service, context):
        mock_book_service.list_reservations.return_value = []
        req = library_pb2.ListReservationsRequest(user_id="", status="", book_id="")

        await servicer.ListReservations(req, context)

        mock_book_service.list_reservations.assert_awaited_once_with(
            user_id=None,
            status=None,
            book_id=None,
        )


class TestGetReservation:
    @pytest.mark.asyncio
    async def test_found(self, servicer, mock_book_service, context):
        reservation = _make_reservation()
        mock_book_service.get_reservation.return_value = reservation
        req = library_pb2.GetReservationRequest(reservation_id=str(reservation.id))

        resp = await servicer.GetReservation(req, context)

        assert isinstance(resp, library_pb2.Reservation)
        assert resp.id == str(reservation.id)
        context.abort.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_not_found_aborts_with_not_found(self, servicer, mock_book_service, context):
        mock_book_service.get_reservation.return_value = None
        req = library_pb2.GetReservationRequest(reservation_id=str(uuid.uuid4()))

        with pytest.raises(_AbortError):
            await servicer.GetReservation(req, context)

        context.abort.assert_awaited_once_with(grpc.StatusCode.NOT_FOUND, "Reservation not found")

    @pytest.mark.asyncio
    async def test_passes_uuid_to_service(self, servicer, mock_book_service, context):
        reservation = _make_reservation()
        mock_book_service.get_reservation.return_value = reservation
        res_id = uuid.uuid4()
        req = library_pb2.GetReservationRequest(reservation_id=str(res_id))

        await servicer.GetReservation(req, context)

        mock_book_service.get_reservation.assert_awaited_once_with(uuid.UUID(str(res_id)))
