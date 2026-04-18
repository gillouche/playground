from config import postgres_config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(
    postgres_config.url,
    pool_pre_ping=postgres_config.pool_pre_ping,
    pool_size=postgres_config.pool_size,
    max_overflow=postgres_config.max_overflow,
    echo=False,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session_factory() as session:
        yield session
