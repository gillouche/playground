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
async def test_create_book_returns_location_header(rest_client):
    resp = await rest_client.post(
        "/api/v1/books",
        json={
            "isbn": "9780000000099",
            "title": "Location Header Book",
            "author": "Test Author",
            "genre": "Fiction",
            "published_year": 2024,
            "total_copies": 1,
        },
    )
    assert resp.status_code == 201
    book = resp.json()
    assert resp.headers["Location"] == f"/api/v1/books/{book['id']}"


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
    data = resp.json()
    assert data["items"] == []
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_list_books_with_data(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000011")
    await create_sample_book(isbn="9780000000012")
    resp = await rest_client.get("/api/v1/books")
    assert resp.status_code == 200
    books = resp.json()["items"]
    assert len(books) == 2


@pytest.mark.asyncio
async def test_list_books_filter_by_genre(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000021", genre="Fiction")
    await create_sample_book(isbn="9780000000022", genre="Science")
    resp = await rest_client.get("/api/v1/books", params={"genre": "Fiction"})
    assert resp.status_code == 200
    books = resp.json()["items"]
    assert len(books) == 1
    assert books[0]["genre"] == "Fiction"


@pytest.mark.asyncio
async def test_list_books_filter_by_author(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000031", author="Alice")
    await create_sample_book(isbn="9780000000032", author="Bob")
    resp = await rest_client.get("/api/v1/books", params={"author": "Alice"})
    assert resp.status_code == 200
    books = resp.json()["items"]
    assert len(books) == 1
    assert books[0]["author"] == "Alice"


@pytest.mark.asyncio
async def test_list_books_filter_available_only(rest_client, create_sample_book):
    book = await create_sample_book(isbn="9780000000041", total_copies=1)
    await create_sample_book(isbn="9780000000042", total_copies=1)
    await rest_client.post(
        "/api/v1/reservations",
        json={"book_ids": [book["id"]]},
    )
    resp = await rest_client.get("/api/v1/books", params={"available_only": "true"})
    assert resp.status_code == 200
    books = resp.json()["items"]
    assert len(books) == 1
    assert books[0]["isbn"] == "9780000000042"


@pytest.mark.asyncio
async def test_list_books_filter_search(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000051", title="Python Programming")
    await create_sample_book(isbn="9780000000052", title="Java Basics")
    resp = await rest_client.get("/api/v1/books", params={"search": "Python"})
    assert resp.status_code == 200
    books = resp.json()["items"]
    assert len(books) == 1
    assert "Python" in books[0]["title"]


@pytest.mark.asyncio
async def test_list_books_pagination(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000071")
    await create_sample_book(isbn="9780000000072")
    await create_sample_book(isbn="9780000000073")

    resp = await rest_client.get("/api/v1/books", params={"limit": 2})
    assert resp.status_code == 200
    page1 = resp.json()
    assert len(page1["items"]) == 2
    assert page1["has_more"] is True
    assert page1["continuation_token"] is not None

    resp2 = await rest_client.get(
        "/api/v1/books",
        params={"limit": 2, "continuation_token": page1["continuation_token"]},
    )
    assert resp2.status_code == 200
    page2 = resp2.json()
    assert len(page2["items"]) == 1


@pytest.mark.asyncio
async def test_list_books_pagination_last_page(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000081")
    await create_sample_book(isbn="9780000000082")

    resp = await rest_client.get("/api/v1/books", params={"limit": 10})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_list_books_sort_by_title_asc(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000091", title="Zebra Book")
    await create_sample_book(isbn="9780000000092", title="Alpha Book")
    await create_sample_book(isbn="9780000000093", title="Middle Book")

    resp = await rest_client.get("/api/v1/books", params={"sort_by": "title", "sort_order": "asc"})
    assert resp.status_code == 200
    books = resp.json()["items"]
    titles = [b["title"] for b in books]
    assert titles == sorted(titles)


@pytest.mark.asyncio
async def test_list_books_sort_by_published_year_desc(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000094", published_year=2020)
    await create_sample_book(isbn="9780000000095", published_year=2024)
    await create_sample_book(isbn="9780000000096", published_year=2022)

    resp = await rest_client.get(
        "/api/v1/books",
        params={"sort_by": "published_year", "sort_order": "desc"},
    )
    assert resp.status_code == 200
    books = resp.json()["items"]
    years = [b["published_year"] for b in books]
    assert years == sorted(years, reverse=True)


@pytest.mark.asyncio
async def test_get_book(rest_client, create_sample_book):
    book = await create_sample_book()
    resp = await rest_client.get(f"/api/v1/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == book["id"]


@pytest.mark.asyncio
async def test_get_book_returns_etag(rest_client, create_sample_book):
    book = await create_sample_book()
    resp = await rest_client.get(f"/api/v1/books/{book['id']}")
    assert resp.status_code == 200
    assert "ETag" in resp.headers
    etag = resp.headers["ETag"]
    assert etag.startswith('"') and etag.endswith('"')


@pytest.mark.asyncio
async def test_get_book_not_found(rest_client):
    fake_id = str(uuid.uuid4())
    resp = await rest_client.get(f"/api/v1/books/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_book_requires_if_match(rest_client, create_sample_book):
    book = await create_sample_book()
    resp = await rest_client.put(
        f"/api/v1/books/{book['id']}",
        json={"title": "Updated Title"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_book_with_correct_etag(rest_client, create_sample_book):
    book = await create_sample_book()
    get_resp = await rest_client.get(f"/api/v1/books/{book['id']}")
    etag = get_resp.headers["ETag"]

    resp = await rest_client.put(
        f"/api/v1/books/{book['id']}",
        json={"title": "Updated Title"},
        headers={"If-Match": etag},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert resp.json()["isbn"] == book["isbn"]


@pytest.mark.asyncio
async def test_update_book_stale_etag(rest_client, create_sample_book):
    book = await create_sample_book()
    get_resp = await rest_client.get(f"/api/v1/books/{book['id']}")
    old_etag = get_resp.headers["ETag"]

    await rest_client.put(
        f"/api/v1/books/{book['id']}",
        json={"title": "First Update"},
        headers={"If-Match": old_etag},
    )

    resp = await rest_client.put(
        f"/api/v1/books/{book['id']}",
        json={"title": "Second Update"},
        headers={"If-Match": old_etag},
    )
    assert resp.status_code == 412


@pytest.mark.asyncio
async def test_update_book_not_found(rest_client):
    fake_id = str(uuid.uuid4())
    resp = await rest_client.put(
        f"/api/v1/books/{fake_id}",
        json={"title": "Nope"},
        headers={"If-Match": '"1"'},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_book_duplicate_isbn(rest_client, create_sample_book):
    await create_sample_book(isbn="9780000000061")
    book2 = await create_sample_book(isbn="9780000000062")
    get_resp = await rest_client.get(f"/api/v1/books/{book2['id']}")
    etag = get_resp.headers["ETag"]
    resp = await rest_client.put(
        f"/api/v1/books/{book2['id']}",
        json={"isbn": "9780000000061"},
        headers={"If-Match": etag},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_total_copies_adjusts_available(rest_client, create_sample_book):
    book = await create_sample_book(total_copies=5)
    get_resp = await rest_client.get(f"/api/v1/books/{book['id']}")
    etag = get_resp.headers["ETag"]
    resp = await rest_client.put(
        f"/api/v1/books/{book['id']}",
        json={"total_copies": 10},
        headers={"If-Match": etag},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["total_copies"] == 10
    assert updated["available_copies"] == book["available_copies"] + 5


@pytest.mark.asyncio
async def test_delete_book(rest_client, create_sample_book):
    book = await create_sample_book()
    resp = await rest_client.delete(f"/api/v1/books/{book['id']}")
    assert resp.status_code == 204
    resp = await rest_client.get(f"/api/v1/books/{book['id']}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_book_not_found(rest_client):
    fake_id = str(uuid.uuid4())
    resp = await rest_client.delete(f"/api/v1/books/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_book_with_active_reservation(rest_client, create_sample_book):
    book = await create_sample_book(total_copies=1)
    await rest_client.post(
        "/api/v1/reservations",
        json={"book_ids": [book["id"]]},
    )
    resp = await rest_client.delete(f"/api/v1/books/{book['id']}")
    assert resp.status_code == 409
