"""System tests for REST API reservation operations."""

import uuid

import pytest


@pytest.mark.asyncio
async def test_reserve_single_book(rest_client, create_sample_book):
    user_id = str(uuid.uuid4())
    book = await create_sample_book(total_copies=3)
    resp = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book["id"]]},
    )
    assert resp.status_code == 201
    reservations = resp.json()
    assert len(reservations) == 1
    assert reservations[0]["book_id"] == book["id"]
    assert reservations[0]["user_id"] == user_id
    assert reservations[0]["status"] == "ACTIVE"

    book_resp = await rest_client.get(f"/api/v1/books/{book['id']}")
    assert book_resp.json()["available_copies"] == 2


@pytest.mark.asyncio
async def test_reserve_multiple_books(rest_client, create_sample_book):
    user_id = str(uuid.uuid4())
    book1 = await create_sample_book(isbn="9780000100001")
    book2 = await create_sample_book(isbn="9780000100002")
    resp = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book1["id"], book2["id"]]},
    )
    assert resp.status_code == 201
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_reserve_unavailable_book(rest_client, create_sample_book):
    user_id1 = str(uuid.uuid4())
    user_id2 = str(uuid.uuid4())
    book = await create_sample_book(total_copies=1)
    await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id1, "book_ids": [book["id"]]},
    )
    resp = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id2, "book_ids": [book["id"]]},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_reserve_nonexistent_book(rest_client):
    user_id = str(uuid.uuid4())
    fake_id = str(uuid.uuid4())
    resp = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [fake_id]},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_return_reservation(rest_client, create_sample_book):
    user_id = str(uuid.uuid4())
    book = await create_sample_book(total_copies=2)
    reserve_resp = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book["id"]]},
    )
    reservation_id = reserve_resp.json()[0]["id"]

    resp = await rest_client.patch(
        f"/api/v1/reservations/{reservation_id}",
        json={"status": "RETURNED"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "RETURNED"

    book_resp = await rest_client.get(f"/api/v1/books/{book['id']}")
    assert book_resp.json()["available_copies"] == 2


@pytest.mark.asyncio
async def test_return_already_returned(rest_client, create_sample_book):
    user_id = str(uuid.uuid4())
    book = await create_sample_book()
    reserve_resp = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book["id"]]},
    )
    reservation_id = reserve_resp.json()[0]["id"]

    await rest_client.patch(
        f"/api/v1/reservations/{reservation_id}",
        json={"status": "RETURNED"},
    )
    resp = await rest_client.patch(
        f"/api/v1/reservations/{reservation_id}",
        json={"status": "RETURNED"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_return_nonexistent(rest_client):
    fake_id = str(uuid.uuid4())
    resp = await rest_client.patch(
        f"/api/v1/reservations/{fake_id}",
        json={"status": "RETURNED"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_reservations(rest_client, create_sample_book):
    user_id = str(uuid.uuid4())
    book = await create_sample_book()
    await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book["id"]]},
    )
    resp = await rest_client.get("/api/v1/reservations")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


@pytest.mark.asyncio
async def test_list_reservations_filter_by_user(rest_client, create_sample_book):
    alice = str(uuid.uuid4())
    bob = str(uuid.uuid4())
    book1 = await create_sample_book(isbn="9780000200001")
    book2 = await create_sample_book(isbn="9780000200002")
    await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": alice, "book_ids": [book1["id"]]},
    )
    await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": bob, "book_ids": [book2["id"]]},
    )
    resp = await rest_client.get("/api/v1/reservations", params={"user_id": alice})
    assert resp.status_code == 200
    reservations = resp.json()["items"]
    assert len(reservations) == 1
    assert reservations[0]["user_id"] == alice


@pytest.mark.asyncio
async def test_list_reservations_filter_by_status(rest_client, create_sample_book):
    user_id = str(uuid.uuid4())
    book1 = await create_sample_book(isbn="9780000300001")
    book2 = await create_sample_book(isbn="9780000300002")
    r1 = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book1["id"]]},
    )
    await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book2["id"]]},
    )
    await rest_client.patch(
        f"/api/v1/reservations/{r1.json()[0]['id']}",
        json={"status": "RETURNED"},
    )

    resp = await rest_client.get("/api/v1/reservations", params={"status": "ACTIVE"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_list_reservations_filter_by_book(rest_client, create_sample_book):
    user_id = str(uuid.uuid4())
    book1 = await create_sample_book(isbn="9780000400001")
    book2 = await create_sample_book(isbn="9780000400002")
    await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book1["id"]]},
    )
    await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book2["id"]]},
    )
    resp = await rest_client.get("/api/v1/reservations", params={"book_id": book1["id"]})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["book_id"] == book1["id"]


@pytest.mark.asyncio
async def test_get_reservation(rest_client, create_sample_book):
    user_id = str(uuid.uuid4())
    book = await create_sample_book()
    reserve_resp = await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book["id"]]},
    )
    reservation_id = reserve_resp.json()[0]["id"]
    resp = await rest_client.get(f"/api/v1/reservations/{reservation_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == reservation_id


@pytest.mark.asyncio
async def test_get_reservation_not_found(rest_client):
    fake_id = str(uuid.uuid4())
    resp = await rest_client.get(f"/api/v1/reservations/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_reservations_pagination(rest_client, create_sample_book):
    user_id = str(uuid.uuid4())
    book1 = await create_sample_book(isbn="9780000500001", total_copies=5)
    book2 = await create_sample_book(isbn="9780000500002", total_copies=5)
    book3 = await create_sample_book(isbn="9780000500003", total_copies=5)
    await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book1["id"]]},
    )
    await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book2["id"]]},
    )
    await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book3["id"]]},
    )

    resp = await rest_client.get("/api/v1/reservations", params={"limit": 2})
    assert resp.status_code == 200
    page1 = resp.json()
    assert len(page1["items"]) == 2
    assert page1["has_more"] is True
    assert page1["continuation_token"] is not None

    resp2 = await rest_client.get(
        "/api/v1/reservations",
        params={"limit": 2, "continuation_token": page1["continuation_token"]},
    )
    assert resp2.status_code == 200
    page2 = resp2.json()
    assert len(page2["items"]) == 1


@pytest.mark.asyncio
async def test_list_reservations_sort_by_due_date(rest_client, create_sample_book):
    user_id = str(uuid.uuid4())
    book1 = await create_sample_book(isbn="9780000600001", total_copies=5)
    book2 = await create_sample_book(isbn="9780000600002", total_copies=5)

    await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book1["id"]]},
    )
    await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": user_id, "book_ids": [book2["id"]]},
    )

    resp = await rest_client.get(
        "/api/v1/reservations",
        params={"sort_by": "due_date", "sort_order": "asc"},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    assert items[0]["due_date"] <= items[1]["due_date"]
