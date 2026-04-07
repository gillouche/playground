import uuid

from fastapi import FastAPI, Request
from middleware.request_id import RequestIdMiddleware
from starlette.testclient import TestClient


def create_app():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request):
        return {"request_id": request.state.request_id}

    return app


class TestRequestIdMiddleware:
    def test_generates_uuid_when_no_header(self):
        client = TestClient(create_app())
        response = client.get("/test")
        assert response.status_code == 200
        request_id = response.headers["X-Request-Id"]
        uuid.UUID(request_id)
        assert response.json()["request_id"] == request_id

    def test_echoes_back_client_provided_header(self):
        client = TestClient(create_app())
        custom_id = "my-custom-request-id-123"
        response = client.get("/test", headers={"X-Request-Id": custom_id})
        assert response.status_code == 200
        assert response.headers["X-Request-Id"] == custom_id
        assert response.json()["request_id"] == custom_id

    def test_sets_request_state_request_id(self):
        client = TestClient(create_app())
        response = client.get("/test")
        body = response.json()
        assert "request_id" in body
        assert body["request_id"] == response.headers["X-Request-Id"]

    def test_empty_header_generates_new_uuid(self):
        client = TestClient(create_app())
        response = client.get("/test", headers={"X-Request-Id": ""})
        assert response.status_code == 200
        request_id = response.headers["X-Request-Id"]
        uuid.UUID(request_id)

    def test_each_request_gets_unique_id(self):
        client = TestClient(create_app())
        r1 = client.get("/test")
        r2 = client.get("/test")
        assert r1.headers["X-Request-Id"] != r2.headers["X-Request-Id"]
