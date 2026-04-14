import logging
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from observability.logging import setup_logging

setup_logging()
logger = logging.getLogger("api-lab.auth")

_redis_client_ref: list = []


@asynccontextmanager
async def lifespan(_application: FastAPI):
    from auth.dependencies import set_jwt_validator
    from auth.jwt import JWTValidator
    from cache.redis_cache import RedisCache
    from config import app_config
    from keycloak_client import KeycloakClient
    from observability.tracing import shutdown_tracing
    from routers import auth as auth_module
    from routers import health as health_module

    logger.info("Starting api-lab python-auth-api...")
    logger.info("Environment: %s", app_config.environment)

    cache = RedisCache()
    await cache.connect()

    _redis_client_ref.append(cache.client)

    keycloak_client = KeycloakClient()
    jwt_validator = JWTValidator()

    set_jwt_validator(jwt_validator)
    auth_module.set_keycloak_client(keycloak_client)
    health_module.set_keycloak_client(keycloak_client)

    logger.info("api-lab python-auth-api started successfully")

    yield

    logger.info("Shutting down api-lab python-auth-api...")
    shutdown_tracing()
    await keycloak_client.close()
    await cache.disconnect()
    _redis_client_ref.clear()
    logger.info("Shutdown complete")


def _create_app() -> FastAPI:
    application = FastAPI(
        title="Auth API",
        version="1.0.0",
        lifespan=lifespan,
    )

    @application.exception_handler(Exception)
    async def global_exception_handler(request, _exc):
        request_id = getattr(getattr(request, "state", None), "request_id", None)
        logger.exception("Unhandled exception", extra={"request_id": request_id})
        from fastapi.responses import JSONResponse as FastAPIJSONResponse

        return FastAPIJSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "request_id": request_id},
        )

    from fastapi.middleware.cors import CORSMiddleware
    from middleware.body_limit import BodyLimitMiddleware
    from middleware.rate_limit import RateLimitMiddleware
    from middleware.request_id import RequestIdMiddleware
    from middleware.security_headers import SecurityHeadersMiddleware
    from observability.metrics import setup_metrics
    from observability.tracing import setup_tracing
    from routers.auth import router as auth_router
    from routers.health import router as health_router
    from routers.profile import router as profile_router
    from routers.users import router as users_router

    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(BodyLimitMiddleware)
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(RateLimitMiddleware, redis_client_ref=_redis_client_ref)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
        expose_headers=[
            "X-Request-Id",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
    )

    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(profile_router)
    application.include_router(health_router)

    setup_metrics(application)
    setup_tracing(application, service_name="python-auth-api")

    return application


app = _create_app()


def handle_signal(sig, _frame):
    logger.info("Received signal %s, shutting down...", sig)
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    uvicorn.run(app, host="0.0.0.0", port=8084)  # nosec B104


if __name__ == "__main__":
    main()
