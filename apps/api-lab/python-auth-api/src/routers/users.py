from auth.dependencies import require_roles
from auth.models import AuthenticatedUser
from fastapi import APIRouter, Depends, HTTPException
from keycloak_client import KeycloakError
from pydantic import BaseModel, Field
from routers.auth import RegisterRequest, get_keycloak_client

router = APIRouter(prefix="/api/v1/auth/users", tags=["users"])


class CreateUserResponse(BaseModel):
    user_id: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    enabled: bool = True


class RoleUpdate(BaseModel):
    add: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)


def _format_user(user: dict) -> UserResponse:
    return UserResponse(
        id=user.get("id", ""),
        username=user.get("username", ""),
        email=user.get("email"),
        first_name=user.get("firstName"),
        last_name=user.get("lastName"),
        enabled=user.get("enabled", True),
    )


@router.post("", status_code=201, response_model=CreateUserResponse)
async def create_user(
    request: RegisterRequest,
    _user: AuthenticatedUser = Depends(require_roles("admin")),
):
    client = get_keycloak_client()
    try:
        user_id = await client.create_user(request.username, request.email, request.password)
    except KeycloakError as e:
        if e.status_code == 409:
            raise HTTPException(status_code=409, detail=e.detail) from e
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

    return CreateUserResponse(user_id=user_id)


@router.get("", response_model=list[UserResponse])
async def list_users(
    first: int = 0,
    max_results: int = 20,
    _user: AuthenticatedUser = Depends(require_roles("admin")),
):
    client = get_keycloak_client()
    try:
        users = await client.list_users(first=first, max_results=max_results)
    except KeycloakError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

    return [_format_user(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    _user: AuthenticatedUser = Depends(require_roles("admin")),
):
    client = get_keycloak_client()
    try:
        user = await client.get_user(user_id)
    except KeycloakError as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=e.detail) from e
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

    return _format_user(user)


@router.patch("/{user_id}/roles")
async def update_roles(
    user_id: str,
    role_update: RoleUpdate,
    _user: AuthenticatedUser = Depends(require_roles("admin")),
):
    client = get_keycloak_client()
    try:
        for role_name in role_update.add:
            await client.assign_role(user_id, role_name)
        for role_name in role_update.remove:
            await client.remove_role(user_id, role_name)
    except KeycloakError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

    return {"status": "ok"}


@router.delete("/{user_id}", status_code=204)
async def deactivate_user(
    user_id: str,
    _user: AuthenticatedUser = Depends(require_roles("admin")),
):
    client = get_keycloak_client()
    try:
        await client.disable_user(user_id)
    except KeycloakError as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=e.detail) from e
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
