"""System tests for complete end-to-end library workflows."""

import pytest


@pytest.mark.asyncio
async def test_complete_library_workflow(rest_client, create_sample_book):
    """Full workflow: create -> list -> reserve -> inventory check -> return -> verify."""
    book1 = await create_sample_book(isbn="9780000900001", total_copies=2)
    await create_sample_book(isbn="9780000900002", total_copies=3)

    # List and verify
    resp = await rest_client.get("/api/v1/books")
    assert len(resp.json()) == 2

    # Reserve book1
    reserve_resp = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": "wf_user", "book_ids": [book1["id"]]},
    )
    assert reserve_resp.status_code == 201
    reservation = reserve_resp.json()[0]

    # Check inventory reflects decreased availability
    inv_resp = await rest_client.get("/api/v1/inventory")
    inv_book1 = next(i for i in inv_resp.json()["items"] if i["id"] == book1["id"])
    assert inv_book1["available_copies"] == 1

    # Return the book
    return_resp = await rest_client.post(f"/api/v1/reservations/{reservation['id']}/return")
    assert return_resp.status_code == 200
    assert return_resp.json()["status"] == "RETURNED"

    # Verify inventory restored
    inv_resp = await rest_client.get("/api/v1/inventory")
    inv_book1 = next(i for i in inv_resp.json()["items"] if i["id"] == book1["id"])
    assert inv_book1["available_copies"] == 2

    # Verify reservation status
    res_resp = await rest_client.get(f"/api/v1/reservations/{reservation['id']}")
    assert res_resp.json()["status"] == "RETURNED"


@pytest.mark.asyncio
async def test_reserve_last_copy_then_fail(rest_client, create_sample_book):
    """Reserve the last copy, then verify a second attempt fails."""
    book = await create_sample_book(isbn="9780000900003", total_copies=1)

    # Reserve the only copy
    resp = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": "user1", "book_ids": [book["id"]]},
    )
    assert resp.status_code == 201

    # Verify no copies available
    book_resp = await rest_client.get(f"/api/v1/books/{book['id']}")
    assert book_resp.json()["available_copies"] == 0

    # Second reservation should fail
    resp2 = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": "user2", "book_ids": [book["id"]]},
    )
    assert resp2.status_code == 409
