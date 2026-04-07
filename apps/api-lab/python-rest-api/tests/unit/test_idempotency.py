import json
from unittest.mock import AsyncMock

from fastapi import FastAPI
from middleware.idempotency import IdempotencyMiddleware
from starlette.testclient import TestClient


def create_app(redis_client, ttl=86400):
    app = FastAPI()
    app.add_middleware(IdempotencyMiddleware, redis_client=redis_client, ttl=ttl)

    @app.post("/test")
    async def post_endpoint():
        return {"status": "created"}

    @app.get("/test")
    async def get_endpoint():
        return {"status": "ok"}

    @app.post("/test-error")
    async def post_error_endpoint():
        from starlette.responses import JSONResponse

        return JSONResponse(status_code=422, content={"detail": "validation error"})

    return app


class TestIdempotencyMiddleware:
    def test_skips_non_post_requests(self):
        redis_client = AsyncMock()
        client = TestClient(create_app(redis_client))

        response = client.get("/test")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        redis_client.get.assert_not_called()

    def test_passes_through_when_no_idempotency_key(self):
        redis_client = AsyncMock()
        client = TestClient(create_app(redis_client))

        response = client.post("/test")

        assert response.status_code == 200
        assert response.json() == {"status": "created"}
        redis_client.get.assert_not_called()

    def test_stores_response_for_new_key(self):
        redis_client = AsyncMock()
        redis_client.get = AsyncMock(return_value=None)
        redis_client.set = AsyncMock()
        client = TestClient(create_app(redis_client))

        response = client.post("/test", headers={"Idempotency-Key": "key-123"})

        assert response.status_code == 200
        redis_client.set.assert_called_once()
        call_args = redis_client.set.call_args
        assert call_args[0][0] == "idempotency:key-123"
        cached_data = json.loads(call_args[0][1])
        assert cached_data["status_code"] == 200
        assert "created" in cached_data["body"]

    def test_returns_cached_response_for_duplicate_key(self):
        redis_client = AsyncMock()
        cached = json.dumps(
            {
                "status_code": 200,
                "body": '{"status":"created"}',
                "headers": {"content-type": "application/json"},
            }
        )
        redis_client.get = AsyncMock(return_value=cached)
        client = TestClient(create_app(redis_client))

        response = client.post("/test", headers={"Idempotency-Key": "key-123"})

        assert response.status_code == 200
        assert response.json() == {"status": "created"}

    def test_preserves_status_code_from_cache(self):
        redis_client = AsyncMock()
        cached = json.dumps(
            {
                "status_code": 422,
                "body": '{"detail":"validation error"}',
                "headers": {"content-type": "application/json"},
            }
        )
        redis_client.get = AsyncMock(return_value=cached)
        client = TestClient(create_app(redis_client))

        response = client.post("/test", headers={"Idempotency-Key": "key-456"})

        assert response.status_code == 422
        assert response.json() == {"detail": "validation error"}

    def test_gracefully_passes_through_on_redis_read_failure(self):
        redis_client = AsyncMock()
        redis_client.get = AsyncMock(side_effect=ConnectionError("Redis down"))
        client = TestClient(create_app(redis_client))

        response = client.post("/test", headers={"Idempotency-Key": "key-789"})

        assert response.status_code == 200
        assert response.json() == {"status": "created"}

    def test_gracefully_passes_through_on_redis_write_failure(self):
        redis_client = AsyncMock()
        redis_client.get = AsyncMock(return_value=None)
        redis_client.set = AsyncMock(side_effect=ConnectionError("Redis down"))
        client = TestClient(create_app(redis_client))

        response = client.post("/test", headers={"Idempotency-Key": "key-abc"})

        assert response.status_code == 200
        assert response.json() == {"status": "created"}

    def test_uses_custom_ttl(self):
        redis_client = AsyncMock()
        redis_client.get = AsyncMock(return_value=None)
        redis_client.set = AsyncMock()
        client = TestClient(create_app(redis_client, ttl=3600))

        client.post("/test", headers={"Idempotency-Key": "key-ttl"})

        call_args = redis_client.set.call_args
        assert call_args.kwargs["ex"] == 3600
