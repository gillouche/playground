import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _make_book_response(**kwargs):
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
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)

    from generated.models import BookResponse

    return BookResponse(**defaults)


def _make_reservation_response(**kwargs):
    from datetime import UTC, datetime

    defaults = {
        "id": uuid.uuid4(),
        "book_id": uuid.uuid4(),
        "user_id": "user-1",
        "reserved_at": datetime.now(UTC),
        "due_date": datetime.now(UTC),
        "returned_at": None,
        "status": "ACTIVE",
    }
    defaults.update(kwargs)

    from generated.models import ReservationResponse

    return ReservationResponse(**defaults)


@pytest.fixture
def mock_book_service():
    from services.book_service import BookService

    service = AsyncMock(spec=BookService)
    return service


@pytest.fixture
def client_with_service(mock_book_service):
    """Yields an AsyncClient with a mocked BookService injected."""
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
        app, service = client_with_service
        service.list_books.return_value = []

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/books")
            assert response.status_code == 200
            assert response.json() == []

    async def test_list_books_with_results(self, client_with_service):
        app, service = client_with_service
        book = _make_book_response()
        service.list_books.return_value = [book]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/books")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["isbn"] == "9780134685991"

    async def test_list_books_with_filters(self, client_with_service):
        app, service = client_with_service
        service.list_books.return_value = []

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/books",
                params={"available_only": True, "genre": "Fiction", "author": "Bloch"},
            )
            assert response.status_code == 200
            service.list_books.assert_called_once_with(
                available_only=True, genre="Fiction", author="Bloch", search=None
            )


class TestGetBook:
    async def test_get_book_found(self, client_with_service):
        app, service = client_with_service
        book_id = uuid.uuid4()
        book = _make_book_response(id=book_id)
        service.get_book.return_value = book

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/books/{book_id}")
            assert response.status_code == 200
            assert response.json()["id"] == str(book_id)

    async def test_get_book_not_found(self, client_with_service):
        app, service = client_with_service
        service.get_book.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/v1/books/{uuid.uuid4()}")
            assert response.status_code == 404


class TestCreateBook:
    async def test_create_book_success(self, client_with_service):
        app, service = client_with_service
        book = _make_book_response()
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
        book = _make_book_response(id=book_id, title="Updated Title")
        service.update_book.return_value = book

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/api/v1/books/{book_id}",
                json={"title": "Updated Title"},
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
            )
            assert response.status_code == 409


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


class TestInventory:
    async def test_get_inventory(self, client_with_service):
        app, service = client_with_service
        book = _make_book_response(available_copies=3)
        service.get_inventory.return_value = [book]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/inventory")
            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["available_copies"] == 3


class TestReservations:
    async def test_reserve_books_success(self, client_with_service):
        app, service = client_with_service
        book_id = uuid.uuid4()
        reservation = _make_reservation_response(book_id=book_id)
        service.reserve_books.return_value = [reservation]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/reservations",
                json={"user_id": "user-1", "book_ids": [str(book_id)]},
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
                json={"user_id": "user-1", "book_ids": [str(uuid.uuid4())]},
            )
            assert response.status_code == 409
            assert "not available" in response.json()["detail"]

    async def test_return_reservation_success(self, client_with_service):
        app, service = client_with_service
        res_id = uuid.uuid4()
        reservation = _make_reservation_response(id=res_id, status="RETURNED")
        service.return_reservation.return_value = reservation

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/v1/reservations/{res_id}/return")
            assert response.status_code == 200
            assert response.json()["status"] == "RETURNED"

    async def test_return_reservation_not_found(self, client_with_service):
        app, service = client_with_service
        service.return_reservation.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/v1/reservations/{uuid.uuid4()}/return")
            assert response.status_code == 404

    async def test_return_reservation_already_returned(self, client_with_service):
        app, service = client_with_service
        service.return_reservation.side_effect = ValueError("Reservation is already RETURNED")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/v1/reservations/{uuid.uuid4()}/return")
            assert response.status_code == 409

    async def test_list_reservations(self, client_with_service):
        app, service = client_with_service
        reservation = _make_reservation_response()
        service.list_reservations.return_value = [reservation]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/reservations")
            assert response.status_code == 200
            assert len(response.json()) == 1

    async def test_list_reservations_with_filters(self, client_with_service):
        app, service = client_with_service
        service.list_reservations.return_value = []

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/reservations",
                params={"user_id": "user-1", "status": "ACTIVE"},
            )
            assert response.status_code == 200
            service.list_reservations.assert_called_once_with(
                user_id="user-1", status="ACTIVE", book_id=None
            )

    async def test_get_reservation_found(self, client_with_service):
        app, service = client_with_service
        res_id = uuid.uuid4()
        reservation = _make_reservation_response(id=res_id)
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
