from typing import Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from config import MongoDBConfig


class MongoClient:
    def __init__(self, config: MongoDBConfig):
        self.config = config
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.collection = None

    async def connect(self):
        self.client = AsyncIOMotorClient(self.config.url)
        self.db = self.client[self.config.database]
        self.collection = self.db["infra_check"]
        await self.client.admin.command("ping")

    async def disconnect(self):
        if self.client:
            self.client.close()

    async def insert(self, key: str, value: str) -> dict:
        doc = {
            "key": key,
            "value": value,
            "created_at": datetime.now(timezone.utc)
        }
        await self.collection.update_one(
            {"key": key},
            {"$set": doc},
            upsert=True
        )
        return {"key": key, "value": value, "status": "inserted"}

    async def find(self, key: Optional[str] = None) -> list[dict]:
        query = {"key": key} if key else {}
        cursor = self.collection.find(query).limit(100)
        docs = []
        async for doc in cursor:
            docs.append({
                "key": doc.get("key"),
                "value": doc.get("value"),
                "created_at": str(doc.get("created_at"))
            })
        return docs

    async def health_check(self) -> dict:
        try:
            await self.client.admin.command("ping")
            return {"status": "healthy", "host": self.config.host}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
