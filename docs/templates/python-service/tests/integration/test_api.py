"""Integration tests for {{SERVICE_NAME}} API."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_full_api_flow(client):
    """Test a complete API flow."""
    # Check service is healthy
    health = client.get("/healthz")
    assert health.status_code == 200

    # Check service is ready
    ready = client.get("/ready")
    assert ready.status_code == 200

    # Test main endpoint
    root = client.get("/")
    assert root.status_code == 200
