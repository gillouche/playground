from unittest.mock import AsyncMock, MagicMock

import pytest
from clients.postgres import PostgresClient
from config import PostgresConfig


@pytest.fixture
def postgres_config():
    return PostgresConfig(
        host="localhost", port=5432, database="test", user="test", password="test"
    )


@pytest.mark.asyncio
async def test_postgres_client_init(postgres_config):
    client = PostgresClient(postgres_config)
    assert client.config == postgres_config
    assert client.engine is None


@pytest.mark.asyncio
async def test_postgres_health_check_not_initialized(postgres_config):
    client = PostgresClient(postgres_config)
    client.session_factory = None
    result = await client.health_check()
    assert "error" in result or result.get("status") == "not initialized"


@pytest.mark.asyncio
async def test_postgres_health_check_healthy(postgres_config):
    client = PostgresClient(postgres_config)
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = (1,)
    mock_session.execute = AsyncMock(return_value=mock_result)
    client.session_factory = MagicMock(return_value=mock_session)

    result = await client.health_check()
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_postgres_health_check_unhealthy(postgres_config):
    client = PostgresClient(postgres_config)
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(side_effect=Exception("Connection failed"))
    client.session_factory = MagicMock(return_value=mock_session)

    result = await client.health_check()
    assert result["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_postgres_write_mock(postgres_config):
    client = PostgresClient(postgres_config)
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    client.session_factory = MagicMock(return_value=mock_session)

    result = await client.write("key1", "value1")
    assert result["key"] == "key1"
    assert result["value"] == "value1"
    assert result["status"] == "written"


@pytest.mark.asyncio
async def test_postgres_read_mock(postgres_config):
    client = PostgresClient(postgres_config)
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("key1", "value1", "2024-01-01")]
    mock_session.execute = AsyncMock(return_value=mock_result)
    client.session_factory = MagicMock(return_value=mock_session)

    result = await client.read()
    assert len(result) == 1
    assert result[0]["key"] == "key1"


@pytest.mark.asyncio
async def test_postgres_read_with_key_mock(postgres_config):
    client = PostgresClient(postgres_config)
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("mykey", "myvalue", "2024-01-01")]
    mock_session.execute = AsyncMock(return_value=mock_result)
    client.session_factory = MagicMock(return_value=mock_session)

    result = await client.read("mykey")
    assert len(result) == 1
    assert result[0]["key"] == "mykey"
