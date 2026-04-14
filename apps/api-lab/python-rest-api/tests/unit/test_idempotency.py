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

    def test_rejects_non_uuid_idempotency_key(self):
        redis_client = AsyncMock()
        client = TestClient(create_app(redis_client))

        response = client.post("/test", headers={"Idempotency-Key": "not-a-uuid"})

        assert response.status_code == 400
        assert response.json() == {"detail": "Idempotency-Key must be a valid UUID"}
        redis_client.get.assert_not_called()

    def test_stores_response_for_new_key(self):
        redis_client = AsyncMock()
        redis_client.get = AsyncMock(return_value=None)
        redis_client.set = AsyncMock()
        client = TestClient(create_app(redis_client))
        key = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

        response = client.post("/test", headers={"Idempotency-Key": key})

        assert response.status_code == 200
        redis_client.set.assert_called_once()
        call_args = redis_client.set.call_args
        assert call_args[0][0] == f"idempotency:POST:/test:{key}"
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

        response = client.post(
            "/test",
            headers={"Idempotency-Key": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"},
        )

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

        response = client.post(
            "/test",
            headers={"Idempotency-Key": "b2c3d4e5-f6a7-8901-bcde-f12345678901"},
        )

        assert response.status_code == 422
        assert response.json() == {"detail": "validation error"}

    def test_gracefully_passes_through_on_redis_read_failure(self):
        redis_client = AsyncMock()
        redis_client.get = AsyncMock(side_effect=ConnectionError("Redis down"))
        client = TestClient(create_app(redis_client))

        response = client.post(
            "/test",
            headers={"Idempotency-Key": "c3d4e5f6-a7b8-9012-cdef-123456789012"},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "created"}

    def test_gracefully_passes_through_on_redis_write_failure(self):
        redis_client = AsyncMock()
        redis_client.get = AsyncMock(return_value=None)
        redis_client.set = AsyncMock(side_effect=ConnectionError("Redis down"))
        client = TestClient(create_app(redis_client))

        response = client.post(
            "/test",
            headers={"Idempotency-Key": "d4e5f6a7-b8c9-0123-defa-234567890123"},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "created"}

    def test_uses_custom_ttl(self):
        redis_client = AsyncMock()
        redis_client.get = AsyncMock(return_value=None)
        redis_client.set = AsyncMock()
        client = TestClient(create_app(redis_client, ttl=3600))

        client.post(
            "/test",
            headers={"Idempotency-Key": "e5f6a7b8-c9d0-1234-efab-345678901234"},
        )

        call_args = redis_client.set.call_args
        assert call_args.kwargs["ex"] == 3600
