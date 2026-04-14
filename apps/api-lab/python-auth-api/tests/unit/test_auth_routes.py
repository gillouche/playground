from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from keycloak_client import KeycloakClient, KeycloakError


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_keycloak():
    return AsyncMock(spec=KeycloakClient)


@pytest.fixture
def client_with_mock(mock_keycloak):
    from main import app
    from routers import auth as auth_module

    original = auth_module._keycloak_client
    auth_module._keycloak_client = mock_keycloak
    yield app, mock_keycloak
    auth_module._keycloak_client = original


class TestRegister:
    async def test_register_success(self, client_with_mock):
        app, mock_kc = client_with_mock
        mock_kc.create_user.return_value = "user-123"

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "securepass123",
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["user_id"] == "user-123"
            assert data["username"] == "testuser"

    async def test_register_duplicate_username(self, client_with_mock):
        app, mock_kc = client_with_mock
        mock_kc.create_user.side_effect = KeycloakError(409, "User 'testuser' already exists")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "securepass123",
                },
            )
            assert response.status_code == 409

    async def test_register_invalid_username_format(self, client_with_mock):
        app, _ = client_with_mock

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": "test@user!",
                    "email": "test@example.com",
                    "password": "securepass123",
                },
            )
            assert response.status_code == 422

    async def test_register_short_password(self, client_with_mock):
        app, _ = client_with_mock

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={"username": "testuser", "email": "test@example.com", "password": "short"},
            )
            assert response.status_code == 422


class TestLogin:
    async def test_login_success(self, client_with_mock):
        app, mock_kc = client_with_mock
        mock_kc.login.return_value = {
            "access_token": "access-token-123",
            "refresh_token": "refresh-token-123",
            "expires_in": 300,
            "token_type": "Bearer",
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "testuser", "password": "securepass123"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "access-token-123"
            assert data["refresh_token"] == "refresh-token-123"
            assert data["expires_in"] == 300
            assert data["token_type"] == "Bearer"

    async def test_login_wrong_password(self, client_with_mock):
        app, mock_kc = client_with_mock
        mock_kc.login.side_effect = KeycloakError(401, "Invalid username or password")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "testuser", "password": "wrongpass"},
            )
            assert response.status_code == 401


class TestRefresh:
    async def test_refresh_success(self, client_with_mock):
        app, mock_kc = client_with_mock
        mock_kc.refresh.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 300,
            "token_type": "Bearer",
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "old-refresh-token"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "new-access-token"
            assert data["refresh_token"] == "new-refresh-token"

    async def test_refresh_invalid_token(self, client_with_mock):
        app, mock_kc = client_with_mock
        mock_kc.refresh.side_effect = KeycloakError(401, "Invalid or expired refresh token")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "invalid-token"},
            )
            assert response.status_code == 401


class TestLogout:
    async def test_logout_success(self, client_with_mock):
        app, mock_kc = client_with_mock
        mock_kc.logout.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/logout",
                json={"refresh_token": "some-refresh-token"},
            )
            assert response.status_code == 204
