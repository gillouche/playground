"""System tests for complete end-to-end library workflows."""

import uuid

import pytest


@pytest.mark.asyncio
async def test_complete_library_workflow(rest_client, create_sample_book):
    """Full workflow: create -> list -> reserve -> check availability -> return -> verify."""
    user_id = str(uuid.uuid4())
    book1 = await create_sample_book(isbn="9780000900001", total_copies=2)
    await create_sample_book(isbn="9780000900002", total_copies=3)

    resp = await rest_client.get("/api/v1/books")
    assert len(resp.json()["items"]) == 2

    reserve_resp = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book1["id"]]},
    )
    assert reserve_resp.status_code == 201
    reservation = reserve_resp.json()[0]

    book_resp = await rest_client.get(f"/api/v1/books/{book1['id']}")
    assert book_resp.json()["available_copies"] == 1

    return_resp = await rest_client.patch(
        f"/api/v1/reservations/{reservation['id']}",
        json={"status": "RETURNED"},
    )
    assert return_resp.status_code == 200
    assert return_resp.json()["status"] == "RETURNED"

    book_resp = await rest_client.get(f"/api/v1/books/{book1['id']}")
    assert book_resp.json()["available_copies"] == 2

    res_resp = await rest_client.get(f"/api/v1/reservations/{reservation['id']}")
    assert res_resp.json()["status"] == "RETURNED"


@pytest.mark.asyncio
async def test_reserve_last_copy_then_fail(rest_client, create_sample_book):
    """Reserve the last copy, then verify a second attempt fails."""
    user_id1 = str(uuid.uuid4())
    user_id2 = str(uuid.uuid4())
    book = await create_sample_book(isbn="9780000900003", total_copies=1)

    resp = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id1, "book_ids": [book["id"]]},
    )
    assert resp.status_code == 201

    book_resp = await rest_client.get(f"/api/v1/books/{book['id']}")
    assert book_resp.json()["available_copies"] == 0

    resp2 = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id2, "book_ids": [book["id"]]},
    )
    assert resp2.status_code == 409
