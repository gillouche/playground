"""System tests for gRPC LibraryService."""

import uuid

import grpc
import pytest
from conftest import grpc_call


@pytest.mark.asyncio
async def test_list_books_empty(grpc_channel):
    result = await grpc_call(grpc_channel, "ListBooks")
    assert result["books"] == []


@pytest.mark.asyncio
async def test_create_and_get_book(grpc_channel):
    created = await grpc_call(
        grpc_channel,
        "CreateBook",
        {
            "isbn": "9780000600001",
            "title": "gRPC Book",
            "author": "gRPC Author",
            "genre": "Technology",
            "published_year": 2024,
            "total_copies": 5,
        },
    )
    assert created["isbn"] == "9780000600001"
    assert created["title"] == "gRPC Book"
    assert created["available_copies"] == 5

    fetched = await grpc_call(grpc_channel, "GetBook", {"book_id": created["id"]})
    assert fetched["id"] == created["id"]
    assert fetched["title"] == "gRPC Book"


@pytest.mark.asyncio
async def test_list_books_with_data(grpc_channel):
    await grpc_call(
        grpc_channel,
        "CreateBook",
        {
            "isbn": "9780000600011",
            "title": "Book One",
            "author": "Author",
            "genre": "Fiction",
            "published_year": 2024,
            "total_copies": 1,
        },
    )
    await grpc_call(
        grpc_channel,
        "CreateBook",
        {
            "isbn": "9780000600012",
            "title": "Book Two",
            "author": "Author",
            "genre": "Fiction",
            "published_year": 2024,
            "total_copies": 1,
        },
    )
    result = await grpc_call(grpc_channel, "ListBooks")
    assert len(result["books"]) == 2


@pytest.mark.asyncio
async def test_update_book(grpc_channel):
    created = await grpc_call(
        grpc_channel,
        "CreateBook",
        {
            "isbn": "9780000600021",
            "title": "Original",
            "author": "Author",
            "genre": "Fiction",
            "published_year": 2024,
            "total_copies": 1,
        },
    )
    updated = await grpc_call(
        grpc_channel,
        "UpdateBook",
        {"book_id": created["id"], "title": "Updated via gRPC"},
    )
    assert updated["title"] == "Updated via gRPC"


@pytest.mark.asyncio
async def test_delete_book(grpc_channel):
    created = await grpc_call(
        grpc_channel,
        "CreateBook",
        {
            "isbn": "9780000600031",
            "title": "To Delete",
            "author": "Author",
            "genre": "Fiction",
            "published_year": 2024,
            "total_copies": 1,
        },
    )
    result = await grpc_call(grpc_channel, "DeleteBook", {"book_id": created["id"]})
    assert result["deleted"] is True

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await grpc_call(grpc_channel, "GetBook", {"book_id": created["id"]})
    assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_get_book_not_found(grpc_channel):
    fake_id = str(uuid.uuid4())
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await grpc_call(grpc_channel, "GetBook", {"book_id": fake_id})
    assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND


@pytest.mark.asyncio
async def test_get_inventory(grpc_channel):
    await grpc_call(
        grpc_channel,
        "CreateBook",
        {
            "isbn": "9780000600041",
            "title": "Inventory Book",
            "author": "Author",
            "genre": "Fiction",
            "published_year": 2024,
            "total_copies": 3,
        },
    )
    result = await grpc_call(grpc_channel, "GetInventory")
    assert len(result["books"]) >= 1


@pytest.mark.asyncio
async def test_reserve_and_return(grpc_channel):
    book = await grpc_call(
        grpc_channel,
        "CreateBook",
        {
            "isbn": "9780000600051",
            "title": "Reserve Me",
            "author": "Author",
            "genre": "Fiction",
            "published_year": 2024,
            "total_copies": 2,
        },
    )
    reserve_result = await grpc_call(
        grpc_channel,
        "ReserveBooks",
        {"user_id": "grpc_user", "book_ids": [book["id"]]},
    )
    reservations = reserve_result["reservations"]
    assert len(reservations) == 1
    assert reservations[0]["status"] == "ACTIVE"

    # Verify copies decremented
    fetched = await grpc_call(grpc_channel, "GetBook", {"book_id": book["id"]})
    assert fetched["available_copies"] == 1

    # Return
    returned = await grpc_call(
        grpc_channel,
        "ReturnReservation",
        {"reservation_id": reservations[0]["id"]},
    )
    assert returned["status"] == "RETURNED"


@pytest.mark.asyncio
async def test_reserve_unavailable(grpc_channel):
    book = await grpc_call(
        grpc_channel,
        "CreateBook",
        {
            "isbn": "9780000600061",
            "title": "One Copy",
            "author": "Author",
            "genre": "Fiction",
            "published_year": 2024,
            "total_copies": 1,
        },
    )
    await grpc_call(
        grpc_channel,
        "ReserveBooks",
        {"user_id": "user1", "book_ids": [book["id"]]},
    )
    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        await grpc_call(
            grpc_channel,
            "ReserveBooks",
            {"user_id": "user2", "book_ids": [book["id"]]},
        )
    assert exc_info.value.code() == grpc.StatusCode.FAILED_PRECONDITION


@pytest.mark.asyncio
async def test_list_reservations(grpc_channel):
    book = await grpc_call(
        grpc_channel,
        "CreateBook",
        {
            "isbn": "9780000600071",
            "title": "List Res",
            "author": "Author",
            "genre": "Fiction",
            "published_year": 2024,
            "total_copies": 5,
        },
    )
    await grpc_call(
        grpc_channel,
        "ReserveBooks",
        {"user_id": "user1", "book_ids": [book["id"]]},
    )
    result = await grpc_call(grpc_channel, "ListReservations")
    assert len(result["reservations"]) >= 1


@pytest.mark.asyncio
async def test_get_reservation(grpc_channel):
    book = await grpc_call(
        grpc_channel,
        "CreateBook",
        {
            "isbn": "9780000600081",
            "title": "Get Res",
            "author": "Author",
            "genre": "Fiction",
            "published_year": 2024,
            "total_copies": 5,
        },
    )
    reserve_result = await grpc_call(
        grpc_channel,
        "ReserveBooks",
        {"user_id": "user1", "book_ids": [book["id"]]},
    )
    res_id = reserve_result["reservations"][0]["id"]
    result = await grpc_call(grpc_channel, "GetReservation", {"reservation_id": res_id})
    assert result["id"] == res_id
    assert result["user_id"] == "user1"
