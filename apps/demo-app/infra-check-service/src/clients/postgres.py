from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from config import PostgresConfig


class PostgresClient:
    def __init__(self, config: PostgresConfig):
        self.config = config
        self.engine = None
        self.session_factory = None

    async def connect(self):
        self.engine = create_async_engine(self.config.url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS infra_check (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

    async def disconnect(self):
        if self.engine:
            await self.engine.dispose()

    async def write(self, key: str, value: str) -> dict:
        async with self.session_factory() as session:
            await session.execute(
                text("INSERT INTO infra_check (key, value) VALUES (:key, :value) ON CONFLICT (key) DO UPDATE SET value = :value"),
                {"key": key, "value": value}
            )
            await session.commit()
        return {"key": key, "value": value, "status": "written"}

    async def read(self, key: Optional[str] = None) -> list[dict]:
        async with self.session_factory() as session:
            if key:
                result = await session.execute(
                    text("SELECT key, value, created_at FROM infra_check WHERE key = :key"),
                    {"key": key}
                )
            else:
                result = await session.execute(text("SELECT key, value, created_at FROM infra_check"))
            rows = result.fetchall()
            return [{"key": row[0], "value": row[1], "created_at": str(row[2])} for row in rows]

    async def health_check(self) -> dict:
        try:
            async with self.session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                result.fetchone()
            return {"status": "healthy", "host": self.config.host}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
