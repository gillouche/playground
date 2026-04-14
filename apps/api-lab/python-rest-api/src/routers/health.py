import os
import platform

from auth.dependencies import require_roles
from auth.models import AuthenticatedUser
from cache.redis_cache import RedisCache
from config import app_config
from database.engine import async_session_factory
from fastapi import APIRouter, Depends
from generated.models import HealthResponse, InfoResponse
from sqlalchemy import text

router = APIRouter(tags=["health"])

_cache: RedisCache | None = None


def set_cache(cache: RedisCache):
    global _cache  # noqa: PLW0603
    _cache = cache


@router.get("/healthz", response_model=HealthResponse)
async def healthz():
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
async def ready():
    errors = []
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        errors.append("postgres: unavailable")

    if _cache:
        healthy = await _cache.health_check()
        if not healthy:
            errors.append("redis: ping failed")

    if errors:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=503, content={"status": "not ready", "errors": errors})

    return HealthResponse(status="ready")


@router.get("/info", response_model=InfoResponse)
async def info(
    _admin: AuthenticatedUser = Depends(require_roles("admin")),  # noqa: B008
):
    return InfoResponse(
        hostname=os.environ.get("HOSTNAME", platform.node()),
        app_version=app_config.app_version,
        environment=app_config.environment,
        app=app_config.app,
        component="python-rest-api",
        node=os.environ.get("NODE_NAME"),
        pod_ip=os.environ.get("POD_IP"),
        log_level=app_config.log_level,
        git_tag=app_config.git_tag,
        git_commit=app_config.git_commit,
    )
