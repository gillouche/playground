from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_clients():
    # Create mocks
    pg = MagicMock()
    redis = MagicMock()
    kafka = MagicMock()
    mongo = MagicMock()

    # Setup default mocks to simulate connected clients
    pg.engine = True
    pg.read = AsyncMock(return_value=[])
    pg.write = AsyncMock(return_value={})
    pg.health_check = AsyncMock(return_value={"status": "healthy"})

    redis.client = True
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value={})
    redis.health_check = AsyncMock(return_value={"status": "healthy"})

    kafka.producer = True
    kafka.consume = AsyncMock(return_value=[])
    kafka.produce = AsyncMock(return_value={})
    kafka.health_check = AsyncMock(return_value={"status": "healthy"})

    mongo.client = True
    mongo.find = AsyncMock(return_value=[])
    mongo.insert = AsyncMock(return_value={})
    mongo.health_check = AsyncMock(return_value={"status": "healthy"})

    # Patch the clients dictionary
    with patch.dict(
        "main.clients", {"postgres": pg, "redis": redis, "kafka": kafka, "mongo": mongo}
    ):
        yield {"postgres": pg, "redis": redis, "kafka": kafka, "mongodb": mongo}


@pytest.mark.asyncio
async def test_root_endpoint(_mock_clients):
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "/postgres" in data["endpoints"]


