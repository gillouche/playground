import logging
import os
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from observability.logging import setup_logging

setup_logging()
logger = logging.getLogger("api-lab.graphql-gateway")


@asynccontextmanager
async def lifespan(_application: FastAPI):
    from client import LibraryClient
    from schema import set_client

    rest_api_url = os.environ.get("REST_API_URL", "http://localhost:8080")

    logger.info("Starting api-lab graphql-gateway...")
    logger.info("REST API URL: %s", rest_api_url)

    client = LibraryClient(base_url=rest_api_url)
    await client.connect()
    set_client(client)

    logger.info("api-lab graphql-gateway started successfully")

    yield

    logger.info("Shutting down api-lab graphql-gateway...")
    from observability.tracing import shutdown_tracing

    shutdown_tracing()
    await client.disconnect()
    logger.info("Shutdown complete")


def _create_app() -> FastAPI:
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

    @application.get("/info")
    async def info():
        return {
            "component": "graphql-gateway",
            "environment": env,
        }

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
    uvicorn.run(app, host="0.0.0.0", port=8083)


if __name__ == "__main__":
    main()
