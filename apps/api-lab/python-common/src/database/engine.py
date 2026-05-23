from config import postgres_config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

engine = create_async_engine(
    postgres_config.url,
    pool_pre_ping=postgres_config.pool_pre_ping,
    pool_size=postgres_config.pool_size,
    max_overflow=postgres_config.max_overflow,
    pool_recycle=postgres_config.pool_recycle_seconds,
    pool_timeout=postgres_config.pool_timeout_seconds,
    connect_args={
        "timeout": postgres_config.connect_timeout_seconds,
        "server_settings": {
            "statement_timeout": str(postgres_config.statement_timeout_ms),
            "application_name": "api-lab",
        },
    },
    echo=False,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session_factory() as session:
        yield session
