import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from generated.models import ListBooksQuery, PaginatedBooks, ReservationCreate
from services.book_service import (
    ActiveReservationsError,
    BookService,
    StaleVersionError,
    _decode_continuation_token,
    _encode_continuation_token,
)


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
        "version": 1,
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
        "user_id": uuid.uuid4(),
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
        book_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        cache.get = AsyncMock(
            return_value={
                "items": [
                    {
                        "id": book_id,
                        "isbn": "123",
                        "title": "Test",
                        "author": "A",
                        "genre": "Fiction",
                        "published_year": 2020,
                        "total_copies": 5,
                        "available_copies": 5,
                        "version": 1,
                        "created_at": now,
                        "updated_at": now,
                    }
                ],
                "continuation_token": None,
                "has_more": False,
            }
        )
        session_factory = AsyncMock()
        service = BookService(session_factory, cache)
        result = await service.list_books()
        assert isinstance(result, PaginatedBooks)
        assert len(result.items) == 1
        cache.get.assert_called_once()

    async def test_list_books_pagination_limit_clamping(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        session_factory = MagicMock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        service = BookService(session_factory, cache)
        result = await service.list_books(ListBooksQuery(limit=200))
        assert isinstance(result, PaginatedBooks)
        assert result.has_more is False

    async def test_list_books_sorting(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        session_factory = MagicMock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        service = BookService(session_factory, cache)
        result = await service.list_books(ListBooksQuery(sort_by="title", sort_order="desc"))
        assert isinstance(result, PaginatedBooks)

    async def test_list_books_full_text_search(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        session_factory = MagicMock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        service = BookService(session_factory, cache)
        result = await service.list_books(ListBooksQuery(search="java programming"))
        assert isinstance(result, PaginatedBooks)
        session.execute.assert_called_once()


class TestContinuationTokenEncoding:
    def test_encode_decode_roundtrip(self):
        token = _encode_continuation_token(42)
        assert _decode_continuation_token(token) == 42

    def test_decode_none_returns_zero(self):
        assert _decode_continuation_token(None) == 0

    def test_decode_empty_string_returns_zero(self):
        assert _decode_continuation_token("") == 0

    def test_decode_invalid_returns_zero(self):
        assert _decode_continuation_token("not-valid-base64!!!") == 0


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
        data = ReservationCreate(user_id=uuid.uuid4(), book_ids=[book.id])

        with pytest.raises(ValueError, match="not available"):
            await service.reserve_books(data)


class TestBookServiceUpdateBook:
    async def test_update_book_version_mismatch(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        book = _make_book(version=5)

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = book
        session.execute = AsyncMock(return_value=result_mock)

        session_factory = MagicMock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        from generated.models import BookUpdate

        service = BookService(session_factory, cache)
        data = BookUpdate(title="Updated")

        with pytest.raises(StaleVersionError):
            await service.update_book(uuid.uuid4(), data, expected_version=1)

    async def test_update_book_increments_version(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.invalidate_books = AsyncMock()
        cache.set = AsyncMock()
        book = _make_book(version=1)
        book.id = uuid.uuid4()

        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = book
        session.execute = AsyncMock(return_value=result_mock)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        session_factory = MagicMock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        from generated.models import BookUpdate

        service = BookService(session_factory, cache)
        data = BookUpdate(title="Updated")

        await service.update_book(book.id, data, expected_version=1)
        assert book.version == 2


class TestBookServiceDeleteBook:
    async def test_delete_book_with_active_reservations(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        book = _make_book()

        session = AsyncMock()
        book_result_mock = MagicMock()
        book_result_mock.scalar_one_or_none.return_value = book

        count_result_mock = MagicMock()
        count_result_mock.scalar.return_value = 3

        session.execute = AsyncMock(side_effect=[book_result_mock, count_result_mock])

        session_factory = MagicMock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        service = BookService(session_factory, cache)

        with pytest.raises(ActiveReservationsError):
            await service.delete_book(book.id)
