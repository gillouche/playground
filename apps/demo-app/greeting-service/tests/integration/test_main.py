from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_read_root_default():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World! Welcome to the Playground (unknown)."}


def test_read_root_with_name():
    response = client.get("/?name=Alice")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, Alice! Welcome to the Playground (unknown)."}


def test_read_root_with_sanitization():
    # Test HTML escaping
    response = client.get("/?name=<script>alert(1)</script>")
    assert response.status_code == 200
    expected_safe = "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert response.json() == {
        "message": f"Hello, {expected_safe}! Welcome to the Playground (unknown)."
    }


def test_read_root_whitespace():
    # Test whitespace stripping
    response = client.get("/?name=  Bob  ")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, Bob! Welcome to the Playground (unknown)."}


def test_read_root_empty():
    # Test empty string falls back to World
    response = client.get("/?name=")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World! Welcome to the Playground (unknown)."}

    response = client.get("/?name=")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, World! Welcome to the Playground (unknown)."}
