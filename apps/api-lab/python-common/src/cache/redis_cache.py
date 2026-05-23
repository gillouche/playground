import base64
import json
import logging
from typing import Any

import redis.asyncio as aioredis
from config import cache_config, redis_config

logger = logging.getLogger("api-lab.cache")

CACHE_PREFIX = "api-lab"
BOOKS_ALL_TTL = cache_config.books_all_ttl
BOOK_TTL = cache_config.book_ttl
INVENTORY_TTL = cache_config.inventory_ttl


class RedisCache:
    def __init__(self):
        self._redis: aioredis.Redis | None = None

    @property
    def client(self) -> aioredis.Redis | None:
        return self._redis

    async def connect(self):
        self._redis = aioredis.from_url(redis_config.url, decode_responses=True)
        logger.info("Connected to Redis")

    async def disconnect(self):
        if self._redis:
            await self._redis.aclose()
            logger.info("Disconnected from Redis")

    async def health_check(self) -> bool:
        try:
            if self._redis:
                return await self._redis.ping()
            return False
        except Exception:
            return False

    async def get(self, key: str) -> Any | None:
        if not self._redis:
            return None
        try:
            data = await self._redis.get(f"{CACHE_PREFIX}:{key}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 60):
        if not self._redis:
            return
        try:
            await self._redis.set(f"{CACHE_PREFIX}:{key}", json.dumps(value, default=str), ex=ttl)
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")

    async def delete(self, key: str):
        if not self._redis:
            return
        try:
            await self._redis.delete(f"{CACHE_PREFIX}:{key}")
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")

    async def delete_pattern(self, pattern: str):
        if not self._redis:
            return
        try:
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(
                    cursor, match=f"{CACHE_PREFIX}:{pattern}", count=100
                )
                if keys:
                    await self._redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning(f"Cache delete_pattern error for {pattern}: {e}")

    async def invalidate_books(self):
        await self.delete("books:all")
        await self.delete("inventory")
        await self.delete_pattern("books:*")

    async def get_bytes(self, key: str) -> bytes | None:
        if not self._redis:
            return None
        try:
            encoded = await self._redis.get(f"{CACHE_PREFIX}:{key}")
            if encoded is None:
                return None
            return base64.b64decode(encoded)
        except Exception as e:
            logger.warning("Cache get_bytes error for %s: %s", key, e)
            return None

    async def set_bytes(self, key: str, value: bytes, ttl: int = 60) -> None:
        if not self._redis:
            return
        try:
            encoded = base64.b64encode(value).decode("ascii")
            await self._redis.set(f"{CACHE_PREFIX}:{key}", encoded, ex=ttl)
        except Exception as e:
            logger.warning("Cache set_bytes error for %s: %s", key, e)
