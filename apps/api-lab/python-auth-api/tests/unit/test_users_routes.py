import uuid
from unittest.mock import AsyncMock

import pytest
from auth.models import AuthenticatedUser
from httpx import ASGITransport, AsyncClient
from keycloak_client import KeycloakClient, KeycloakError


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
def regular_user():
    return AuthenticatedUser(
        sub=uuid.uuid4(),
        username="regular",
        roles=["user"],
        email="user@example.com",
    )


def _override_auth(app, user: AuthenticatedUser):
    from auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides(app):
    app.dependency_overrides.clear()


@pytest.fixture
def client_admin(mock_keycloak, admin_user):
    from main import app
    from routers import auth as auth_module

    original = auth_module._keycloak_client
    auth_module._keycloak_client = mock_keycloak
    _override_auth(app, admin_user)
    yield app, mock_keycloak
    auth_module._keycloak_client = original
    _clear_overrides(app)


@pytest.fixture
def client_regular(mock_keycloak, regular_user):
    from main import app
    from routers import auth as auth_module

    original = auth_module._keycloak_client
    auth_module._keycloak_client = mock_keycloak
    _override_auth(app, regular_user)
    yield app, mock_keycloak
    auth_module._keycloak_client = original
    _clear_overrides(app)


class TestCreateUser:
    async def test_create_user_as_admin(self, client_admin):
        app, mock_kc = client_admin
        mock_kc.create_user.return_value = "new-user-id"

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/users",
                json={
                    "username": "newuser",
                    "email": "new@example.com",
                    "password": "securepass123",
                },
            )
            assert response.status_code == 201
            assert response.json()["user_id"] == "new-user-id"

    async def test_create_user_as_non_admin(self, client_regular):
        app, _ = client_regular

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/users",
                json={
                    "username": "newuser",
                    "email": "new@example.com",
                    "password": "securepass123",
                },
            )
            assert response.status_code == 403


class TestListUsers:
    async def test_list_users_as_admin(self, client_admin):
        app, mock_kc = client_admin
        mock_kc.list_users.return_value = [
            {
                "id": "user-1",
                "username": "alice",
                "email": "alice@example.com",
                "firstName": "Alice",
                "lastName": "Smith",
                "enabled": True,
            },
        ]

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/auth/users")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["username"] == "alice"


class TestGetUser:
    async def test_get_user_not_found(self, client_admin):
        app, mock_kc = client_admin
        mock_kc.get_user.side_effect = KeycloakError(404, "User not found")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/auth/users/nonexistent-id")
            assert response.status_code == 404


class TestUpdateRoles:
    async def test_update_roles(self, client_admin):
        app, mock_kc = client_admin
        mock_kc.assign_role.return_value = None
        mock_kc.remove_role.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.patch(
                "/api/v1/auth/users/user-123/roles",
                json={"add": ["admin"], "remove": ["user"]},
            )
            assert response.status_code == 200
            mock_kc.assign_role.assert_called_once_with("user-123", "admin")
            mock_kc.remove_role.assert_called_once_with("user-123", "user")


class TestDeactivateUser:
    async def test_deactivate_user(self, client_admin):
        app, mock_kc = client_admin
        mock_kc.disable_user.return_value = None

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete("/api/v1/auth/users/user-123")
            assert response.status_code == 204
            mock_kc.disable_user.assert_called_once_with("user-123")
