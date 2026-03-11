from unittest.mock import AsyncMock

import pytest
from cache.redis_cache import RedisCache


class TestRedisCache:
    @pytest.fixture
    def cache(self):
        c = RedisCache()
        c._redis = AsyncMock()
        return c

    async def test_get_returns_parsed_json(self, cache):
        cache._redis.get = AsyncMock(return_value='{"key": "value"}')
        result = await cache.get("test-key")
        assert result == {"key": "value"}

    async def test_get_returns_none_on_miss(self, cache):
        cache._redis.get = AsyncMock(return_value=None)
        result = await cache.get("test-key")
        assert result is None

    async def test_get_returns_none_when_not_connected(self):
        cache = RedisCache()
        result = await cache.get("test-key")
        assert result is None

    async def test_set_stores_json(self, cache):
        await cache.set("test-key", {"key": "value"}, ttl=30)
        cache._redis.set.assert_called_once()

    async def test_delete(self, cache):
        await cache.delete("test-key")
        cache._redis.delete.assert_called_once()

    async def test_health_check_success(self, cache):
        cache._redis.ping = AsyncMock(return_value=True)
        assert await cache.health_check() is True

    async def test_health_check_failure(self):
        cache = RedisCache()
        assert await cache.health_check() is False

    async def test_invalidate_books(self, cache):
        cache._redis.scan = AsyncMock(return_value=(0, []))
        await cache.invalidate_books()
        # Should delete books:all and inventory keys
        assert cache._redis.delete.call_count >= 2
