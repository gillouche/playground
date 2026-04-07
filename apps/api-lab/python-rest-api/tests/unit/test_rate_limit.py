from unittest.mock import AsyncMock

from fastapi import FastAPI
from middleware.rate_limit import RateLimitMiddleware
from starlette.testclient import TestClient


def create_app(redis_client, rate_limit=5, window_seconds=60):
    app = FastAPI()
    app.add_middleware(
        RateLimitMiddleware,
        redis_client=redis_client,
        rate_limit=rate_limit,
        window_seconds=window_seconds,
    )

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    return app


class TestRateLimitMiddleware:
    def test_allows_requests_under_limit(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=1)
        redis_client.expire = AsyncMock()
        client = TestClient(create_app(redis_client, rate_limit=5))

        response = client.get("/test")

        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "5"
        assert response.headers["X-RateLimit-Remaining"] == "4"
        assert "X-RateLimit-Reset" in response.headers

    def test_blocks_requests_over_limit(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=6)
        client = TestClient(create_app(redis_client, rate_limit=5))

        response = client.get("/test")

        assert response.status_code == 429
        assert response.json() == {"detail": "Rate limit exceeded", "status_code": 429}
        assert response.headers["X-RateLimit-Limit"] == "5"
        assert response.headers["X-RateLimit-Remaining"] == "0"
        assert "Retry-After" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_remaining_count_decrements(self):
        redis_client = AsyncMock()
        redis_client.expire = AsyncMock()
        client = TestClient(create_app(redis_client, rate_limit=5))

        for i in range(1, 6):
            redis_client.incr = AsyncMock(return_value=i)
            response = client.get("/test")
            expected_remaining = max(0, 5 - i)
            assert response.headers["X-RateLimit-Remaining"] == str(expected_remaining)

    def test_gracefully_allows_on_redis_failure(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(side_effect=ConnectionError("Redis down"))
        client = TestClient(create_app(redis_client, rate_limit=5))

        response = client.get("/test")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_different_ips_tracked_separately(self):
        redis_client = AsyncMock()
        redis_client.expire = AsyncMock()

        incr_values = {}

        async def mock_incr(key):
            incr_values[key] = incr_values.get(key, 0) + 1
            return incr_values[key]

        redis_client.incr = mock_incr
        client = TestClient(create_app(redis_client, rate_limit=5))

        client.get("/test")

        called_keys = list(incr_values.keys())
        assert len(called_keys) == 1
        assert "rate_limit:" in called_keys[0]

    def test_sets_expire_on_first_request_in_window(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=1)
        redis_client.expire = AsyncMock()
        client = TestClient(create_app(redis_client, rate_limit=5, window_seconds=60))

        client.get("/test")

        redis_client.expire.assert_called_once()

    def test_does_not_set_expire_on_subsequent_requests(self):
        redis_client = AsyncMock()
        redis_client.incr = AsyncMock(return_value=2)
        redis_client.expire = AsyncMock()
        client = TestClient(create_app(redis_client, rate_limit=5))

        client.get("/test")

        redis_client.expire.assert_not_called()
