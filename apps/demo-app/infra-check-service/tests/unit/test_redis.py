import pytest
from unittest.mock import AsyncMock
from clients.redis import RedisClient
from config import RedisConfig


@pytest.fixture
def redis_config():
    return RedisConfig(host="localhost", port=6379, password="test")


@pytest.mark.asyncio
async def test_redis_client_init(redis_config):
    client = RedisClient(redis_config)
    assert client.config == redis_config
    assert client.client is None


@pytest.mark.asyncio
async def test_redis_set_mock(redis_config):
    client = RedisClient(redis_config)
    client.client = AsyncMock()
    client.client.set = AsyncMock()

    result = await client.set("key1", "value1")
    assert result["key"] == "key1"
    assert result["value"] == "value1"
    assert result["status"] == "set"
    client.client.set.assert_called_once_with("key1", "value1")


@pytest.mark.asyncio
async def test_redis_get_with_key_mock(redis_config):
    client = RedisClient(redis_config)
    client.client = AsyncMock()
    client.client.get = AsyncMock(return_value="myvalue")

    result = await client.get("mykey")
    assert result["key"] == "mykey"
    assert result["value"] == "myvalue"


@pytest.mark.asyncio
async def test_redis_get_all_keys_mock(redis_config):
    client = RedisClient(redis_config)
    client.client = AsyncMock()
    client.client.keys = AsyncMock(return_value=["k1", "k2"])
    client.client.get = AsyncMock(side_effect=["v1", "v2"])

    result = await client.get()
    assert "keys" in result
    assert result["keys"]["k1"] == "v1"
    assert result["keys"]["k2"] == "v2"


@pytest.mark.asyncio
async def test_redis_health_check_healthy(redis_config):
    client = RedisClient(redis_config)
    client.client = AsyncMock()
    client.client.ping = AsyncMock(return_value=True)

    result = await client.health_check()
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_redis_health_check_unhealthy(redis_config):
    client = RedisClient(redis_config)
    client.client = AsyncMock()
    client.client.ping = AsyncMock(side_effect=Exception("Connection failed"))

    result = await client.health_check()
    assert result["status"] == "unhealthy"
    assert "error" in result
