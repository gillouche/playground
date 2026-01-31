import pytest
from unittest.mock import AsyncMock, MagicMock
from clients.kafka import KafkaClient
from config import KafkaConfig


@pytest.fixture
def kafka_config():
    return KafkaConfig(bootstrap_servers="localhost:9092", topic="test-topic")


@pytest.mark.asyncio
async def test_kafka_client_init(kafka_config):
    client = KafkaClient(kafka_config)
    assert client.config == kafka_config
    assert client.producer is None


@pytest.mark.asyncio
async def test_kafka_produce_mock(kafka_config):
    client = KafkaClient(kafka_config)
    client.producer = AsyncMock()
    client.producer.send_and_wait = AsyncMock()

    result = await client.produce("test message")
    assert result["topic"] == "test-topic"
    assert result["message"] == "test message"
    assert result["status"] == "produced"


@pytest.mark.asyncio
async def test_kafka_produce_custom_topic(kafka_config):
    client = KafkaClient(kafka_config)
    client.producer = AsyncMock()
    client.producer.send_and_wait = AsyncMock()

    result = await client.produce("msg", "custom-topic")
    assert result["topic"] == "custom-topic"


@pytest.mark.asyncio
async def test_kafka_health_check_healthy(kafka_config):
    client = KafkaClient(kafka_config)
    client.producer = AsyncMock()
    mock_metadata = MagicMock()
    mock_metadata.topics.return_value = ["topic1", "topic2"]
    client.producer.client = MagicMock()
    client.producer.client.fetch_all_metadata = AsyncMock(return_value=mock_metadata)

    result = await client.health_check()
    assert result["status"] == "healthy"
    assert "topics" in result


@pytest.mark.asyncio
async def test_kafka_health_check_unhealthy(kafka_config):
    client = KafkaClient(kafka_config)
    client.producer = AsyncMock()
    client.producer.client = MagicMock()
    client.producer.client.fetch_all_metadata = AsyncMock(side_effect=Exception("Failed"))

    result = await client.health_check()
    assert result["status"] == "unhealthy"
