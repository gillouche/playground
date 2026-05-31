import logging
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from observability.logging import setup_logging

setup_logging()
logger = logging.getLogger("api-lab.rest")

_redis_client_ref: list = []


@asynccontextmanager
async def lifespan(_application: FastAPI):
    from cache.redis_cache import RedisCache
    from config import app_config
    from observability.tracing import shutdown_tracing
    from routers import health as health_module
    from routers import rest as rest_module
    from services.book_service import BookService

    from database.engine import async_session_factory, engine

    logger.info("Starting api-lab python-rest-api...")
    logger.info("Environment: %s", app_config.environment)

    cache = RedisCache()
    await cache.connect()

    _redis_client_ref.append(cache.client)

    from auth.dependencies import set_jwt_validator
    from auth.jwt import JWTValidator

    jwt_validator = JWTValidator()
    set_jwt_validator(jwt_validator)

    book_service = BookService(async_session_factory, cache)

    rest_module.set_book_service(book_service)
    health_module.set_cache(cache)

    logger.info("api-lab python-rest-api started successfully")

    yield

    logger.info("Shutting down api-lab python-rest-api...")
    shutdown_tracing()
    await cache.disconnect()
    await engine.dispose()
    _redis_client_ref.clear()
    logger.info("Shutdown complete")


def _create_app() -> FastAPI:
    application = FastAPI(
        title="Library Book Management REST API",
        version="1.0.0",
        lifespan=lifespan,
    )

    from auth.permissions import PermissionDeniedError
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse as FastAPIJSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    _STATUS_ERROR_CODES = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        412: "precondition_failed",
        413: "payload_too_large",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_server_error",
        503: "service_unavailable",
    }

    def _status_to_error_code(status_code: int) -> str:
        return _STATUS_ERROR_CODES.get(status_code, f"error_{status_code}")

    @application.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(request, exc):
        request_id = getattr(getattr(request, "state", None), "request_id", None)
        return FastAPIJSONResponse(
            status_code=403,
            content={"error": "forbidden", "detail": str(exc), "request_id": request_id},
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request, exc):
        request_id = getattr(getattr(request, "state", None), "request_id", None)
        return FastAPIJSONResponse(
            status_code=exc.status_code,
            content={
                "error": _status_to_error_code(exc.status_code),
                "detail": exc.detail,
                "request_id": request_id,
            },
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        request_id = getattr(getattr(request, "state", None), "request_id", None)
        return FastAPIJSONResponse(
            status_code=422,
            content={"error": "validation_error", "detail": str(exc), "request_id": request_id},
        )

    @application.exception_handler(Exception)
    async def global_exception_handler(request, _exc):
        request_id = getattr(getattr(request, "state", None), "request_id", None)
        logger.exception("Unhandled exception", extra={"request_id": request_id})
        return FastAPIJSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "detail": "An unexpected error occurred",
                "request_id": request_id,
            },
        )

    from fastapi.middleware.cors import CORSMiddleware
    from middleware.body_limit import BodyLimitMiddleware
    from middleware.idempotency import IdempotencyMiddleware
    from middleware.rate_limit import RateLimitMiddleware
    from middleware.request_id import RequestIdMiddleware
    from middleware.security_headers import SecurityHeadersMiddleware
    from observability.metrics import setup_metrics
    from observability.tracing import setup_tracing
    from routers.health import router as health_router
    from routers.rest import router as rest_router

    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(BodyLimitMiddleware)
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(RateLimitMiddleware, redis_client_ref=_redis_client_ref)
    application.add_middleware(IdempotencyMiddleware, redis_client_ref=_redis_client_ref)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "If-Match",
            "X-Request-Id",
        ],
        expose_headers=[
            "ETag",
            "Location",
            "X-Request-Id",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
    )

    application.include_router(rest_router)
    application.include_router(health_router)

    setup_metrics(application)
    setup_tracing(application, service_name="python-rest-api")

    return application


app = _create_app()


def handle_signal(sig, _frame):
    logger.info("Received signal %s, shutting down...", sig)
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    uvicorn.run(app, host="0.0.0.0", port=8080)  # nosec B104


if __name__ == "__main__":
    main()
