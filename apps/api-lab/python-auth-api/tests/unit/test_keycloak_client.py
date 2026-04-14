from unittest.mock import AsyncMock

import httpx
import pytest
from keycloak_client import KeycloakClient, KeycloakError


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _make_response(
    status_code: int, json_data: dict | list | None = None, headers: dict | None = None
):
    response = httpx.Response(
        status_code=status_code,
        json=json_data,
        headers=headers or {},
        request=httpx.Request("POST", "http://test"),
    )
    return response


def _make_admin_token_response():
    return _make_response(200, {"access_token": "admin-token", "expires_in": 300})


class TestCreateUser:
    async def test_create_user_success(self):
        client = KeycloakClient()
        mock_http = AsyncMock()

        admin_token_resp = _make_admin_token_response()
        create_user_resp = _make_response(
            201, None, {"Location": "http://keycloak/users/new-user-id"}
        )
        role_resp = _make_response(200, {"id": "role-id", "name": "user"})
        assign_role_resp = _make_response(204)

        mock_http.post.side_effect = [admin_token_resp, create_user_resp, assign_role_resp]
        mock_http.get.return_value = role_resp
        client._http = mock_http

        user_id = await client.create_user("testuser", "test@example.com", "password123")

        assert user_id == "new-user-id"
        assert mock_http.post.call_count == 3

    async def test_create_user_duplicate(self):
        client = KeycloakClient()
        mock_http = AsyncMock()

        admin_token_resp = _make_admin_token_response()
        duplicate_resp = _make_response(409, {"error": "User exists"})

        mock_http.post.side_effect = [admin_token_resp, duplicate_resp]
        client._http = mock_http

        with pytest.raises(KeycloakError) as exc_info:
            await client.create_user("existing", "test@example.com", "password123")
        assert exc_info.value.status_code == 409


class TestLogin:
    async def test_login_success(self):
        client = KeycloakClient()
        mock_http = AsyncMock()

        token_resp = _make_response(
            200,
            {
                "access_token": "access-123",
                "refresh_token": "refresh-123",
                "expires_in": 300,
                "token_type": "Bearer",
            },
        )
        mock_http.post.return_value = token_resp
        client._http = mock_http

        result = await client.login("testuser", "password123")

        assert result["access_token"] == "access-123"
        assert result["refresh_token"] == "refresh-123"
        assert result["expires_in"] == 300
        assert result["token_type"] == "Bearer"

    async def test_login_invalid_credentials(self):
        client = KeycloakClient()
        mock_http = AsyncMock()

        error_resp = _make_response(401, {"error": "invalid_grant"})
        mock_http.post.return_value = error_resp
        client._http = mock_http

        with pytest.raises(KeycloakError) as exc_info:
            await client.login("testuser", "wrongpass")
        assert exc_info.value.status_code == 401
