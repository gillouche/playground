from auth.dependencies import get_current_user
from auth.models import AuthenticatedUser
from fastapi import APIRouter, Depends, HTTPException
from keycloak_client import KeycloakError
from pydantic import BaseModel, Field
from routers.auth import get_keycloak_client

router = APIRouter(prefix="/api/v1/auth/me", tags=["profile"])


class ProfileResponse(BaseModel):
    id: str
    username: str
    email: str | None = None
    roles: list[str] = Field(default_factory=list)
    first_name: str | None = None
    last_name: str | None = None


class ProfileUpdate(BaseModel):
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
):
    client = get_keycloak_client()
    try:
        kc_user = await client.get_user(str(user.sub))
    except KeycloakError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

    return ProfileResponse(
        id=str(user.sub),
        username=user.username,
        email=kc_user.get("email"),
        roles=user.roles,
        first_name=kc_user.get("firstName"),
        last_name=kc_user.get("lastName"),
    )


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    update: ProfileUpdate,
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
):
    client = get_keycloak_client()

    update_data: dict = {}
    if update.email is not None:
        update_data["email"] = update.email
    if update.first_name is not None:
        update_data["firstName"] = update.first_name
    if update.last_name is not None:
        update_data["lastName"] = update.last_name

    if update_data:
        try:
            await client.update_user(str(user.sub), update_data)
        except KeycloakError as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail) from e

    try:
        kc_user = await client.get_user(str(user.sub))
    except KeycloakError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

    return ProfileResponse(
        id=str(user.sub),
        username=user.username,
        email=kc_user.get("email"),
        roles=user.roles,
        first_name=kc_user.get("firstName"),
        last_name=kc_user.get("lastName"),
    )


@router.post("/change-password", status_code=204)
async def change_password(
    request: ChangePasswordRequest,
    user: AuthenticatedUser = Depends(get_current_user),  # noqa: B008
):
    client = get_keycloak_client()

    try:
        await client.login(user.username, request.current_password)
    except KeycloakError as e:
        raise HTTPException(status_code=400, detail="Current password is incorrect") from e

    try:
        await client.update_user(
            str(user.sub),
            {
                "credentials": [
                    {"type": "password", "value": request.new_password, "temporary": False}
                ]
            },
        )
    except KeycloakError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
