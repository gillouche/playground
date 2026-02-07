from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_info_endpoint_defaults():
    # Calling without specific env vars set should return 200 and default/unknown values
    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()

    # Keys should exist
    assert "hostname" in data
    assert "app_version" in data
    assert "environment" in data
    assert "node" in data
    assert "log_level" in data
