"""Shared fixtures for api-lab system tests.

These tests run against real running services with real PostgreSQL and Redis.
They skip automatically if services are not reachable.
Database schema is managed by the database migration project.
"""

import json
import os
import uuid

import asyncpg
import grpc
import httpx
import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from migrate import migrate as run_migrations

# Configuration via environment variables
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")
GRAPHQL_BASE_URL = os.environ.get("GRAPHQL_BASE_URL", "http://localhost:8083")
GRPC_HOST = os.environ.get("GRPC_HOST", "localhost:50051")

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_DATABASE = os.environ.get("POSTGRES_DATABASE", "api_lab")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "playground")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "playground")

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "playground")

_services_checked = False
_services_available = False


async def _check_service(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            return resp.status_code == 200
    except Exception:
        return False


async def _check_grpc(host: str) -> bool:
    try:
        channel = grpc.aio.insecure_channel(host)
        await channel.channel_ready()
        await channel.close()
        return True
    except Exception:
        return False


async def _db_connect():
    return await asyncpg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DATABASE,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


@pytest_asyncio.fixture(autouse=True)
async def ensure_and_clean():
    """Check services are reachable (once), then clean DB and Redis."""
    global _services_checked, _services_available  # noqa: PLW0603

    if not _services_checked:
        rest_ok = await _check_service(f"{API_BASE_URL}/healthz")
        graphql_ok = await _check_service(f"{GRAPHQL_BASE_URL}/healthz")
        grpc_ok = await _check_grpc(GRPC_HOST)
        _services_checked = True
        _services_available = rest_ok and graphql_ok and grpc_ok
        if not _services_available:
            missing = []
            if not rest_ok:
                missing.append(f"REST API ({API_BASE_URL})")
            if not graphql_ok:
                missing.append(f"GraphQL ({GRAPHQL_BASE_URL})")
            if not grpc_ok:
                missing.append(f"gRPC ({GRPC_HOST})")
            pytest.skip(f"Services not reachable: {', '.join(missing)}")

        # Apply database migrations (idempotent, only on first run)
        await run_migrations()

    if not _services_available:
        pytest.skip("Services not reachable")

    # Flush Redis cache first so services don't serve stale data
    redis_client = aioredis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True,
    )
    try:
        await redis_client.flushdb()
    finally:
        await redis_client.aclose()

    # Clean data: DELETE in FK order (no TRUNCATE to keep SQLAlchemy sessions valid)
    conn = await _db_connect()
    try:
        await conn.execute("DELETE FROM reservations")
        await conn.execute("DELETE FROM books")
    finally:
        await conn.close()

    yield


@pytest_asyncio.fixture
async def rest_client():
    """HTTP client for the REST API."""
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
        yield client


@pytest_asyncio.fixture
async def graphql_client():
    """HTTP client for the GraphQL gateway."""
    async with httpx.AsyncClient(base_url=GRAPHQL_BASE_URL, timeout=10.0) as client:
        yield client


@pytest_asyncio.fixture
async def grpc_channel():
    """gRPC async channel."""
    channel = grpc.aio.insecure_channel(GRPC_HOST)
    yield channel
    await channel.close()


def _sample_book_data(isbn: str | None = None) -> dict:
    return {
        "isbn": isbn or f"978{uuid.uuid4().hex[:10]}",
        "title": "Test Book",
        "author": "Test Author",
        "genre": "Fiction",
        "published_year": 2024,
        "total_copies": 3,
    }


@pytest_asyncio.fixture
async def create_sample_book(rest_client):
    """Helper fixture that creates a book via REST and returns the response JSON."""

    async def _create(isbn: str | None = None, **overrides) -> dict:
        data = _sample_book_data(isbn)
        data.update(overrides)
        resp = await rest_client.post("/api/v1/books", json=data)
        assert resp.status_code == 201, f"Failed to create book: {resp.status_code} {resp.text}"
        return resp.json()

    return _create


async def grpc_call(channel, method: str, request: dict | None = None):
    """Call a gRPC method with JSON request/response on the LibraryService."""
    return await channel.unary_unary(
        f"/library.v1.LibraryService/{method}",
        request_serializer=lambda x: json.dumps(x, default=str).encode(),
        response_deserializer=lambda x: json.loads(x),
    )(request or {})


async def graphql_query(client, query: str, variables: dict | None = None):
    """Execute a GraphQL query/mutation and return the parsed JSON response."""
    resp = await client.post("/graphql", json={"query": query, "variables": variables})
    return resp.json()
