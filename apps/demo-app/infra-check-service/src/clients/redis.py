from typing import Optional
import redis.asyncio as redis
from config import RedisConfig


class RedisClient:
    def __init__(self, config: RedisConfig):
        self.config = config
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        self.client = redis.Redis(
            host=self.config.host,
            port=self.config.port,
            password=self.config.password if self.config.password else None,
            decode_responses=True
        )
        await self.client.ping()

    async def disconnect(self):
        if self.client:
            await self.client.aclose()

    async def set(self, key: str, value: str) -> dict:
        await self.client.set(key, value)
        return {"key": key, "value": value, "status": "set"}

    async def get(self, key: Optional[str] = None) -> dict:
        if key:
            value = await self.client.get(key)
            return {"key": key, "value": value}
        else:
            keys = await self.client.keys("*")
            result = {}
            for k in keys[:100]:
                result[k] = await self.client.get(k)
            return {"keys": result}

    async def health_check(self) -> dict:
        try:
            pong = await self.client.ping()
            return {"status": "healthy" if pong else "unhealthy", "host": self.config.host}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
