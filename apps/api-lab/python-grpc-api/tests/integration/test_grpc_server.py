import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from grpc import aio
from grpc_server import LibraryServiceServicer
from library.v1 import library_pb2, library_pb2_grpc
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


@pytest.fixture
def mock_book_service():
    return AsyncMock()


@pytest.fixture
async def grpc_server_and_channel(mock_book_service):
    server = aio.server()
    servicer = LibraryServiceServicer(mock_book_service)
    library_pb2_grpc.add_LibraryServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("[::]:0")
    await server.start()
    channel = aio.insecure_channel(f"localhost:{port}")
    stub = library_pb2_grpc.LibraryServiceStub(channel)
    yield stub, mock_book_service
    await channel.close()
    await server.stop(grace=0)


class TestListBooksIntegration:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.list_books.return_value = []

        resp = await stub.ListBooks(library_pb2.ListBooksRequest())

        assert isinstance(resp, library_pb2.ListBooksResponse)
        assert len(resp.books) == 0

    @pytest.mark.asyncio
    async def test_returns_books(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        book = _make_book()
        mock_svc.list_books.return_value = [book]

        resp = await stub.ListBooks(library_pb2.ListBooksRequest())

        assert len(resp.books) == 1
        assert resp.books[0].title == "The Pragmatic Programmer"
        assert resp.books[0].isbn == "978-0-13-468599-1"

    @pytest.mark.asyncio
    async def test_with_available_only_filter(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.list_books.return_value = []

        await stub.ListBooks(library_pb2.ListBooksRequest(available_only=True))

        mock_svc.list_books.assert_awaited_once_with(
            available_only=True,
            genre=None,
            author=None,
            search=None,
        )

    @pytest.mark.asyncio
    async def test_with_genre_filter(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.list_books.return_value = []

        await stub.ListBooks(library_pb2.ListBooksRequest(genre="Fiction"))

        call_kwargs = mock_svc.list_books.call_args[1]
        assert call_kwargs["genre"] == "Fiction"


class TestGetBookIntegration:
    @pytest.mark.asyncio
    async def test_found(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        book = _make_book()
        mock_svc.get_book.return_value = book

        resp = await stub.GetBook(library_pb2.GetBookRequest(book_id=str(book.id)))

        assert isinstance(resp, library_pb2.Book)
        assert resp.id == str(book.id)
        assert resp.title == book.title
        assert resp.author == book.author

    @pytest.mark.asyncio
    async def test_not_found_raises_rpc_error(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.get_book.return_value = None

        with pytest.raises(aio.AioRpcError) as exc_info:
            await stub.GetBook(library_pb2.GetBookRequest(book_id=str(uuid.uuid4())))

        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND


class TestCreateBookIntegration:
    @pytest.mark.asyncio
    async def test_creates_successfully(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        book = _make_book()
        mock_svc.create_book.return_value = book

        resp = await stub.CreateBook(
            library_pb2.CreateBookRequest(
                isbn="978-0-13-468599-1",
                title="New Book",
                author="Author",
                genre="Technology",
                published_year=2025,
                total_copies=10,
            )
        )

        assert isinstance(resp, library_pb2.Book)
        assert resp.id == str(book.id)

    @pytest.mark.asyncio
    async def test_duplicate_isbn_raises_already_exists(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.create_book.side_effect = DuplicateISBNError("978-0-13-468599-1")

        with pytest.raises(aio.AioRpcError) as exc_info:
            await stub.CreateBook(
                library_pb2.CreateBookRequest(
                    isbn="978-0-13-468599-1",
                    title="Duplicate",
                    author="Author",
                    genre="Tech",
                    published_year=2020,
                    total_copies=1,
                )
            )

        assert exc_info.value.code() == grpc.StatusCode.ALREADY_EXISTS


class TestUpdateBookIntegration:
    @pytest.mark.asyncio
    async def test_updates_title(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        book = _make_book(title="Updated Title")
        mock_svc.update_book.return_value = book

        resp = await stub.UpdateBook(
            library_pb2.UpdateBookRequest(book_id=str(uuid.uuid4()), title="Updated Title")
        )

        assert isinstance(resp, library_pb2.Book)
        assert resp.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_not_found_raises_not_found(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.update_book.return_value = None

        with pytest.raises(aio.AioRpcError) as exc_info:
            await stub.UpdateBook(
                library_pb2.UpdateBookRequest(book_id=str(uuid.uuid4()), title="X")
            )

        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_duplicate_isbn_raises_already_exists(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.update_book.side_effect = DuplicateISBNError("978-0-13-468599-1")

        with pytest.raises(aio.AioRpcError) as exc_info:
            await stub.UpdateBook(
                library_pb2.UpdateBookRequest(book_id=str(uuid.uuid4()), isbn="978-0-13-468599-1")
            )

        assert exc_info.value.code() == grpc.StatusCode.ALREADY_EXISTS


class TestDeleteBookIntegration:
    @pytest.mark.asyncio
    async def test_deletes_successfully(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.delete_book.return_value = True

        resp = await stub.DeleteBook(library_pb2.DeleteBookRequest(book_id=str(uuid.uuid4())))

        assert isinstance(resp, library_pb2.DeleteBookResponse)

    @pytest.mark.asyncio
    async def test_not_found_raises_not_found(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.delete_book.return_value = False

        with pytest.raises(aio.AioRpcError) as exc_info:
            await stub.DeleteBook(library_pb2.DeleteBookRequest(book_id=str(uuid.uuid4())))

        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND


class TestGetInventoryIntegration:
    @pytest.mark.asyncio
    async def test_returns_available_books(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        books = [_make_book(), _make_book(available_copies=1)]
        mock_svc.get_inventory.return_value = books

        resp = await stub.GetInventory(library_pb2.GetInventoryRequest())

        assert isinstance(resp, library_pb2.GetInventoryResponse)
        assert len(resp.books) == 2

    @pytest.mark.asyncio
    async def test_empty_inventory(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.get_inventory.return_value = []

        resp = await stub.GetInventory(library_pb2.GetInventoryRequest())

        assert len(resp.books) == 0


class TestReserveBooksIntegration:
    @pytest.mark.asyncio
    async def test_reserves_successfully(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        reservations = [_make_reservation()]
        mock_svc.reserve_books.return_value = reservations
        book_id = str(uuid.uuid4())

        resp = await stub.ReserveBooks(
            library_pb2.ReserveBooksRequest(user_id="user-1", book_ids=[book_id])
        )

        assert isinstance(resp, library_pb2.ReserveBooksResponse)
        assert len(resp.reservations) == 1
        assert resp.reservations[0].user_id == "user-42"
        assert resp.reservations[0].status == library_pb2.RESERVATION_STATUS_ACTIVE

    @pytest.mark.asyncio
    async def test_unavailable_book_raises_failed_precondition(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.reserve_books.side_effect = ValueError("Book not available")

        with pytest.raises(aio.AioRpcError) as exc_info:
            await stub.ReserveBooks(
                library_pb2.ReserveBooksRequest(user_id="user-1", book_ids=[str(uuid.uuid4())])
            )

        assert exc_info.value.code() == grpc.StatusCode.FAILED_PRECONDITION


class TestReturnReservationIntegration:
    @pytest.mark.asyncio
    async def test_returns_successfully(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        returned_at = datetime(2025, 3, 10, 15, 0, 0, tzinfo=UTC)
        reservation = _make_reservation(status="RETURNED", returned_at=returned_at)
        mock_svc.return_reservation.return_value = reservation

        resp = await stub.ReturnReservation(
            library_pb2.ReturnReservationRequest(reservation_id=str(uuid.uuid4()))
        )

        assert isinstance(resp, library_pb2.Reservation)
        assert resp.status == library_pb2.RESERVATION_STATUS_RETURNED
        assert resp.HasField("returned_at")

    @pytest.mark.asyncio
    async def test_not_found_raises_not_found(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.return_reservation.return_value = None

        with pytest.raises(aio.AioRpcError) as exc_info:
            await stub.ReturnReservation(
                library_pb2.ReturnReservationRequest(reservation_id=str(uuid.uuid4()))
            )

        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND

    @pytest.mark.asyncio
    async def test_already_returned_raises_failed_precondition(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.return_reservation.side_effect = ValueError("Reservation is already RETURNED")

        with pytest.raises(aio.AioRpcError) as exc_info:
            await stub.ReturnReservation(
                library_pb2.ReturnReservationRequest(reservation_id=str(uuid.uuid4()))
            )

        assert exc_info.value.code() == grpc.StatusCode.FAILED_PRECONDITION


class TestListReservationsIntegration:
    @pytest.mark.asyncio
    async def test_returns_all_reservations(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        reservations = [_make_reservation(), _make_reservation()]
        mock_svc.list_reservations.return_value = reservations

        resp = await stub.ListReservations(library_pb2.ListReservationsRequest())

        assert isinstance(resp, library_pb2.ListReservationsResponse)
        assert len(resp.reservations) == 2

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.list_reservations.return_value = []

        await stub.ListReservations(library_pb2.ListReservationsRequest(user_id="user-7"))

        call_kwargs = mock_svc.list_reservations.call_args[1]
        assert call_kwargs["user_id"] == "user-7"

    @pytest.mark.asyncio
    async def test_filters_by_status(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.list_reservations.return_value = []

        await stub.ListReservations(library_pb2.ListReservationsRequest(status="ACTIVE"))

        call_kwargs = mock_svc.list_reservations.call_args[1]
        assert call_kwargs["status"] == "ACTIVE"

    @pytest.mark.asyncio
    async def test_filters_by_book_id(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.list_reservations.return_value = []
        book_id = uuid.uuid4()

        await stub.ListReservations(library_pb2.ListReservationsRequest(book_id=str(book_id)))

        call_kwargs = mock_svc.list_reservations.call_args[1]
        assert call_kwargs["book_id"] == uuid.UUID(str(book_id))


class TestGetReservationIntegration:
    @pytest.mark.asyncio
    async def test_found(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        reservation = _make_reservation()
        mock_svc.get_reservation.return_value = reservation

        resp = await stub.GetReservation(
            library_pb2.GetReservationRequest(reservation_id=str(reservation.id))
        )

        assert isinstance(resp, library_pb2.Reservation)
        assert resp.id == str(reservation.id)
        assert resp.user_id == "user-42"

    @pytest.mark.asyncio
    async def test_not_found_raises_not_found(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.get_reservation.return_value = None

        with pytest.raises(aio.AioRpcError) as exc_info:
            await stub.GetReservation(
                library_pb2.GetReservationRequest(reservation_id=str(uuid.uuid4()))
            )

        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND
