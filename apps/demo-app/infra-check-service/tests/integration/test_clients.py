from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from clients.kafka import KafkaClient
from clients.mongodb import MongoClient
from clients.postgres import PostgresClient
from clients.redis import RedisClient
from config import KafkaConfig, MongoDBConfig, PostgresConfig, RedisConfig, load_config


def test_config_loading():
    config = load_config()
    assert config.postgres.host is not None
    assert config.redis.host is not None
    assert config.kafka.bootstrap_servers is not None
    assert config.mongodb.host is not None


@pytest.fixture
def postgres_config():
    return PostgresConfig(
        host="localhost", port=5432, database="test", user="test", password="test"
    )


@pytest.fixture
def redis_config():
    return RedisConfig(host="localhost", port=6379, password="test")


@pytest.fixture
def kafka_config():
    return KafkaConfig(bootstrap_servers="localhost:9092", topic="test")


@pytest.fixture
def mongodb_config():
    return MongoDBConfig(host="localhost", port=27017, database="test", user="test")


@pytest.mark.asyncio
async def test_postgres_client_write(postgres_config):
    client = PostgresClient(postgres_config)
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    client.session_factory = MagicMock(return_value=mock_session)

    result = await client.write("k", "v")
    assert result["status"] == "written"


@pytest.mark.asyncio
async def test_postgres_client_read(postgres_config):
    client = PostgresClient(postgres_config)
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("k", "v", "2024-01-01")]
    mock_session.execute = AsyncMock(return_value=mock_result)
    client.session_factory = MagicMock(return_value=mock_session)

    result = await client.read()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_postgres_client_health(postgres_config):
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
async def test_redis_client_set(redis_config):
    client = RedisClient(redis_config)
    client.client = AsyncMock()
    client.client.set = AsyncMock()

    result = await client.set("k", "v")
    assert result["status"] == "set"


@pytest.mark.asyncio
async def test_redis_client_get(redis_config):
    client = RedisClient(redis_config)
    client.client = AsyncMock()
    client.client.get = AsyncMock(return_value="v")

    result = await client.get("k")
    assert result["value"] == "v"


@pytest.mark.asyncio
async def test_redis_client_get_all(redis_config):
    client = RedisClient(redis_config)
    client.client = AsyncMock()
    client.client.keys = AsyncMock(return_value=["k1", "k2"])
    client.client.get = AsyncMock(side_effect=["v1", "v2"])

    result = await client.get()
    assert "keys" in result


@pytest.mark.asyncio
async def test_redis_client_health(redis_config):
    client = RedisClient(redis_config)
    client.client = AsyncMock()
    client.client.ping = AsyncMock(return_value=True)

    result = await client.health_check()
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_kafka_client_produce(kafka_config):
    client = KafkaClient(kafka_config)
    client.producer = AsyncMock()
    client.producer.send_and_wait = AsyncMock()

    result = await client.produce("msg")
    assert result["status"] == "produced"


@pytest.mark.asyncio
async def test_kafka_client_health(kafka_config):
    client = KafkaClient(kafka_config)
    client.producer = AsyncMock()
    mock_metadata = MagicMock()
    mock_metadata.topics.return_value = ["t1"]
    client.producer.client = MagicMock()
    client.producer.client.fetch_all_metadata = AsyncMock(return_value=mock_metadata)

    result = await client.health_check()
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_kafka_client_health_unhealthy(kafka_config):
    client = KafkaClient(kafka_config)
    client.producer = AsyncMock()
    client.producer.client = MagicMock()
    client.producer.client.fetch_all_metadata = AsyncMock(side_effect=Exception("fail"))

    result = await client.health_check()
    assert result["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_kafka_client_produce_custom_topic(kafka_config):
    client = KafkaClient(kafka_config)
    client.producer = AsyncMock()
    client.producer.send_and_wait = AsyncMock()

    result = await client.produce("msg", "custom-topic")
    assert result["topic"] == "custom-topic"


@pytest.mark.asyncio
async def test_kafka_client_consume_success(kafka_config):
    client = KafkaClient(kafka_config)
    mock_consumer = AsyncMock()
    mock_consumer.start = AsyncMock()
    mock_consumer.stop = AsyncMock()

    # Mock getmany to return messages then empty
    msg = MagicMock()
    msg.topic = "t"
    msg.partition = 0
    msg.offset = 0
    msg.value = b"v"

    mock_consumer.getmany = AsyncMock(side_effect=[{("t", 0): [msg]}, {}])

    with patch("clients.kafka.AIOKafkaConsumer", return_value=mock_consumer):
        result = await client.consume(timeout=0.1)

    assert len(result) == 1
    assert result[0]["value"] == "v"


@pytest.mark.asyncio
async def test_kafka_client_consume_timeout(kafka_config):
    client = KafkaClient(kafka_config)
    mock_consumer = AsyncMock()
    mock_consumer.start = AsyncMock()
    mock_consumer.stop = AsyncMock()
    mock_consumer.getmany = AsyncMock(return_value={})

    with patch("clients.kafka.AIOKafkaConsumer", return_value=mock_consumer):
        result = await client.consume(timeout=0.1)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_kafka_client_disconnect(kafka_config):
    client = KafkaClient(kafka_config)
    client.producer = AsyncMock()
    await client.disconnect()
    client.producer.stop.assert_called_once()


@pytest.mark.asyncio
async def test_kafka_client_disconnect_no_producer(kafka_config):
    client = KafkaClient(kafka_config)
    client.producer = None
    await client.disconnect()  # Should not raise


@pytest.mark.asyncio
async def test_postgres_health_unhealthy(postgres_config):
    client = PostgresClient(postgres_config)
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(side_effect=Exception("fail"))
    client.session_factory = MagicMock(return_value=mock_session)

    result = await client.health_check()
    assert result["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_redis_health_unhealthy(redis_config):
    client = RedisClient(redis_config)
    client.client = AsyncMock()
    client.client.ping = AsyncMock(side_effect=Exception("fail"))

    result = await client.health_check()
    assert result["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_mongodb_health_unhealthy(mongodb_config):
    client = MongoClient(mongodb_config)
    client.client = MagicMock()
    client.client.admin = MagicMock()
    client.client.admin.command = AsyncMock(side_effect=Exception("fail"))

    result = await client.health_check()
    assert result["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_mongodb_client_insert(mongodb_config):
    client = MongoClient(mongodb_config)
    client.collection = AsyncMock()
    client.collection.update_one = AsyncMock()

    result = await client.insert("k", "v")
    assert result["status"] == "inserted"


@pytest.mark.asyncio
async def test_mongodb_client_find(mongodb_config):
    client = MongoClient(mongodb_config)
    mock_cursor = MagicMock()
    mock_cursor.limit.return_value = mock_cursor

    async def async_gen():
        yield {"key": "k", "value": "v", "created_at": "2024-01-01"}

    mock_cursor.__aiter__ = lambda _self: async_gen()
    client.collection = MagicMock()
    client.collection.find.return_value = mock_cursor

    result = await client.find()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_mongodb_client_health(mongodb_config):
    client = MongoClient(mongodb_config)
    client.client = MagicMock()
    client.client.admin = MagicMock()
    client.client.admin.command = AsyncMock(return_value={"ok": 1})

    result = await client.health_check()
    assert result["status"] == "healthy"
