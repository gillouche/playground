import logging
import time

import httpx
from config import keycloak_config

logger = logging.getLogger("api-lab.auth.keycloak")


class KeycloakError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Keycloak error {status_code}: {detail}")


class KeycloakClient:
    def __init__(self):
        self._http = httpx.AsyncClient(timeout=float(keycloak_config.timeout))
        self._admin_token: str | None = None
        self._admin_token_expires_at: float = 0
        self._server_url = keycloak_config.server_url
        self._realm = keycloak_config.realm
        self._admin_url = keycloak_config.admin_url
        self._token_url = keycloak_config.token_url
        self._auth_service_client_id = keycloak_config.auth_service_client_id
        self._auth_service_client_secret = keycloak_config.auth_service_client_secret
        self._user_client_id = keycloak_config.client_id
        self._user_client_secret = keycloak_config.client_secret

    async def close(self):
        await self._http.aclose()

    async def _get_admin_token(self) -> str:
        if self._admin_token and time.time() < self._admin_token_expires_at - 30:
            return self._admin_token

        response = await self._http.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._auth_service_client_id,
                "client_secret": self._auth_service_client_secret,
            },
        )
        if response.status_code != 200:
            raise KeycloakError(response.status_code, "Failed to obtain admin token")

        data = response.json()
        self._admin_token = data["access_token"]
        self._admin_token_expires_at = time.time() + data.get("expires_in", 300)
        return self._admin_token

    async def _admin_headers(self) -> dict[str, str]:
        token = await self._get_admin_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def create_user(self, username: str, email: str, password: str) -> str:
        headers = await self._admin_headers()

        user_payload = {
            "username": username,
            "email": email,
            "firstName": username,
            "lastName": "User",
            "enabled": True,
            "emailVerified": True,
            "credentials": [{"type": "password", "value": password, "temporary": False}],
        }

        response = await self._http.post(
            f"{self._admin_url}/users",
            json=user_payload,
            headers=headers,
        )

        if response.status_code == 409:
            raise KeycloakError(409, f"User '{username}' already exists")
        if response.status_code != 201:
            raise KeycloakError(response.status_code, f"Failed to create user: {response.text}")

        location = response.headers.get("Location", "")
        user_id = location.rsplit("/", 1)[-1]

        await self.assign_role(user_id, "user")

        return user_id

    async def login(self, username: str, password: str) -> dict:
        response = await self._http.post(
            self._token_url,
            data={
                "grant_type": "password",
                "client_id": self._user_client_id,
                "client_secret": self._user_client_secret,
                "username": username,
                "password": password,
            },
        )

        if response.status_code != 200:
            raise KeycloakError(401, "Invalid username or password")

        data = response.json()
        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_in": data["expires_in"],
            "token_type": data["token_type"],
        }

    async def refresh(self, refresh_token: str) -> dict:
        response = await self._http.post(
            self._token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": self._user_client_id,
                "client_secret": self._user_client_secret,
                "refresh_token": refresh_token,
            },
        )

        if response.status_code != 200:
            raise KeycloakError(401, "Invalid or expired refresh token")

        data = response.json()
        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_in": data["expires_in"],
            "token_type": data["token_type"],
        }

    async def logout(self, refresh_token: str) -> None:
        response = await self._http.post(
            f"{self._server_url}/realms/{self._realm}/protocol/openid-connect/logout",
            data={
                "client_id": self._user_client_id,
                "client_secret": self._user_client_secret,
                "refresh_token": refresh_token,
            },
        )

        if response.status_code not in (200, 204):
            raise KeycloakError(response.status_code, "Failed to logout")

    async def get_user(self, user_id: str) -> dict:
        headers = await self._admin_headers()
        response = await self._http.get(
            f"{self._admin_url}/users/{user_id}",
            headers=headers,
        )

        if response.status_code == 404:
            raise KeycloakError(404, f"User '{user_id}' not found")
        if response.status_code != 200:
            raise KeycloakError(response.status_code, f"Failed to get user: {response.text}")

        return response.json()

    async def list_users(self, first: int = 0, max_results: int = 20) -> list[dict]:
        headers = await self._admin_headers()
        response = await self._http.get(
            f"{self._admin_url}/users",
            params={"first": first, "max": max_results},
            headers=headers,
        )

        if response.status_code != 200:
            raise KeycloakError(response.status_code, f"Failed to list users: {response.text}")

        return response.json()

    async def update_user(self, user_id: str, data: dict) -> None:
        headers = await self._admin_headers()
        response = await self._http.put(
            f"{self._admin_url}/users/{user_id}",
            json=data,
            headers=headers,
        )

        if response.status_code == 404:
            raise KeycloakError(404, f"User '{user_id}' not found")
        if response.status_code not in (200, 204):
            raise KeycloakError(response.status_code, f"Failed to update user: {response.text}")

    async def disable_user(self, user_id: str) -> None:
        await self.update_user(user_id, {"enabled": False})

    async def assign_role(self, user_id: str, role_name: str) -> None:
        headers = await self._admin_headers()

        role_response = await self._http.get(
            f"{self._admin_url}/roles/{role_name}",
            headers=headers,
        )
        if role_response.status_code != 200:
            raise KeycloakError(role_response.status_code, f"Role '{role_name}' not found")
        role = role_response.json()

        response = await self._http.post(
            f"{self._admin_url}/users/{user_id}/role-mappings/realm",
            json=[role],
            headers=headers,
        )
        if response.status_code not in (200, 204):
            raise KeycloakError(
                response.status_code,
                f"Failed to assign role '{role_name}': {response.text}",
            )

    async def remove_role(self, user_id: str, role_name: str) -> None:
        headers = await self._admin_headers()

        role_response = await self._http.get(
            f"{self._admin_url}/roles/{role_name}",
            headers=headers,
        )
        if role_response.status_code != 200:
            raise KeycloakError(role_response.status_code, f"Role '{role_name}' not found")
        role = role_response.json()

        response = await self._http.request(
            "DELETE",
            f"{self._admin_url}/users/{user_id}/role-mappings/realm",
            headers=headers,
            json=[role],
        )
        if response.status_code not in (200, 204):
            raise KeycloakError(
                response.status_code,
                f"Failed to remove role '{role_name}': {response.text}",
            )

    async def health_check(self) -> bool:
        try:
            response = await self._http.get(
                f"{self._server_url}/realms/{self._realm}",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception:
            return False
