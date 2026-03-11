import logging
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from observability.logging import setup_logging

setup_logging()
logger = logging.getLogger("api-lab")


@asynccontextmanager
async def lifespan(application: FastAPI):
    from cache.redis_cache import RedisCache
    from config import app_config, grpc_config
    from database.engine import async_session_factory, engine
    from grpc_server import start_grpc_server
    from observability.metrics import setup_metrics
    from observability.tracing import setup_tracing
    from routers import graphql as graphql_module
    from routers import health as health_module
    from routers import rest as rest_module
    from services.book_service import BookService

    logger.info("Starting api-lab python-api...")
    logger.info("Environment: %s", app_config.environment)

    cache = RedisCache()
    await cache.connect()

    book_service = BookService(async_session_factory, cache)

    rest_module.set_book_service(book_service)
    graphql_module.set_book_service(book_service)
    health_module.set_cache(cache)

    setup_metrics(application)
    setup_tracing(application)

    grpc_server = await start_grpc_server(book_service, grpc_config.port)

    logger.info("api-lab python-api started successfully")

    yield

    logger.info("Shutting down api-lab python-api...")
    if grpc_server:
        await grpc_server.stop(grace=5)
    await cache.disconnect()
    await engine.dispose()
    logger.info("Shutdown complete")


def _create_app() -> FastAPI:
    application = FastAPI(
        title="Library Book Management API",
        version="1.0.0",
        lifespan=lifespan,
    )

    from routers.graphql import create_graphql_router
    from routers.health import router as health_router
    from routers.rest import router as rest_router

    application.include_router(rest_router)
    application.include_router(health_router)

    from config import app_config

    graphiql = app_config.environment != "prod"
    graphql_router = create_graphql_router(graphiql=graphiql)
    application.include_router(graphql_router)

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