@pytest.mark.asyncio
async def test_healthz():
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_ready(mock_clients):
    mock_clients["postgres"].health_check = AsyncMock(return_value={"status": "healthy"})
    mock_clients["redis"].health_check = AsyncMock(return_value={"status": "healthy"})
    mock_clients["kafka"].health_check = AsyncMock(return_value={"status": "healthy"})
    mock_clients["mongodb"].health_check = AsyncMock(return_value={"status": "healthy"})

    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_info():
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/info")

    assert response.status_code == 200
    data = response.json()
    assert "hostname" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_postgres_get_not_connected():
    import main

    with patch.dict(main.clients, {"postgres": None}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/postgres")

        assert response.status_code == 503


@pytest.mark.asyncio
async def test_postgres_post_not_connected():
    import main

    with patch.dict(main.clients, {"postgres": None}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/postgres", json={"key": "k", "value": "v"})

        assert response.status_code == 503


@pytest.mark.asyncio
async def test_redis_get_not_connected():
    import main

    with patch.dict(main.clients, {"redis": None}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/redis")

        assert response.status_code == 503


@pytest.mark.asyncio
async def test_redis_post_not_connected():
    import main

    with patch.dict(main.clients, {"redis": None}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/redis", json={"key": "k", "value": "v"})

        assert response.status_code == 503


@pytest.mark.asyncio
async def test_kafka_get_not_connected():
    import main

    with patch.dict(main.clients, {"kafka": None}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/kafka")

        assert response.status_code == 503


@pytest.mark.asyncio
async def test_kafka_post_not_connected():
    import main

    with patch.dict(main.clients, {"kafka": None}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/kafka", json={"message": "m"})

        assert response.status_code == 503


@pytest.mark.asyncio
async def test_mongodb_get_not_connected():
    import main

    with patch.dict(main.clients, {"mongo": None}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/mongodb")

        assert response.status_code == 503


@pytest.mark.asyncio
async def test_mongodb_post_not_connected():
    import main

    with patch.dict(main.clients, {"mongo": None}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/mongodb", json={"key": "k", "value": "v"})

        assert response.status_code == 503


@pytest.mark.asyncio
async def test_postgres_health_endpoint():
    import main

    with patch.dict(main.clients, {"postgres": None}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/postgres/health")

        assert response.status_code == 200
        assert response.json()["status"] == "not initialized"


@pytest.mark.asyncio
async def test_redis_health_endpoint():
    import main

    with patch.dict(main.clients, {"redis": None}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/redis/health")

        assert response.status_code == 200
        assert response.json()["status"] == "not initialized"


@pytest.mark.asyncio
async def test_kafka_health_endpoint():
    import main

    with patch.dict(main.clients, {"kafka": None}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/kafka/health")

        assert response.status_code == 200
        assert response.json()["status"] == "not initialized"


@pytest.mark.asyncio
async def test_mongodb_health_endpoint():
    import main

    with patch.dict(main.clients, {"mongo": None}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/mongodb/health")

        assert response.status_code == 200
        assert response.json()["status"] == "not initialized"


@pytest.mark.asyncio
async def test_postgres_get_with_mocked_client():
    import main

    mock_pg = MagicMock()
    mock_pg.engine = True
    mock_pg.read = AsyncMock(return_value=[{"key": "k", "value": "v"}])

    with patch.dict(main.clients, {"postgres": mock_pg}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/postgres")

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_postgres_post_with_mocked_client():
    import main

    mock_pg = MagicMock()
    mock_pg.engine = True
    mock_pg.write = AsyncMock(return_value={"key": "k", "value": "v", "status": "written"})

    with patch.dict(main.clients, {"postgres": mock_pg}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/postgres", json={"key": "k", "value": "v"})

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_redis_get_with_mocked_client():
    import main

    mock_redis = MagicMock()
    mock_redis.client = True
    mock_redis.get = AsyncMock(return_value={"key": "k", "value": "v"})

    with patch.dict(main.clients, {"redis": mock_redis}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/redis?key=k")

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_redis_post_with_mocked_client():
    import main

    mock_redis = MagicMock()
    mock_redis.client = True
    mock_redis.set = AsyncMock(return_value={"key": "k", "value": "v", "status": "set"})

    with patch.dict(main.clients, {"redis": mock_redis}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/redis", json={"key": "k", "value": "v"})

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_kafka_get_with_mocked_client():
    import main

    mock_kafka = MagicMock()
    mock_kafka.producer = True
    mock_kafka.consume = AsyncMock(return_value=[{"topic": "t", "value": "v"}])

    with patch.dict(main.clients, {"kafka": mock_kafka}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/kafka")

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_kafka_post_with_mocked_client():
    import main

    mock_kafka = MagicMock()
    mock_kafka.producer = True
    mock_kafka.produce = AsyncMock(return_value={"topic": "t", "status": "produced"})

    with patch.dict(main.clients, {"kafka": mock_kafka}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/kafka", json={"message": "m"})

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_mongodb_get_with_mocked_client():
    import main

    mock_mongo = MagicMock()
    mock_mongo.client = True
    mock_mongo.find = AsyncMock(return_value=[{"key": "k", "value": "v"}])

    with patch.dict(main.clients, {"mongo": mock_mongo}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/mongodb")

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_mongodb_post_with_mocked_client():
    import main

    mock_mongo = MagicMock()
    mock_mongo.client = True
    mock_mongo.insert = AsyncMock(return_value={"key": "k", "value": "v", "status": "inserted"})

    with patch.dict(main.clients, {"mongo": mock_mongo}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/mongodb", json={"key": "k", "value": "v"})

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_postgres_health_with_mocked_client():
    import main

    mock_pg = MagicMock()
    mock_pg.health_check = AsyncMock(return_value={"status": "healthy"})

    with patch.dict(main.clients, {"postgres": mock_pg}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/postgres/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_redis_health_with_mocked_client():
    import main

    mock_redis = MagicMock()
    mock_redis.health_check = AsyncMock(return_value={"status": "healthy"})

    with patch.dict(main.clients, {"redis": mock_redis}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/redis/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_kafka_health_with_mocked_client():
    import main

    mock_kafka = MagicMock()
    mock_kafka.health_check = AsyncMock(return_value={"status": "healthy"})

    with patch.dict(main.clients, {"kafka": mock_kafka}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/kafka/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_mongodb_health_with_mocked_client():
    import main

    mock_mongo = MagicMock()
    mock_mongo.health_check = AsyncMock(return_value={"status": "healthy"})

    with patch.dict(main.clients, {"mongo": mock_mongo}):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/mongodb/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
