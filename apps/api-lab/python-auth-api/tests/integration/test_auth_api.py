import uuid
from unittest.mock import AsyncMock

import pytest
from auth.models import AuthenticatedUser
from httpx import ASGITransport, AsyncClient
from keycloak_client import KeycloakClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_keycloak():
    return AsyncMock(spec=KeycloakClient)


@pytest.fixture
def admin_user():
    return AuthenticatedUser(
        sub=uuid.uuid4(),
        username="admin",
        roles=["admin"],
        email="admin@example.com",
    )


@pytest.fixture
def app_with_mock(mock_keycloak, admin_user):
    from auth.dependencies import get_current_user
    from main import app
    from routers import auth as auth_module

    original = auth_module._keycloak_client
    auth_module._keycloak_client = mock_keycloak
    app.dependency_overrides[get_current_user] = lambda: admin_user
    yield app, mock_keycloak
    auth_module._keycloak_client = original
    app.dependency_overrides.clear()


class TestAuthFlow:
    @pytest.mark.asyncio
    async def test_register_then_login(self, app_with_mock):
        app, mock_kc = app_with_mock
        mock_kc.create_user.return_value = "user-abc"
        mock_kc.login.return_value = {
            "access_token": "tok",
            "refresh_token": "ref",
            "expires_in": 300,
            "token_type": "Bearer",
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            reg = await client.post(
                "/api/v1/auth/register",
                json={"username": "newuser", "email": "new@test.com", "password": "password123"},
            )
            assert reg.status_code == 201

            login = await client.post(
                "/api/v1/auth/login",
                json={"username": "newuser", "password": "password123"},
            )
            assert login.status_code == 200
            assert login.json()["access_token"] == "tok"

    @pytest.mark.asyncio
    async def test_refresh_then_logout(self, app_with_mock):
        app, mock_kc = app_with_mock
        mock_kc.refresh.return_value = {
            "access_token": "new-tok",
            "refresh_token": "new-ref",
            "expires_in": 300,
            "token_type": "Bearer",
        }
        mock_kc.logout.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            refresh = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "old-ref"},
            )
            assert refresh.status_code == 200

            logout = await client.post(
                "/api/v1/auth/logout",
                json={"refresh_token": "new-ref"},
            )
            assert logout.status_code == 204


class TestAdminUserManagement:
    @pytest.mark.asyncio
    async def test_create_list_deactivate(self, app_with_mock):
        app, mock_kc = app_with_mock
        mock_kc.create_user.return_value = "managed-user-id"
        mock_kc.list_users.return_value = [
            {
                "id": "managed-user-id",
                "username": "managed",
                "email": "m@test.com",
                "enabled": True,
            },
        ]
        mock_kc.disable_user.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create = await client.post(
                "/api/v1/auth/users",
                json={"username": "managed", "email": "m@test.com", "password": "password123"},
            )
            assert create.status_code == 201

            listing = await client.get("/api/v1/auth/users")
            assert listing.status_code == 200
            assert len(listing.json()) == 1

            deactivate = await client.delete("/api/v1/auth/users/managed-user-id")
            assert deactivate.status_code == 204


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_healthz(self):
        from main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/healthz")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"
