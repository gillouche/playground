import os
import uuid

import asyncpg
import grpc
import httpx
import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from library.v1 import library_pb2_grpc
from migrate import migrate as run_migrations

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")
GRAPHQL_BASE_URL = os.environ.get("GRAPHQL_BASE_URL", "http://localhost:8083")
GRPC_HOST = os.environ.get("GRPC_HOST", "localhost:50051")
AUTH_API_URL = os.environ.get("AUTH_API_URL", "http://localhost:8084")

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

        await run_migrations()

    if not _services_available:
        pytest.skip("Services not reachable")

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

    conn = await _db_connect()
    try:
        await conn.execute("DELETE FROM reservations")
        await conn.execute("DELETE FROM books")
    finally:
        await conn.close()

    yield


@pytest_asyncio.fixture
async def rest_client(admin_token):
    async with httpx.AsyncClient(
        base_url=API_BASE_URL,
        timeout=10.0,
        headers={"Authorization": f"Bearer {admin_token}"},
    ) as client:
        yield client


@pytest_asyncio.fixture
async def graphql_client(admin_token):
    async with httpx.AsyncClient(
        base_url=GRAPHQL_BASE_URL,
        timeout=10.0,
        headers={"Authorization": f"Bearer {admin_token}"},
    ) as client:
        yield client


class _AuthInterceptor(grpc.aio.UnaryUnaryClientInterceptor):
    def __init__(self, token: str):
        self._metadata = [("authorization", f"Bearer {token}")]

    async def intercept_unary_unary(self, continuation, client_call_details, request):
        metadata = list(client_call_details.metadata or []) + self._metadata
        new_details = grpc.aio.ClientCallDetails(
            client_call_details.method,
            client_call_details.timeout,
            metadata,
            client_call_details.credentials,
            client_call_details.wait_for_ready,
        )
        return await continuation(new_details, request)


@pytest_asyncio.fixture
async def grpc_channel(admin_token):
    channel = grpc.aio.insecure_channel(
        GRPC_HOST,
        interceptors=[_AuthInterceptor(admin_token)],
    )
    yield channel
    await channel.close()


def _sample_book_data(isbn: str | None = None) -> dict:
    return {
        "isbn": isbn or f"978{uuid.uuid4().int % 10**10:010d}",
        "title": "Test Book",
        "author": "Test Author",
        "genre": "Fiction",
        "published_year": 2024,
        "total_copies": 3,
    }


@pytest_asyncio.fixture
async def create_sample_book(rest_client):
    async def _create(isbn: str | None = None, **overrides) -> dict:
        data = _sample_book_data(isbn)
        data.update(overrides)
        resp = await rest_client.post("/api/v1/books", json=data)
        assert resp.status_code == 201, f"Failed to create book: {resp.status_code} {resp.text}"
        return resp.json()

    return _create


@pytest_asyncio.fixture
async def grpc_stub(grpc_channel):
    return library_pb2_grpc.LibraryServiceStub(grpc_channel)


async def graphql_query(client, query: str, variables: dict | None = None):
    resp = await client.post("/graphql", json={"query": query, "variables": variables})
    return resp.json()


@pytest_asyncio.fixture
async def auth_client():
    async with httpx.AsyncClient(base_url=AUTH_API_URL, timeout=10.0) as client:
        yield client


@pytest_asyncio.fixture
async def registered_user(auth_client):
    username = f"testuser-{uuid.uuid4().hex[:8]}"
    resp = await auth_client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@test.local",
            "password": "testpass123",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    yield {"username": username, "password": "testpass123", "user_id": data["user_id"]}


@pytest_asyncio.fixture
async def user_token(auth_client, registered_user):
    resp = await auth_client.post(
        "/api/v1/auth/login",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    yield data["access_token"]


@pytest_asyncio.fixture
async def admin_token():
    async with httpx.AsyncClient(base_url=AUTH_API_URL, timeout=10.0) as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin-user",
                "password": "admin",
            },
        )
        if resp.status_code == 200:
            return resp.json()["access_token"]
    keycloak_url = os.environ.get("KEYCLOAK_SERVER_URL", "http://localhost:8180")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{keycloak_url}/realms/api-lab/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "api-lab",
                "client_secret": "api-lab-secret",
                "username": "admin-user",
                "password": "admin",
            },
        )
        return resp.json()["access_token"]
