import os
from unittest import mock

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


@mock.patch.dict(
    os.environ,
    {
        "HOSTNAME": "test-host",
        "APP_VERSION": "v1.2.3",
        "ENVIRONMENT": "test",
        "APP": "my-app",
        "COMPONENT": "my-component",
        "NODE_NAME": "worker-node-1",
        "POD_IP": "10.0.0.1",
        "LOG_LEVEL": "DEBUG",
        "GIT_TAG": "v1.2.3",
        "GIT_COMMIT": "abcdef123",
    },
)
def test_info_endpoint():
    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()

    # Debug print
    print(f"Response Data: {data}")

    assert data["hostname"] == "test-host"
    assert data["app_version"] == "v1.2.3"
    assert data["environment"] == "test"
    assert data["app"] == "my-app"
    assert data["component"] == "my-component"
    assert data["node"] == "worker-node-1"
    assert data["pod_ip"] == "10.0.0.1"
    assert data["log_level"] == "DEBUG"
    assert data["git_tag"] == "v1.2.3"
    assert data["git_commit"] == "abcdef123"
