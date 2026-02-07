from unittest.mock import AsyncMock, MagicMock

import pytest
from clients.mongodb import MongoClient
from config import MongoDBConfig


@pytest.fixture
def mongodb_config():
    return MongoDBConfig(
        host="localhost", port=27017, database="test", user="test", password="test"
    )


@pytest.mark.asyncio
async def test_mongodb_client_init(mongodb_config):
    client = MongoClient(mongodb_config)
    assert client.config == mongodb_config
    assert client.client is None


@pytest.mark.asyncio
async def test_mongodb_insert_mock(mongodb_config):
    client = MongoClient(mongodb_config)
    client.collection = AsyncMock()
    client.collection.update_one = AsyncMock()

    result = await client.insert("key1", "value1")
    assert result["key"] == "key1"
    assert result["value"] == "value1"
    assert result["status"] == "inserted"


@pytest.mark.asyncio
async def test_mongodb_find_all_mock(mongodb_config):
    client = MongoClient(mongodb_config)
    mock_cursor = MagicMock()
    mock_cursor.limit.return_value = mock_cursor

    async def async_gen():
        yield {"key": "k1", "value": "v1", "created_at": "2024-01-01"}
        yield {"key": "k2", "value": "v2", "created_at": "2024-01-01"}

    mock_cursor.__aiter__ = lambda _self: async_gen()
    client.collection = MagicMock()
    client.collection.find.return_value = mock_cursor

    result = await client.find()
    assert len(result) == 2


@pytest.mark.asyncio
async def test_mongodb_find_by_key_mock(mongodb_config):
    client = MongoClient(mongodb_config)
    mock_cursor = MagicMock()
    mock_cursor.limit.return_value = mock_cursor

    async def async_gen():
        yield {"key": "mykey", "value": "myvalue", "created_at": "2024-01-01"}

    mock_cursor.__aiter__ = lambda _self: async_gen()
    client.collection = MagicMock()
    client.collection.find.return_value = mock_cursor

    result = await client.find("mykey")
    assert len(result) == 1
    assert result[0]["key"] == "mykey"


@pytest.mark.asyncio
async def test_mongodb_health_check_healthy(mongodb_config):
    client = MongoClient(mongodb_config)
    client.client = MagicMock()
    client.client.admin = MagicMock()
    client.client.admin.command = AsyncMock(return_value={"ok": 1})

    result = await client.health_check()
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_mongodb_health_check_unhealthy(mongodb_config):
    client = MongoClient(mongodb_config)
    client.client = MagicMock()
    client.client.admin = MagicMock()
    client.client.admin.command = AsyncMock(side_effect=Exception("Failed"))

    result = await client.health_check()
    assert result["status"] == "unhealthy"


def test_mongodb_url_with_auth(mongodb_config):
    assert "test:test@localhost" in mongodb_config.url


def test_mongodb_url_without_auth():
    config = MongoDBConfig(host="localhost", port=27017, database="test", user="", password="")
    assert config.url == "mongodb://localhost:27017"
