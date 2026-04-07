import uuid
from unittest.mock import AsyncMock

import pytest
from generated.models import ListBooksQuery, ListReservationsQuery
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _make_book(**kwargs):
    from datetime import UTC, datetime

    defaults = {
        "id": uuid.uuid4(),
        "isbn": "9780134685991",
        "title": "Effective Java",
        "author": "Joshua Bloch",
        "genre": "Programming",
        "published_year": 2018,
        "total_copies": 5,
        "available_copies": 5,
        "version": 1,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)

    from generated.models import Book

    return Book(**defaults)


def _make_reservation(**kwargs):
    from datetime import UTC, datetime

    defaults = {
        "id": uuid.uuid4(),
        "book_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "reserved_at": datetime.now(UTC),
        "due_date": datetime.now(UTC),
        "returned_at": None,
        "status": "ACTIVE",
    }
    defaults.update(kwargs)

    from generated.models import Reservation

    return Reservation(**defaults)


@pytest.fixture
def mock_book_service():
    from services.book_service import BookService

    service = AsyncMock(spec=BookService)
    return service


@pytest.fixture
def client_with_service(mock_book_service):
    from main import app
    from routers import rest as rest_module

    original = rest_module._book_service
    rest_module._book_service = mock_book_service
    yield app, mock_book_service
    rest_module._book_service = original


class TestHealthEndpoints:
    async def test_healthz(self):
        from main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/healthz")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    async def test_info(self):
        from main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/info")
            assert response.status_code == 200
            data = response.json()
            assert "hostname" in data
            assert "environment" in data


