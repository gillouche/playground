import os
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_info_endpoint():
    # Mock environment variables
    os.environ["HOSTNAME"] = "test-host"
    os.environ["APP_VERSION"] = "v1.2.3"
    os.environ["ENVIRONMENT"] = "test"
    os.environ["APP_NAME"] = "my-app"
    os.environ["COMPONENT"] = "my-component"
    os.environ["NODE_NAME"] = "worker-node-1"
    os.environ["POD_IP"] = "10.0.0.1"
    os.environ["LOG_LEVEL"] = "DEBUG"

    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()
    
    assert data["hostname"] == "test-host"
    assert data["version"] == "v1.2.3"
    assert data["environment"] == "test"
    assert data["app"] == "my-app"
    assert data["component"] == "my-component"
    assert data["node"] == "worker-node-1"
    assert data["pod_ip"] == "10.0.0.1"
    assert data["log_level"] == "DEBUG"

    # Cleanup (optional if running in isolated env, but good practice)
    del os.environ["HOSTNAME"]
    del os.environ["APP_VERSION"] 
    del os.environ["ENVIRONMENT"]
    del os.environ["APP_NAME"]
    del os.environ["COMPONENT"]
    del os.environ["NODE_NAME"]
    del os.environ["POD_IP"]
    del os.environ["LOG_LEVEL"]
