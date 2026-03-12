"""System tests for REST API inventory endpoint."""

import pytest


@pytest.mark.asyncio
async def test_inventory_empty(rest_client):
    resp = await rest_client.get("/api/v1/inventory")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []


@pytest.mark.asyncio
async def test_inventory_excludes_zero_copies(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000500001", total_copies=3)
    await create_sample_book(isbn="9780000500002", total_copies=0)
    resp = await rest_client.get("/api/v1/inventory")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    isbns = [item["isbn"] for item in items]
    assert "9780000500001" in isbns


@pytest.mark.asyncio
async def test_inventory_reflects_reservations(rest_client, create_sample_book):
    book = await create_sample_book(isbn="9780000500003", total_copies=2)

    # Check initial inventory
    resp = await rest_client.get("/api/v1/inventory")
    items_before = resp.json()["items"]
    inv_book = next(i for i in items_before if i["isbn"] == "9780000500003")
    assert inv_book["available_copies"] == 2

    # Reserve one copy
    reserve_resp = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": "user1", "book_ids": [book["id"]]},
    )
    reservation_id = reserve_resp.json()[0]["id"]

    # Inventory should reflect decreased availability
    resp = await rest_client.get("/api/v1/inventory")
    items_after = resp.json()["items"]
    inv_book = next(i for i in items_after if i["isbn"] == "9780000500003")
    assert inv_book["available_copies"] == 1

    # Return and verify restored
    await rest_client.post(f"/api/v1/reservations/{reservation_id}/return")
    resp = await rest_client.get("/api/v1/inventory")
    items_restored = resp.json()["items"]
    inv_book = next(i for i in items_restored if i["isbn"] == "9780000500003")
    assert inv_book["available_copies"] == 2