class TestListBooks:
    async def test_list_books_empty(self, client_with_service):
        from generated.models import PaginatedBooks

        app, service = client_with_service
        service.list_books.return_value = PaginatedBooks(
            items=[], continuation_token=None, has_more=False
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/books")
            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []
            assert data["continuation_token"] is None
            assert data["has_more"] is False

    async def test_list_books_with_results(self, client_with_service):
        from generated.models import PaginatedBooks

        app, service = client_with_service
        book = _make_book()
        service.list_books.return_value = PaginatedBooks(
            items=[book], continuation_token=None, has_more=False
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/books")
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["isbn"] == "9780134685991"

    async def test_list_books_with_filters(self, client_with_service):
        from generated.models import PaginatedBooks

        app, service = client_with_service
        service.list_books.return_value = PaginatedBooks(
            items=[], continuation_token=None, has_more=False
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/books",
                params={"available_only": True, "genre": "Fiction", "author": "Bloch"},
            )
            assert response.status_code == 200
            service.list_books.assert_called_once_with(
                ListBooksQuery(
                    available_only=True,
                    genre="Fiction",
                    author="Bloch",
                    search=None,
                    limit=20,
                    continuation_token=None,
                    sort_by="created_at",
                    sort_order="asc",
                )
            )

    async def test_list_books_with_pagination(self, client_with_service):
        from generated.models import PaginatedBooks

        app, service = client_with_service
        service.list_books.return_value = PaginatedBooks(
            items=[], continuation_token="next123", has_more=True
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/books",
                params={"limit": 10, "continuation_token": "abc"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["continuation_token"] == "next123"
            assert data["has_more"] is True
            service.list_books.assert_called_once_with(
                ListBooksQuery(
                    available_only=False,
                    genre=None,
                    author=None,
                    search=None,
                    limit=10,
                    continuation_token="abc",
                    sort_by="created_at",
                    sort_order="asc",
                )
            )

    async def test_list_books_with_sorting(self, client_with_service):
        from generated.models import PaginatedBooks

        app, service = client_with_service
        service.list_books.return_value = PaginatedBooks(
            items=[], continuation_token=None, has_more=False
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/books",
                params={"sort_by": "title", "sort_order": "desc"},
            )
            assert response.status_code == 200
            service.list_books.assert_called_once_with(
                ListBooksQuery(
                    available_only=False,
                    genre=None,
                    author=None,
                    search=None,
                    limit=20,
                    continuation_token=None,
                    sort_by="title",
                    sort_order="desc",
                )
            )


class TestGetBook:
    async def test_get_book_found(self, client_with_service):
        app, service = client_with_service
        book_id = uuid.uuid4()
        book = _make_book(id=book_id)
        service.get_book.return_value = book

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/books/{book_id}")
            assert response.status_code == 200
            assert response.json()["id"] == str(book_id)
            assert "ETag" in response.headers

    async def test_get_book_not_found(self, client_with_service):
        app, service = client_with_service
        service.get_book.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/books/{uuid.uuid4()}")
            assert response.status_code == 404


class TestCreateBook:
    async def test_create_book_success(self, client_with_service):
        app, service = client_with_service
        book = _make_book()
        service.create_book.return_value = book

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/books",
                json={
                    "isbn": "9780134685991",
                    "title": "Effective Java",
                    "author": "Joshua Bloch",
                    "genre": "Programming",
                    "published_year": 2018,
                    "total_copies": 5,
                },
            )
            assert response.status_code == 201
            assert response.json()["isbn"] == "9780134685991"
            assert "Location" in response.headers
            assert f"/api/v1/books/{book.id}" in response.headers["Location"]
            assert "ETag" in response.headers

    async def test_create_book_duplicate_isbn(self, client_with_service):
        app, service = client_with_service
        from services.book_service import DuplicateISBNError

        service.create_book.side_effect = DuplicateISBNError("9780134685991")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/books",
                json={
                    "isbn": "9780134685991",
                    "title": "Duplicate",
                    "author": "Author",
                    "genre": "Fiction",
                    "published_year": 2020,
                    "total_copies": 1,
                },
            )
            assert response.status_code == 409
            assert "already exists" in response.json()["detail"]


class TestUpdateBook:
    async def test_update_book_success(self, client_with_service):
        app, service = client_with_service
        book_id = uuid.uuid4()
        book = _make_book(id=book_id, title="Updated Title", version=2)
        service.update_book.return_value = book

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/api/v1/books/{book_id}",
                json={"title": "Updated Title"},
                headers={"If-Match": '"1"'},
            )
            assert response.status_code == 200
            assert response.json()["title"] == "Updated Title"

    async def test_update_book_not_found(self, client_with_service):
        app, service = client_with_service
        service.update_book.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/api/v1/books/{uuid.uuid4()}",
                json={"title": "New"},
                headers={"If-Match": '"1"'},
            )
            assert response.status_code == 404

    async def test_update_book_duplicate_isbn(self, client_with_service):
        app, service = client_with_service
        from services.book_service import DuplicateISBNError

        service.update_book.side_effect = DuplicateISBNError("9780134685991")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/api/v1/books/{uuid.uuid4()}",
                json={"isbn": "9780134685991"},
                headers={"If-Match": '"1"'},
            )
            assert response.status_code == 409

    async def test_update_book_version_mismatch(self, client_with_service):
        app, service = client_with_service
        from services.book_service import StaleVersionError

        service.update_book.side_effect = StaleVersionError(
            "Expected version 1, but current version is 2"
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/api/v1/books/{uuid.uuid4()}",
                json={"title": "Stale"},
                headers={"If-Match": '"1"'},
            )
            assert response.status_code == 412

    async def test_update_book_missing_if_match(self, client_with_service):
        app, service = client_with_service

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/api/v1/books/{uuid.uuid4()}",
                json={"title": "No ETag"},
            )
            assert response.status_code == 422


class TestDeleteBook:
    async def test_delete_book_success(self, client_with_service):
        app, service = client_with_service
        service.delete_book.return_value = True

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(f"/api/v1/books/{uuid.uuid4()}")
            assert response.status_code == 204

    async def test_delete_book_not_found(self, client_with_service):
        app, service = client_with_service
        service.delete_book.return_value = False

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(f"/api/v1/books/{uuid.uuid4()}")
            assert response.status_code == 404

    async def test_delete_book_with_active_reservations(self, client_with_service):
        app, service = client_with_service
        from services.book_service import ActiveReservationsError

        service.delete_book.side_effect = ActiveReservationsError()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(f"/api/v1/books/{uuid.uuid4()}")
            assert response.status_code == 409
            assert "active reservations" in response.json()["detail"].lower()


