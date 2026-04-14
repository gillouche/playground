from unittest.mock import AsyncMock

from fastapi import FastAPI
from middleware.rate_limit import RateLimitMiddleware
from starlette.testclient import TestClient


def create_app(redis_client):
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.post("/test")
    async def test_post_endpoint():
        return {"status": "ok"}

    @app.get("/healthz")
    async def healthz():
        return {"status": "healthy"}

    @app.get("/ready")
    async def ready():
        return {"status": "ready"}

    @app.get("/metrics")
    async def metrics():
        return {"status": "metrics"}

    @app.post("/api/v1/auth/login")
    async def login():
        return {"token": "abc"}

    @app.post("/api/v1/auth/register")
    async def register():
        return {"token": "abc"}

    return app


class TestRateLimitMiddleware:
    def test_allows_requests_under_read_limit(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=1)
        redis_client.expire = AsyncMock()
        client = TestClient(create_app(redis_client))

        response = client.get("/test")

        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "200"
        assert response.headers["X-RateLimit-Remaining"] == "199"
        assert "X-RateLimit-Reset" in response.headers

    def test_blocks_requests_over_read_limit(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=201)
        client = TestClient(create_app(redis_client))

        response = client.get("/test")

        assert response.status_code == 429
        assert response.json() == {"detail": "Rate limit exceeded", "status_code": 429}
        assert response.headers["X-RateLimit-Limit"] == "200"
        assert response.headers["X-RateLimit-Remaining"] == "0"
        assert "Retry-After" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_write_has_lower_limit(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=51)
        client = TestClient(create_app(redis_client))

        response = client.post("/test")

        assert response.status_code == 429
        assert response.headers["X-RateLimit-Limit"] == "50"

    def test_write_allows_under_limit(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=1)
        redis_client.expire = AsyncMock()
        client = TestClient(create_app(redis_client))

        response = client.post("/test")

        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "50"
        assert response.headers["X-RateLimit-Remaining"] == "49"

    def test_auth_has_lowest_limit(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=11)
        client = TestClient(create_app(redis_client))

        response = client.post("/api/v1/auth/login")

        assert response.status_code == 429
        assert response.headers["X-RateLimit-Limit"] == "10"

    def test_auth_allows_under_limit(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=1)
        redis_client.expire = AsyncMock()
        client = TestClient(create_app(redis_client))

        response = client.post("/api/v1/auth/login")

        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "10"

    def test_health_exempt(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=1)
        redis_client.expire = AsyncMock()
        client = TestClient(create_app(redis_client))

        response = client.get("/healthz")

        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers
        redis_client.incr.assert_not_called()

    def test_ready_exempt(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=1)
        redis_client.expire = AsyncMock()
        client = TestClient(create_app(redis_client))

        response = client.get("/ready")

        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers
        redis_client.incr.assert_not_called()

    def test_metrics_exempt(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=1)
        redis_client.expire = AsyncMock()
        client = TestClient(create_app(redis_client))

        response = client.get("/metrics")

        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers
        redis_client.incr.assert_not_called()

    def test_uses_x_forwarded_for(self):
        redis_client = AsyncMock()
        redis_client.expire = AsyncMock()

        captured_keys = []
        original_incr = AsyncMock(return_value=1)

        async def capturing_incr(key):
            captured_keys.append(key)
            return await original_incr(key)

        redis_client.incr = capturing_incr
        client = TestClient(create_app(redis_client))

        client.get("/test", headers={"X-Forwarded-For": "203.0.113.50, 10.0.0.1"})

        assert len(captured_keys) == 1
        assert "203.0.113.50" in captured_keys[0]

    def test_uses_client_host_without_proxy(self):
        redis_client = AsyncMock()
        redis_client.expire = AsyncMock()

        captured_keys = []
        original_incr = AsyncMock(return_value=1)

        async def capturing_incr(key):
            captured_keys.append(key)
            return await original_incr(key)

        redis_client.incr = capturing_incr
        client = TestClient(create_app(redis_client))

        client.get("/test")

        assert len(captured_keys) == 1
        assert "rate_limit:" in captured_keys[0]
        assert "203.0.113.50" not in captured_keys[0]

    def test_gracefully_allows_on_redis_failure(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(side_effect=ConnectionError("Redis down"))
        client = TestClient(create_app(redis_client))

        response = client.get("/test")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_rate_limit_headers_present(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=5)
        redis_client.expire = AsyncMock()
        client = TestClient(create_app(redis_client))

        response = client.get("/test")

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "200"
        assert response.headers["X-RateLimit-Remaining"] == "195"

    def test_sets_expire_on_first_request_in_window(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=1)
        redis_client.expire = AsyncMock()
        client = TestClient(create_app(redis_client))

        client.get("/test")

        redis_client.expire.assert_called_once()

    def test_does_not_set_expire_on_subsequent_requests(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=2)
        redis_client.expire = AsyncMock()
        client = TestClient(create_app(redis_client))

        client.get("/test")

        redis_client.expire.assert_not_called()

    def test_register_auth_path_has_auth_limit(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=11)
        client = TestClient(create_app(redis_client))

        response = client.post("/api/v1/auth/register")

        assert response.status_code == 429
        assert response.headers["X-RateLimit-Limit"] == "10"

    def test_x_forwarded_for_skips_trusted_proxies(self):
        redis_client = AsyncMock()
        redis_client.expire = AsyncMock()

        captured_keys = []
        original_incr = AsyncMock(return_value=1)

        async def capturing_incr(key):
            captured_keys.append(key)
            return await original_incr(key)

        redis_client.incr = capturing_incr
        client = TestClient(create_app(redis_client))

        client.get(
            "/test",
            headers={"X-Forwarded-For": "8.8.8.8, 172.16.0.1, 10.0.0.1"},
        )

        assert len(captured_keys) == 1
        assert "8.8.8.8" in captured_keys[0]
