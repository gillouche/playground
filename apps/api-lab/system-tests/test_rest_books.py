"""System tests for REST API book CRUD operations."""

import uuid

import pytest


@pytest.mark.asyncio
async def test_create_book(rest_client, create_sample_book):  # noqa: ARG001
    book = await create_sample_book(isbn="9780000000001")
    assert book["isbn"] == "9780000000001"
    assert book["title"] == "Test Book"
    assert book["author"] == "Test Author"
    assert book["genre"] == "Fiction"
    assert book["published_year"] == 2024
    assert book["total_copies"] == 3
    assert book["available_copies"] == 3
    assert "id" in book
    assert "created_at" in book
    assert "updated_at" in book


@pytest.mark.asyncio
async def test_create_book_duplicate_isbn(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000002")
    resp = await rest_client.post(
        "/api/v1/books",
        json={
            "isbn": "9780000000002",
            "title": "Another Book",
            "author": "Author",
            "genre": "Science",
            "published_year": 2023,
            "total_copies": 1,
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_books_empty(rest_client):
    resp = await rest_client.get("/api/v1/books")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_books_with_data(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000011")
    await create_sample_book(isbn="9780000000012")
    resp = await rest_client.get("/api/v1/books")
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 2


@pytest.mark.asyncio
async def test_list_books_filter_by_genre(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000021", genre="Fiction")
    await create_sample_book(isbn="9780000000022", genre="Science")
    resp = await rest_client.get("/api/v1/books", params={"genre": "Fiction"})
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 1
    assert books[0]["genre"] == "Fiction"


@pytest.mark.asyncio
async def test_list_books_filter_by_author(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000031", author="Alice")
    await create_sample_book(isbn="9780000000032", author="Bob")
    resp = await rest_client.get("/api/v1/books", params={"author": "Alice"})
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 1
    assert books[0]["author"] == "Alice"


@pytest.mark.asyncio
async def test_list_books_filter_available_only(rest_client, create_sample_book):
    book = await create_sample_book(isbn="9780000000041", total_copies=1)
    await create_sample_book(isbn="9780000000042", total_copies=1)
    # Reserve the first book to make it unavailable
    await rest_client.post(
        "/api/v1/reservations",
        json={"user_id": "user1", "book_ids": [book["id"]]},
    )
    resp = await rest_client.get("/api/v1/books", params={"available_only": "true"})
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 1
    assert books[0]["isbn"] == "9780000000042"


@pytest.mark.asyncio
async def test_list_books_filter_search(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000051", title="Python Programming")
    await create_sample_book(isbn="9780000000052", title="Java Basics")
    resp = await rest_client.get("/api/v1/books", params={"search": "Python"})
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 1
    assert "Python" in books[0]["title"]


@pytest.mark.asyncio
async def test_get_book(rest_client, create_sample_book):
    book = await create_sample_book()
    resp = await rest_client.get(f"/api/v1/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == book["id"]


@pytest.mark.asyncio
async def test_get_book_not_found(rest_client):
    fake_id = str(uuid.uuid4())
    resp = await rest_client.get(f"/api/v1/books/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_book(rest_client, create_sample_book):
    book = await create_sample_book()
    resp = await rest_client.put(
        f"/api/v1/books/{book['id']}",
        json={"title": "Updated Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert resp.json()["isbn"] == book["isbn"]


@pytest.mark.asyncio
async def test_update_book_not_found(rest_client):
    fake_id = str(uuid.uuid4())
    resp = await rest_client.put(
        f"/api/v1/books/{fake_id}",
        json={"title": "Nope"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_book_duplicate_isbn(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000061")
    book2 = await create_sample_book(isbn="9780000000062")
    resp = await rest_client.put(
        f"/api/v1/books/{book2['id']}",
        json={"isbn": "9780000000061"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_total_copies_adjusts_available(rest_client, create_sample_book):
    book = await create_sample_book(total_copies=5)
    resp = await rest_client.put(
        f"/api/v1/books/{book['id']}",
        json={"total_copies": 10},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["total_copies"] == 10
    # available_copies should increase by the same delta
    assert updated["available_copies"] == book["available_copies"] + 5


@pytest.mark.asyncio
async def test_delete_book(rest_client, create_sample_book):
    book = await create_sample_book()
    resp = await rest_client.delete(f"/api/v1/books/{book['id']}")
    assert resp.status_code == 204
    # Verify deleted
    resp = await rest_client.get(f"/api/v1/books/{book['id']}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_book_not_found(rest_client):
    fake_id = str(uuid.uuid4())
    resp = await rest_client.delete(f"/api/v1/books/{fake_id}")
    assert resp.status_code == 404
