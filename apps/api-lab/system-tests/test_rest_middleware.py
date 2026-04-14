"""System tests for REST API middleware (request ID, rate limiting, idempotency)."""

import uuid

import pytest


@pytest.mark.asyncio
async def test_request_id_generated(rest_client):
    response = await rest_client.get("/api/v1/books?limit=1")
    assert "X-Request-Id" in response.headers
    uuid.UUID(response.headers["X-Request-Id"])


@pytest.mark.asyncio
async def test_request_id_echoed(rest_client):
    custom_id = str(uuid.uuid4())
    response = await rest_client.get("/api/v1/books?limit=1", headers={"X-Request-Id": custom_id})
    assert response.headers["X-Request-Id"] == custom_id


@pytest.mark.asyncio
async def test_rate_limit_headers_present(rest_client):
    response = await rest_client.get("/api/v1/books?limit=1")
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers


@pytest.mark.asyncio
async def test_idempotency_key_deduplication(rest_client):
    key = str(uuid.uuid4())
    headers = {"Idempotency-Key": key}
    book_data = {
        "isbn": f"978{uuid.uuid4().int % 10**10:010d}",
        "title": "Idempotency Test",
        "author": "Test Author",
        "genre": "Testing",
        "published_year": 2025,
        "total_copies": 1,
    }
    r1 = await rest_client.post("/api/v1/books", json=book_data, headers=headers)
    assert r1.status_code == 201
    r2 = await rest_client.post("/api/v1/books", json=book_data, headers=headers)
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]
