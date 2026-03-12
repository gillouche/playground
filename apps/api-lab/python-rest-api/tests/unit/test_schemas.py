import uuid
from datetime import UTC, datetime

from generated.models import (
    BookCreate,
    BookResponse,
    BookUpdate,
    ReservationCreate,
    ReservationResponse,
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

    def test_book_response_from_attributes(self):
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
        response = BookResponse(**data)
        assert response.available_copies == 3


class TestReservationSchemas:
    def test_reservation_create(self):
        book_id = uuid.uuid4()
        data = ReservationCreate(user_id="user-1", book_ids=[book_id])
        assert data.user_id == "user-1"
        assert len(data.book_ids) == 1

    def test_reservation_response(self):
        now = datetime.now(UTC)
        data = {
            "id": uuid.uuid4(),
            "book_id": uuid.uuid4(),
            "user_id": "user-1",
            "reserved_at": now,
            "due_date": now,
            "returned_at": None,
            "status": "ACTIVE",
        }
        response = ReservationResponse(**data)
        assert response.status == "ACTIVE"
        assert response.returned_at is None
