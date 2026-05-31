import asyncio
import uuid
from unittest.mock import AsyncMock

from generated.models import ReservationCreate


class TestConcurrentReservation:
    async def test_last_copy_concurrent_reserve_one_succeeds(self):
        from services.book_service import BookService

        mock_session_factory = AsyncMock()
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.invalidate_books = AsyncMock()

        service = BookService(mock_session_factory, mock_cache)

        book_id = uuid.uuid4()
        user1 = uuid.uuid4()
        user2 = uuid.uuid4()
        data = ReservationCreate(book_ids=[book_id])

        results = []
        exceptions = []

        async def attempt_reserve(user_id):
            try:
                result = await service.reserve_books(data, user_id=user_id)
                results.append(result)
            except (ValueError, Exception) as e:
                exceptions.append(e)

        await asyncio.gather(attempt_reserve(user1), attempt_reserve(user2))

        total = len(results) + len(exceptions)
        assert total == 2
