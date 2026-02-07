from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def postgres_client_mock():
    mock = MagicMock()
    mock.health_check = AsyncMock()
    return mock


@pytest.fixture
def redis_client_mock():
    mock = MagicMock()
    mock.health_check = AsyncMock()
    return mock


@pytest.fixture
def kafka_client_mock():
    mock = MagicMock()
    mock.health_check = AsyncMock()
    return mock


@pytest.fixture
def mongo_client_mock():
    mock = MagicMock()
    mock.health_check = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_root_endpoint():
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "infra-check-service"


@pytest.mark.asyncio
async def test_healthz():
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ready(postgres_client_mock, redis_client_mock, kafka_client_mock, mongo_client_mock):
    import main
    from main import app

    # Setup mocks
    main.clients["postgres"] = postgres_client_mock
    main.clients["redis"] = redis_client_mock
    main.clients["kafka"] = kafka_client_mock
    main.clients["mongo"] = mongo_client_mock

    postgres_client_mock.health_check.return_value = {"status": "healthy"}
    redis_client_mock.health_check.return_value = {"status": "healthy"}
    kafka_client_mock.health_check.return_value = {"status": "healthy"}
    mongo_client_mock.health_check.return_value = {"status": "healthy"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ready_unhealthy(
    postgres_client_mock, redis_client_mock, kafka_client_mock, mongo_client_mock
):
    import main
    from main import app

    # Setup mocks
    main.clients["postgres"] = postgres_client_mock
    main.clients["redis"] = redis_client_mock
    main.clients["kafka"] = kafka_client_mock
    main.clients["mongo"] = mongo_client_mock

    postgres_client_mock.health_check.return_value = {"status": "healthy"}
    # Fail Redis
    redis_client_mock.health_check.return_value = {"status": "unhealthy"}
    kafka_client_mock.health_check.return_value = {"status": "healthy"}
    mongo_client_mock.health_check.return_value = {"status": "healthy"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_info():
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/info")

    assert response.status_code == 200
    assert "hostname" in response.json()


@pytest.mark.asyncio
async def test_postgres_health_endpoint():
    import main

    main.clients["postgres"] = None
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/postgres/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_redis_health_endpoint():
    import main

    main.clients["redis"] = None
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/redis/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_kafka_health_endpoint():
    import main

    main.clients["kafka"] = None
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/kafka/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_mongodb_health_endpoint():
    import main

    main.clients["mongo"] = None
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/mongodb/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_postgres_get_not_connected():
    import main

    main.clients["postgres"] = None
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/postgres")

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_redis_get_not_connected():
    import main

    main.clients["redis"] = None
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/redis")

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_kafka_get_not_connected():
    import main

    main.clients["kafka"] = None
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/kafka")

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_mongodb_get_not_connected():
    import main

    main.clients["mongo"] = None
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/mongodb")

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_postgres_post_not_connected():
    import main

    main.clients["postgres"] = None
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/postgres", json={"key": "k", "value": "v"})

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_redis_post_not_connected():
    import main

    main.clients["redis"] = None
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/redis", json={"key": "k", "value": "v"})

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_kafka_post_not_connected():
    import main

    main.clients["kafka"] = None
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/kafka", json={"message": "m"})

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_mongodb_post_not_connected():
    import main

    main.clients["mongo"] = None
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/mongodb", json={"key": "k", "value": "v"})

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_postgres_with_mocked_client():
    import main

    mock_pg = MagicMock()
    mock_pg.engine = True
    mock_pg.read = AsyncMock(return_value=[{"key": "k", "value": "v"}])
    mock_pg.write = AsyncMock(return_value={"status": "written"})
    mock_pg.health_check = AsyncMock(return_value={"status": "healthy"})
    main.clients["postgres"] = mock_pg
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/postgres")
    assert response.status_code == 200

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/postgres", json={"key": "k", "value": "v"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_redis_with_mocked_client():
    import main

    mock_redis = MagicMock()
    mock_redis.client = True
    mock_redis.get = AsyncMock(return_value={"key": "k", "value": "v"})
    mock_redis.set = AsyncMock(return_value={"status": "set"})
    mock_redis.health_check = AsyncMock(return_value={"status": "healthy"})
    main.clients["redis"] = mock_redis
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/redis?key=k")
    assert response.status_code == 200

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/redis", json={"key": "k", "value": "v"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_kafka_with_mocked_client():
    import main

    mock_kafka = MagicMock()
    mock_kafka.producer = True
    mock_kafka.consume = AsyncMock(return_value=[{"topic": "t", "value": "v"}])
    mock_kafka.produce = AsyncMock(return_value={"status": "produced"})
    mock_kafka.health_check = AsyncMock(return_value={"status": "healthy"})
    main.clients["kafka"] = mock_kafka
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/kafka")
    assert response.status_code == 200

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/kafka", json={"message": "m"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_mongodb_with_mocked_client():
    import main

    mock_mongo = MagicMock()
    mock_mongo.client = True
    mock_mongo.find = AsyncMock(return_value=[{"key": "k", "value": "v"}])
    mock_mongo.insert = AsyncMock(return_value={"status": "inserted"})
    mock_mongo.health_check = AsyncMock(return_value={"status": "healthy"})
    main.clients["mongo"] = mock_mongo
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/mongodb")
    assert response.status_code == 200

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/mongodb", json={"key": "k", "value": "v"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_lifespan_startup_errors():
    from main import app, lifespan

    with (
        patch("clients.postgres.PostgresClient.connect", side_effect=ConnectionError("pg fail")),
        patch("clients.redis.RedisClient.connect", side_effect=ConnectionError("redis fail")),
        patch("clients.kafka.KafkaClient.connect", side_effect=ConnectionError("kafka fail")),
        patch("clients.mongodb.MongoClient.connect", side_effect=ConnectionError("mongo fail")),
        pytest.raises(ConnectionError),
    ):
        async with lifespan(app):
            pass
