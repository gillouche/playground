"""System tests for gRPC LibraryService."""

import uuid

import grpc
import pytest
from library.v1 import library_pb2


@pytest.mark.asyncio
async def test_list_books_empty(grpc_stub):
    response = await grpc_stub.ListBooks(library_pb2.ListBooksRequest())
    assert len(response.books) == 0


@pytest.mark.asyncio
async def test_create_and_get_book(grpc_stub):
    created = await grpc_stub.CreateBook(
        library_pb2.CreateBookRequest(
            isbn="9780000600001",
            title="gRPC Book",
            author="gRPC Author",
            genre="Technology",
            published_year=2024,
            total_copies=5,
        )
    )
    assert created.isbn == "9780000600001"
    assert created.title == "gRPC Book"
    assert created.available_copies == 5

    fetched = await grpc_stub.GetBook(library_pb2.GetBookRequest(book_id=created.id))
    assert fetched.id == created.id
    assert fetched.title == "gRPC Book"


@pytest.mark.asyncio
async def test_list_books_with_data(grpc_stub):
    await grpc_stub.CreateBook(
        library_pb2.CreateBookRequest(
            isbn="9780000600011",
            title="Book One",
            author="Author",
            genre="Fiction",
            published_year=2024,
            total_copies=1,
        )
    )
    await grpc_stub.CreateBook(
        library_pb2.CreateBookRequest(
            isbn="9780000600012",
            title="Book Two",
            author="Author",
            genre="Fiction",
            published_year=2024,
            total_copies=1,
        )
    )
    response = await grpc_stub.ListBooks(library_pb2.ListBooksRequest())
    assert len(response.books) == 2
    assert response.next_page_token == ""


@pytest.mark.asyncio
async def test_list_books_pagination(grpc_stub):
    for i in range(3):
        await grpc_stub.CreateBook(
            library_pb2.CreateBookRequest(
                isbn=f"978000060009{i}",
                title=f"Page Book {i}",
                author="Author",
                genre="Fiction",
                published_year=2024,
                total_copies=1,
            )
        )

    response = await grpc_stub.ListBooks(library_pb2.ListBooksRequest(page_size=2))
    assert len(response.books) == 2
    assert response.next_page_token != ""

    response2 = await grpc_stub.ListBooks(
        library_pb2.ListBooksRequest(page_size=2, page_token=response.next_page_token)
    )
    assert len(response2.books) == 1


@pytest.mark.asyncio
async def test_update_book(grpc_stub):
    created = await grpc_stub.CreateBook(
        library_pb2.CreateBookRequest(
            isbn="9780000600021",
            title="Original",
            author="Author",
            genre="Fiction",
            published_year=2024,
            total_copies=1,
        )
    )
    updated = await grpc_stub.UpdateBook(
        library_pb2.UpdateBookRequest(book_id=created.id, title="Updated via gRPC")
    )
    assert updated.title == "Updated via gRPC"


@pytest.mark.asyncio
async def test_delete_book(grpc_stub):
    created = await grpc_stub.CreateBook(
        library_pb2.CreateBookRequest(
            isbn="9780000600031",
            title="To Delete",
            author="Author",
            genre="Fiction",
            published_year=2024,
            total_copies=1,
        )
    )
    await grpc_stub.DeleteBook(library_pb2.DeleteBookRequest(book_id=created.id))

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await grpc_stub.GetBook(library_pb2.GetBookRequest(book_id=created.id))
    assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_get_book_not_found(grpc_stub):
    fake_id = str(uuid.uuid4())
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await grpc_stub.GetBook(library_pb2.GetBookRequest(book_id=fake_id))
    assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_reserve_and_return(grpc_stub):
    user_id = str(uuid.uuid4())
    book = await grpc_stub.CreateBook(
        library_pb2.CreateBookRequest(
            isbn="9780000600051",
            title="Reserve Me",
            author="Author",
            genre="Fiction",
            published_year=2024,
            total_copies=2,
        )
    )
    reserve_result = await grpc_stub.ReserveBooks(
        library_pb2.ReserveBooksRequest(user_id=user_id, book_ids=[book.id])
    )
    reservations = reserve_result.reservations
    assert len(reservations) == 1
    assert reservations[0].status == library_pb2.RESERVATION_STATUS_ACTIVE

    fetched = await grpc_stub.GetBook(library_pb2.GetBookRequest(book_id=book.id))
    assert fetched.available_copies == 1

    returned = await grpc_stub.ReturnReservation(
        library_pb2.ReturnReservationRequest(reservation_id=reservations[0].id)
    )
    assert returned.status == library_pb2.RESERVATION_STATUS_RETURNED


@pytest.mark.asyncio
async def test_reserve_unavailable(grpc_stub):
    user_id1 = str(uuid.uuid4())
    user_id2 = str(uuid.uuid4())
    book = await grpc_stub.CreateBook(
        library_pb2.CreateBookRequest(
            isbn="9780000600061",
            title="One Copy",
            author="Author",
            genre="Fiction",
            published_year=2024,
            total_copies=1,
        )
    )
    await grpc_stub.ReserveBooks(
        library_pb2.ReserveBooksRequest(user_id=user_id1, book_ids=[book.id])
    )
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await grpc_stub.ReserveBooks(
            library_pb2.ReserveBooksRequest(user_id=user_id2, book_ids=[book.id])
        )
    assert exc_info.value.code() == grpc.StatusCode.FAILED_PRECONDITION


@pytest.mark.asyncio
async def test_list_reservations(grpc_stub):
    user_id = str(uuid.uuid4())
    book = await grpc_stub.CreateBook(
        library_pb2.CreateBookRequest(
            isbn="9780000600071",
            title="List Res",
            author="Author",
            genre="Fiction",
            published_year=2024,
            total_copies=5,
        )
    )
    await grpc_stub.ReserveBooks(
        library_pb2.ReserveBooksRequest(user_id=user_id, book_ids=[book.id])
    )
    result = await grpc_stub.ListReservations(library_pb2.ListReservationsRequest())
    assert len(result.reservations) >= 1


@pytest.mark.asyncio
async def test_get_reservation(grpc_stub):
    user_id = str(uuid.uuid4())
    book = await grpc_stub.CreateBook(
        library_pb2.CreateBookRequest(
            isbn="9780000600081",
            title="Get Res",
            author="Author",
            genre="Fiction",
            published_year=2024,
            total_copies=5,
        )
    )
    reserve_result = await grpc_stub.ReserveBooks(
        library_pb2.ReserveBooksRequest(user_id=user_id, book_ids=[book.id])
    )
    res_id = reserve_result.reservations[0].id
    result = await grpc_stub.GetReservation(
        library_pb2.GetReservationRequest(reservation_id=res_id)
    )
    assert result.id == res_id
    assert result.user_id == user_id
