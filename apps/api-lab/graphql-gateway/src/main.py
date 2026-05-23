import logging
import os
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from observability.logging import setup_logging

setup_logging()
logger = logging.getLogger("api-lab.graphql-gateway")

_rest_client_ref: list = [None]
_cache_ref: list = [None]
_redis_client_ref: list = [None]


@asynccontextmanager
async def lifespan(_application: FastAPI):
    from cache.redis_cache import RedisCache
    from client import LibraryClient
    from schema import set_client

    rest_api_url = os.environ.get("REST_API_URL", "http://localhost:8080")

    logger.info("Starting api-lab graphql-gateway...")
    logger.info("REST API URL: %s", rest_api_url)

    cache = RedisCache()
    await cache.connect()
    _cache_ref[0] = cache
    _redis_client_ref[0] = cache.client

    client = LibraryClient(base_url=rest_api_url)
    await client.connect()
    set_client(client)
    _rest_client_ref[0] = client

    logger.info("api-lab graphql-gateway started successfully")

    yield

    logger.info("Shutting down api-lab graphql-gateway...")
    from observability.tracing import shutdown_tracing

    shutdown_tracing()
    await client.disconnect()
    await cache.disconnect()
    logger.info("Shutdown complete")


def _create_app() -> FastAPI:
    from middleware.body_limit import BodyLimitMiddleware
    from middleware.rate_limit import RateLimitMiddleware
    from middleware.request_id import RequestIdMiddleware
    from middleware.security_headers import SecurityHeadersMiddleware
    from observability.metrics import setup_metrics
    from observability.tracing import setup_tracing

    application = FastAPI(
        title="Library GraphQL Gateway",
        version="1.0.0",
        lifespan=lifespan,
    )

    from schema import create_graphql_router

    env = os.environ.get("ENVIRONMENT", "dev")
    graphiql = env != "prod"
    graphql_router = create_graphql_router(graphiql=graphiql)
    application.include_router(graphql_router)

    @application.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @application.get("/ready")
    async def ready():
        errors = []
        rest_client = _rest_client_ref[0]
        cache = _cache_ref[0]
        if rest_client is None:
            errors.append("rest_client: not initialized")
        else:
            healthy = await rest_client.health_check()
            if not healthy:
                errors.append("rest_api: unavailable")
        if cache is not None:
            ok = await cache.health_check()
            if not ok:
                errors.append("redis: ping failed")
        if errors:
            return JSONResponse(status_code=503, content={"status": "not ready", "errors": errors})
        return {"status": "ready"}

    @application.get("/info")
    async def info():
        return {
            "component": "graphql-gateway",
            "environment": env,
        }

    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(BodyLimitMiddleware)
    application.add_middleware(
        RateLimitMiddleware,
        redis_client_ref=_redis_client_ref,
    )
    application.add_middleware(RequestIdMiddleware)

    allow_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
    allow_origins = [o.strip() for o in allow_origins_env.split(",") if o.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
        expose_headers=["X-Request-Id"],
    )

    setup_metrics(application)
    setup_tracing(application, service_name="graphql-gateway", enable_httpx=True)

    return application


app = _create_app()


def handle_signal(sig, _frame):
    logger.info("Received signal %s, shutting down...", sig)
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=8083)


if __name__ == "__main__":
    main()