class TestReservations:
    async def test_reserve_books_success(self, client_with_service):
        app, service = client_with_service
        book_id = uuid.uuid4()
        user_id = uuid.uuid4()
        reservation = _make_reservation(book_id=book_id, user_id=user_id)
        service.reserve_books.return_value = [reservation]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/reservations",
                json={"user_id": str(user_id), "book_ids": [str(book_id)]},
            )
            assert response.status_code == 201
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == "ACTIVE"

    async def test_reserve_books_unavailable(self, client_with_service):
        app, service = client_with_service
        service.reserve_books.side_effect = ValueError(
            "Book 'Test' is not available for reservation"
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/reservations",
                json={"user_id": str(uuid.uuid4()), "book_ids": [str(uuid.uuid4())]},
            )
            assert response.status_code == 409
            assert "not available" in response.json()["detail"]

    async def test_update_reservation_success(self, client_with_service):
        app, service = client_with_service
        res_id = uuid.uuid4()
        reservation = _make_reservation(id=res_id, status="RETURNED")
        service.return_reservation.return_value = reservation

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.patch(
                f"/api/v1/reservations/{res_id}",
                json={"status": "RETURNED"},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "RETURNED"

    async def test_update_reservation_not_found(self, client_with_service):
        app, service = client_with_service
        service.return_reservation.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.patch(
                f"/api/v1/reservations/{uuid.uuid4()}",
                json={"status": "RETURNED"},
            )
            assert response.status_code == 404

    async def test_update_reservation_already_returned(self, client_with_service):
        app, service = client_with_service
        service.return_reservation.side_effect = ValueError("Reservation is already RETURNED")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.patch(
                f"/api/v1/reservations/{uuid.uuid4()}",
                json={"status": "RETURNED"},
            )
            assert response.status_code == 409

    async def test_update_reservation_invalid_status(self, client_with_service):
        app, service = client_with_service

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.patch(
                f"/api/v1/reservations/{uuid.uuid4()}",
                json={"status": "ACTIVE"},
            )
            assert response.status_code == 400

    async def test_list_reservations(self, client_with_service):
        from generated.models import PaginatedReservations

        app, service = client_with_service
        reservation = _make_reservation()
        service.list_reservations.return_value = PaginatedReservations(
            items=[reservation], continuation_token=None, has_more=False
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/reservations")
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["continuation_token"] is None
            assert data["has_more"] is False

    async def test_list_reservations_with_filters(self, client_with_service):
        from generated.models import PaginatedReservations

        app, service = client_with_service
        user_id = uuid.uuid4()
        service.list_reservations.return_value = PaginatedReservations(
            items=[], continuation_token=None, has_more=False
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/reservations",
                params={"user_id": str(user_id), "status": "ACTIVE"},
            )
            assert response.status_code == 200
            service.list_reservations.assert_called_once_with(
                ListReservationsQuery(
                    user_id=user_id,
                    status="ACTIVE",
                    book_id=None,
                    limit=20,
                    continuation_token=None,
                    sort_by="reserved_at",
                    sort_order="desc",
                )
            )

    async def test_list_reservations_with_pagination(self, client_with_service):
        from generated.models import PaginatedReservations

        app, service = client_with_service
        service.list_reservations.return_value = PaginatedReservations(
            items=[], continuation_token="next456", has_more=True
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/reservations",
                params={"limit": 5, "continuation_token": "tok"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["continuation_token"] == "next456"
            assert data["has_more"] is True

    async def test_get_reservation_found(self, client_with_service):
        app, service = client_with_service
        res_id = uuid.uuid4()
        reservation = _make_reservation(id=res_id)
        service.get_reservation.return_value = reservation

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/reservations/{res_id}")
            assert response.status_code == 200
            assert response.json()["id"] == str(res_id)

    async def test_get_reservation_not_found(self, client_with_service):
        app, service = client_with_service
        service.get_reservation.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/reservations/{uuid.uuid4()}")
            assert response.status_code == 404
