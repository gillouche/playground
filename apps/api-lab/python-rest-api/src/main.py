import logging
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from observability.logging import setup_logging

setup_logging()
logger = logging.getLogger("api-lab.rest")


@asynccontextmanager
async def lifespan(_application: FastAPI):
    from cache.redis_cache import RedisCache
    from config import app_config
    from database.engine import async_session_factory, engine
    from observability.tracing import shutdown_tracing
    from routers import health as health_module
    from routers import rest as rest_module
    from services.book_service import BookService

    logger.info("Starting api-lab python-rest-api...")
    logger.info("Environment: %s", app_config.environment)

    cache = RedisCache()
    await cache.connect()

    book_service = BookService(async_session_factory, cache)

    rest_module.set_book_service(book_service)
    health_module.set_cache(cache)

    logger.info("api-lab python-rest-api started successfully")

    yield

    logger.info("Shutting down api-lab python-rest-api...")
    shutdown_tracing()
    await cache.disconnect()
    await engine.dispose()
    logger.info("Shutdown complete")


def _create_app() -> FastAPI:
    application = FastAPI(
        title="Library Book Management REST API",
        version="1.0.0",
        lifespan=lifespan,
    )

    from observability.metrics import setup_metrics
    from observability.tracing import setup_tracing
    from routers.health import router as health_router
    from routers.rest import router as rest_router

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
    uvicorn.run(app, host="0.0.0.0", port=8080)  # nosec B104 - bind all interfaces in container


if __name__ == "__main__":
    main()
