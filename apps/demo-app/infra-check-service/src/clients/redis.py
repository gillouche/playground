import redis.asyncio as redis
from config import RedisConfig


class RedisClient:
    def __init__(self, config: RedisConfig):
        self.config = config
        self.client: redis.Redis | None = None

    async def connect(self):
        self.client = redis.Redis(
            host=self.config.host,
            port=self.config.port,
            password=self.config.password if self.config.password else None,
            decode_responses=True,
        )
        await self.client.ping()

    async def disconnect(self):
        if self.client:
            await self.client.aclose()

    async def set(self, key: str, value: str) -> dict:
        assert self.client is not None
        await self.client.set(key, value)
        return {"key": key, "value": value, "status": "set"}

    async def get(self, key: str | None = None) -> dict:
        assert self.client is not None
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
            assert self.client is not None
            pong = await self.client.ping()
            return {"status": "healthy" if pong else "unhealthy", "host": self.config.host}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
