import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from generated.models import PaginatedBooks, PaginatedReservations
from grpc import aio
from grpc_server import LibraryServiceServicer
from library.v1 import library_pb2, library_pb2_grpc
from services.book_service import ActiveReservationsError, DuplicateISBNError, StaleVersionError

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
    book.version = overrides.get("version", 1)
    book.created_at = overrides.get("created_at", datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC))
    book.updated_at = overrides.get("updated_at", datetime(2025, 6, 1, 0, 0, 0, tzinfo=UTC))
    return book


def _make_reservation(**overrides):
    res = MagicMock()
    res.id = overrides.get("id", uuid.uuid4())
    res.book_id = overrides.get("book_id", uuid.uuid4())
    res.user_id = overrides.get("user_id", uuid.uuid4())
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
        mock_svc.list_books.return_value = PaginatedBooks(
            items=[], continuation_token=None, has_more=False
        )

        resp = await stub.ListBooks(library_pb2.ListBooksRequest())

        assert isinstance(resp, library_pb2.ListBooksResponse)
        assert len(resp.books) == 0

    @pytest.mark.asyncio
    async def test_returns_books(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        book = _make_book()
        mock_svc.list_books.return_value = PaginatedBooks(
            items=[book], continuation_token=None, has_more=False
        )

        resp = await stub.ListBooks(library_pb2.ListBooksRequest())

        assert len(resp.books) == 1
        assert resp.books[0].title == "The Pragmatic Programmer"
        assert resp.books[0].isbn == "978-0-13-468599-1"

    @pytest.mark.asyncio
    async def test_with_available_only_filter(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.list_books.return_value = PaginatedBooks(
            items=[], continuation_token=None, has_more=False
        )

        await stub.ListBooks(library_pb2.ListBooksRequest(available_only=True))

        mock_svc.list_books.assert_awaited_once()
        query = mock_svc.list_books.call_args[0][0]
        assert query.available_only is True

    @pytest.mark.asyncio
    async def test_with_genre_filter(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.list_books.return_value = PaginatedBooks(
            items=[], continuation_token=None, has_more=False
        )

        await stub.ListBooks(library_pb2.ListBooksRequest(genre="Fiction"))

        query = mock_svc.list_books.call_args[0][0]
        assert query.genre == "Fiction"

    @pytest.mark.asyncio
    async def test_with_pagination_params(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.list_books.return_value = PaginatedBooks(
            items=[], continuation_token="next_token", has_more=True
        )

        resp = await stub.ListBooks(
            library_pb2.ListBooksRequest(page_size=5, page_token="prev_token")
        )

        assert resp.next_page_token == "next_token"
        query = mock_svc.list_books.call_args[0][0]
        assert query.limit == 5
        assert query.continuation_token == "prev_token"


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

    @pytest.mark.asyncio
    async def test_version_mismatch_raises_aborted(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.update_book.side_effect = StaleVersionError("Version mismatch")

        with pytest.raises(aio.AioRpcError) as exc_info:
            await stub.UpdateBook(
                library_pb2.UpdateBookRequest(
                    book_id=str(uuid.uuid4()),
                    title="Stale",
                    expected_version=1,
                )
            )

        assert exc_info.value.code() == grpc.StatusCode.ABORTED

    @pytest.mark.asyncio
    async def test_with_field_mask(self, grpc_server_and_channel):
        from google.protobuf import field_mask_pb2

        stub, mock_svc = grpc_server_and_channel
        book = _make_book(title="Masked Title", author="Masked Author")
        mock_svc.update_book.return_value = book

        resp = await stub.UpdateBook(
            library_pb2.UpdateBookRequest(
                book_id=str(uuid.uuid4()),
                title="Masked Title",
                author="Masked Author",
                genre="Should be ignored",
                update_mask=field_mask_pb2.FieldMask(paths=["title", "author"]),
            )
        )

        assert resp.title == "Masked Title"
        call_args = mock_svc.update_book.call_args[0]
        update_data = call_args[1]
        assert update_data.title == "Masked Title"
        assert update_data.author == "Masked Author"
        assert update_data.genre is None


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

    @pytest.mark.asyncio
    async def test_active_reservations_raises_failed_precondition(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.delete_book.side_effect = ActiveReservationsError()

        with pytest.raises(aio.AioRpcError) as exc_info:
            await stub.DeleteBook(library_pb2.DeleteBookRequest(book_id=str(uuid.uuid4())))

        assert exc_info.value.code() == grpc.StatusCode.FAILED_PRECONDITION


class TestReserveBooksIntegration:
    @pytest.mark.asyncio
    async def test_reserves_successfully(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        reservations = [_make_reservation()]
        mock_svc.reserve_books.return_value = reservations
        book_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        resp = await stub.ReserveBooks(
            library_pb2.ReserveBooksRequest(user_id=user_id, book_ids=[book_id])
        )

        assert isinstance(resp, library_pb2.ReserveBooksResponse)
        assert len(resp.reservations) == 1
        assert resp.reservations[0].status == library_pb2.RESERVATION_STATUS_ACTIVE

    @pytest.mark.asyncio
    async def test_unavailable_book_raises_failed_precondition(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.reserve_books.side_effect = ValueError("Book not available")

        with pytest.raises(aio.AioRpcError) as exc_info:
            await stub.ReserveBooks(
                library_pb2.ReserveBooksRequest(
                    user_id=str(uuid.uuid4()), book_ids=[str(uuid.uuid4())]
                )
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
        mock_svc.list_reservations.return_value = PaginatedReservations(
            items=reservations, continuation_token=None, has_more=False
        )

        resp = await stub.ListReservations(library_pb2.ListReservationsRequest())

        assert isinstance(resp, library_pb2.ListReservationsResponse)
        assert len(resp.reservations) == 2

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.list_reservations.return_value = PaginatedReservations(
            items=[], continuation_token=None, has_more=False
        )
        user_id = str(uuid.uuid4())

        await stub.ListReservations(library_pb2.ListReservationsRequest(user_id=user_id))

        query = mock_svc.list_reservations.call_args[0][0]
        assert query.user_id == uuid.UUID(user_id)

    @pytest.mark.asyncio
    async def test_filters_by_status(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.list_reservations.return_value = PaginatedReservations(
            items=[], continuation_token=None, has_more=False
        )

        await stub.ListReservations(
            library_pb2.ListReservationsRequest(
                status=library_pb2.RESERVATION_STATUS_ACTIVE,
            )
        )

        query = mock_svc.list_reservations.call_args[0][0]
        assert query.status == "ACTIVE"

    @pytest.mark.asyncio
    async def test_filters_by_book_id(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.list_reservations.return_value = PaginatedReservations(
            items=[], continuation_token=None, has_more=False
        )
        book_id = uuid.uuid4()

        await stub.ListReservations(library_pb2.ListReservationsRequest(book_id=str(book_id)))

        query = mock_svc.list_reservations.call_args[0][0]
        assert query.book_id == uuid.UUID(str(book_id))

    @pytest.mark.asyncio
    async def test_with_pagination_params(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.list_reservations.return_value = PaginatedReservations(
            items=[], continuation_token="next_page", has_more=True
        )

        resp = await stub.ListReservations(
            library_pb2.ListReservationsRequest(page_size=10, page_token="prev_page")
        )

        assert resp.next_page_token == "next_page"
        query = mock_svc.list_reservations.call_args[0][0]
        assert query.limit == 10
        assert query.continuation_token == "prev_page"


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

    @pytest.mark.asyncio
    async def test_not_found_raises_not_found(self, grpc_server_and_channel):
        stub, mock_svc = grpc_server_and_channel
        mock_svc.get_reservation.return_value = None

        with pytest.raises(aio.AioRpcError) as exc_info:
            await stub.GetReservation(
                library_pb2.GetReservationRequest(reservation_id=str(uuid.uuid4()))
            )

        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND
