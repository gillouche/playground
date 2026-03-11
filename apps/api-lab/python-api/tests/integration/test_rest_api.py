import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


class TestHealthEndpoints:
    async def test_healthz(self):
        """Test that healthz returns 200 without any infrastructure."""
        from main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/healthz")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    async def test_info(self):
        """Test that info returns basic app information."""
        from main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/info")
            assert response.status_code == 200
            data = response.json()
            assert "hostname" in data
            assert "environment" in data
