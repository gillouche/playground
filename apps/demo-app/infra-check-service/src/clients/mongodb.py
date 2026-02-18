import os
from datetime import UTC, datetime

from config import MongoDBConfig
from motor.motor_asyncio import AsyncIOMotorClient


class MongoClient:
    def __init__(self, config: MongoDBConfig):
        self.config = config
        self.client: AsyncIOMotorClient | None = None
        self.db = None
        self.collection = None

    async def connect(self):
        kwargs: dict = {"host": self.config.host, "port": self.config.port}
        password = os.environ.get("MONGODB_PASSWORD", "")
        if self.config.user and password:
            kwargs["username"] = self.config.user
            kwargs["password"] = password
        self.client = AsyncIOMotorClient(**kwargs)
        self.db = self.client[self.config.database]
        self.collection = self.db["infra_check"]
        await self.client.admin.command("ping")

    async def disconnect(self):
        if self.client:
            self.client.close()

    async def insert(self, key: str, value: str) -> dict:
        assert self.collection is not None
        doc = {"key": key, "value": value, "created_at": datetime.now(UTC)}
        await self.collection.update_one({"key": key}, {"$set": doc}, upsert=True)
        return {"key": key, "value": value, "status": "inserted"}

    async def find(self, key: str | None = None) -> list[dict]:
        assert self.collection is not None
        query = {"key": key} if key else {}
        cursor = self.collection.find(query).limit(100)
        docs = []
        async for doc in cursor:
            docs.append(
                {
                    "key": doc.get("key"),
                    "value": doc.get("value"),
                    "created_at": str(doc.get("created_at")),
                }
            )
        return docs

    async def health_check(self) -> dict:
        try:
            assert self.client is not None
            await self.client.admin.command("ping")
            return {"status": "healthy", "host": self.config.host}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
