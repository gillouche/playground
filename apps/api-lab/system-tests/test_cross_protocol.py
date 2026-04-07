"""System tests verifying data consistency across REST, gRPC, and GraphQL."""

import uuid

import pytest
from conftest import graphql_query
from library.v1 import library_pb2


@pytest.mark.asyncio
async def test_create_rest_query_graphql_and_grpc(rest_client, graphql_client, grpc_stub):
    """Create a book via REST, verify it's visible via GraphQL and gRPC."""
    resp = await rest_client.post(
        "/api/v1/books",
        json={
            "isbn": "9780000800001",
            "title": "Cross Protocol",
            "author": "Cross Author",
            "genre": "Science",
            "published_year": 2024,
            "total_copies": 4,
        },
    )
    assert resp.status_code == 201
    rest_book = resp.json()

    gql_result = await graphql_query(
        graphql_client,
        f"""
        {{
            book(bookId: "{rest_book["id"]}") {{
                id isbn title author
            }}
        }}
        """,
    )
    gql_book = gql_result["data"]["book"]
    assert gql_book["isbn"] == "9780000800001"
    assert gql_book["title"] == "Cross Protocol"

    grpc_book = await grpc_stub.GetBook(library_pb2.GetBookRequest(book_id=rest_book["id"]))
    assert grpc_book.isbn == "9780000800001"
    assert grpc_book.title == "Cross Protocol"


@pytest.mark.asyncio
async def test_reserve_grpc_verify_rest_and_graphql(rest_client, graphql_client, grpc_stub):
    """Reserve via gRPC, verify reservation visible via REST and GraphQL."""
    user_id = str(uuid.uuid4())
    resp = await rest_client.post(
        "/api/v1/books",
        json={
            "isbn": "9780000800002",
            "title": "Reserve Cross",
            "author": "Author",
            "genre": "Fiction",
            "published_year": 2024,
            "total_copies": 3,
        },
    )
    book = resp.json()

    reserve_result = await grpc_stub.ReserveBooks(
        library_pb2.ReserveBooksRequest(user_id=user_id, book_ids=[book["id"]])
    )
    res_id = reserve_result.reservations[0].id

    rest_res = await rest_client.get(f"/api/v1/reservations/{res_id}")
    assert rest_res.status_code == 200
    assert rest_res.json()["status"] == "ACTIVE"

    gql_result = await graphql_query(
        graphql_client,
        f"""
        {{
            reservation(reservationId: "{res_id}") {{
                id status userId
            }}
        }}
        """,
    )
    assert gql_result["data"]["reservation"]["status"] == "ACTIVE"
    assert gql_result["data"]["reservation"]["userId"] == user_id


@pytest.mark.asyncio
async def test_full_cross_protocol_lifecycle(rest_client, graphql_client, grpc_stub):
    """REST create -> gRPC reserve -> GraphQL query -> REST return -> verify all."""
    user_id = str(uuid.uuid4())
    resp = await rest_client.post(
        "/api/v1/books",
        json={
            "isbn": "9780000800003",
            "title": "Lifecycle",
            "author": "Author",
            "genre": "Fiction",
            "published_year": 2024,
            "total_copies": 2,
        },
    )
    book = resp.json()

    reserve_result = await grpc_stub.ReserveBooks(
        library_pb2.ReserveBooksRequest(user_id=user_id, book_ids=[book["id"]])
    )
    res_id = reserve_result.reservations[0].id

    gql_result = await graphql_query(
        graphql_client,
        f"""
        {{
            reservation(reservationId: "{res_id}") {{
                status
            }}
        }}
        """,
    )
    assert gql_result["data"]["reservation"]["status"] == "ACTIVE"

    return_resp = await rest_client.patch(
        f"/api/v1/reservations/{res_id}",
        json={"status": "RETURNED"},
    )
    assert return_resp.status_code == 200
    assert return_resp.json()["status"] == "RETURNED"

    rest_res = await rest_client.get(f"/api/v1/reservations/{res_id}")
    assert rest_res.json()["status"] == "RETURNED"

    grpc_res = await grpc_stub.GetReservation(
        library_pb2.GetReservationRequest(reservation_id=res_id)
    )
    assert grpc_res.status == library_pb2.RESERVATION_STATUS_RETURNED

    gql_result = await graphql_query(
        graphql_client,
        f"""
        {{
            reservation(reservationId: "{res_id}") {{
                status
            }}
        }}
        """,
    )
    assert gql_result["data"]["reservation"]["status"] == "RETURNED"
