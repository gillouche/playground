import uuid
from datetime import UTC, datetime

from generated.models import (
    Book,
    BookCreate,
    BookUpdate,
    PaginatedBooks,
    PaginatedReservations,
    Reservation,
    ReservationCreate,
    ReservationUpdate,
)


class TestBookSchemas:
    def test_book_create_valid(self):
        book = BookCreate(
            isbn="9780134685991",
            title="Effective Java",
            author="Joshua Bloch",
            genre="Programming",
            published_year=2018,
            total_copies=5,
        )
        assert book.isbn == "9780134685991"
        assert book.total_copies == 5

    def test_book_create_with_zero_copies(self):
        book = BookCreate(
            isbn="9780134685991",
            title="Test",
            author="Test",
            genre="Test",
            published_year=2020,
            total_copies=0,
        )
        assert book.total_copies == 0

    def test_book_update_partial(self):
        update = BookUpdate(title="New Title")
        assert update.title == "New Title"
        assert update.isbn is None
        assert update.author is None

    def test_book_from_attributes(self):
        now = datetime.now(UTC)
        data = {
            "id": uuid.uuid4(),
            "isbn": "9780134685991",
            "title": "Test",
            "author": "Author",
            "genre": "Fiction",
            "published_year": 2020,
            "total_copies": 5,
            "available_copies": 3,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }
        response = Book(**data)
        assert response.available_copies == 3
        assert response.version == 1

    def test_book_default_version(self):
        now = datetime.now(UTC)
        data = {
            "id": uuid.uuid4(),
            "isbn": "9780134685991",
            "title": "Test",
            "author": "Author",
            "genre": "Fiction",
            "published_year": 2020,
            "total_copies": 5,
            "available_copies": 3,
            "created_at": now,
            "updated_at": now,
        }
        response = Book(**data)
        assert response.version == 1


class TestReservationSchemas:
    def test_reservation_create(self):
        book_id = uuid.uuid4()
        user_id = uuid.uuid4()
        data = ReservationCreate(user_id=user_id, book_ids=[book_id])
        assert data.user_id == user_id
        assert len(data.book_ids) == 1

    def test_reservation_model(self):
        now = datetime.now(UTC)
        user_id = uuid.uuid4()
        data = {
            "id": uuid.uuid4(),
            "book_id": uuid.uuid4(),
            "user_id": user_id,
            "reserved_at": now,
            "due_date": now,
            "returned_at": None,
            "status": "ACTIVE",
        }
        response = Reservation(**data)
        assert response.status.value == "ACTIVE"
        assert response.returned_at is None
        assert response.user_id == user_id


class TestReservationUpdate:
    def test_reservation_update_returned(self):
        update = ReservationUpdate(status="RETURNED")
        assert update.status.value == "RETURNED"

    def test_reservation_update_active(self):
        update = ReservationUpdate(status="ACTIVE")
        assert update.status.value == "ACTIVE"


class TestPaginatedBooks:
    def test_empty_paginated_books(self):
        paginated = PaginatedBooks(items=[], continuation_token=None, has_more=False)
        assert paginated.items == []
        assert paginated.continuation_token is None
        assert paginated.has_more is False

    def test_paginated_books_with_items(self):
        now = datetime.now(UTC)
        book = Book(
            id=uuid.uuid4(),
            isbn="9780134685991",
            title="Test",
            author="Author",
            genre="Fiction",
            published_year=2020,
            total_copies=5,
            available_copies=3,
            version=1,
            created_at=now,
            updated_at=now,
        )
        paginated = PaginatedBooks(items=[book], continuation_token="next_token", has_more=True)
        assert len(paginated.items) == 1
        assert paginated.continuation_token == "next_token"
        assert paginated.has_more is True


class TestPaginatedReservations:
    def test_empty_paginated_reservations(self):
        paginated = PaginatedReservations(items=[], continuation_token=None, has_more=False)
        assert paginated.items == []
        assert paginated.continuation_token is None
        assert paginated.has_more is False

    def test_paginated_reservations_with_items(self):
        now = datetime.now(UTC)
        user_id = uuid.uuid4()
        reservation = Reservation(
            id=uuid.uuid4(),
            book_id=uuid.uuid4(),
            user_id=user_id,
            reserved_at=now,
            due_date=now,
            returned_at=None,
            status="ACTIVE",
        )
        paginated = PaginatedReservations(
            items=[reservation], continuation_token="tok", has_more=True
        )
        assert len(paginated.items) == 1
        assert paginated.continuation_token == "tok"
        assert paginated.has_more is True
