import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from schemas.book import ReservationCreate
from services.book_service import BookService


def _make_book(**kwargs):
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
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def _make_reservation(**kwargs):
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
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


class TestBookServiceListBooks:
    async def test_list_books_returns_from_cache(self):
        cache = AsyncMock()
        now = datetime.now(UTC).isoformat()
        cache.get = AsyncMock(
            return_value=[
                {
                    "id": str(uuid.uuid4()),
                    "isbn": "123",
                    "title": "Test",
                    "author": "A",
                    "genre": "Fiction",
                    "published_year": 2020,
                    "total_copies": 5,
                    "available_copies": 5,
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        )
        session_factory = AsyncMock()
        service = BookService(session_factory, cache)
        result = await service.list_books()
        assert len(result) == 1
        cache.get.assert_called_once()


class TestBookServiceReservation:
    async def test_reserve_books_unavailable_raises(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        book = _make_book(available_copies=0)

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = book
        session.execute = AsyncMock(return_value=result_mock)

        session_factory = MagicMock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        service = BookService(session_factory, cache)
        data = ReservationCreate(user_id="user-1", book_ids=[book.id])

        with pytest.raises(ValueError, match="not available"):
            await service.reserve_books(data)
