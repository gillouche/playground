import os
import platform

from auth.dependencies import is_jwt_validator_initialized, require_roles
from auth.models import AuthenticatedUser
from config import app_config
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from generated.models import HealthResponse, InfoResponse
from keycloak_client import KeycloakClient

router = APIRouter(tags=["health"])

_keycloak_client: KeycloakClient | None = None


def set_keycloak_client(client: KeycloakClient):
    global _keycloak_client  # noqa: PLW0603
    _keycloak_client = client


@router.get("/healthz", response_model=HealthResponse)
async def healthz():
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
async def ready():
    errors = []

    if _keycloak_client:
        healthy = await _keycloak_client.health_check()
        if not healthy:
            errors.append("keycloak: unavailable")
    else:
        errors.append("keycloak: not initialized")

    if not is_jwt_validator_initialized():
        errors.append("jwt_validator: not initialized")

    if errors:
        return JSONResponse(status_code=503, content={"status": "not ready", "errors": errors})

    return HealthResponse(status="ready")


@router.get("/info", response_model=InfoResponse)
async def info(
    _user: AuthenticatedUser = Depends(require_roles("admin")),
):
    return InfoResponse(
        hostname=os.environ.get("HOSTNAME", platform.node()),
        app_version=app_config.app_version,
        environment=app_config.environment,
        app=app_config.app,
        component="python-auth-api",
        node=os.environ.get("NODE_NAME"),
        pod_ip=os.environ.get("POD_IP"),
        log_level=app_config.log_level,
        git_tag=app_config.git_tag,
        git_commit=app_config.git_commit,
    )
