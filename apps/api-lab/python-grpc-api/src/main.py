import asyncio
import logging
import signal

from grpc_server import start_grpc_server
from observability.logging import setup_logging

setup_logging()
logger = logging.getLogger("api-lab.grpc")


async def serve():
    from cache.redis_cache import RedisCache
    from config import app_config, grpc_config
    from database.engine import async_session_factory, engine
    from observability.tracing import setup_tracing, shutdown_tracing
    from services.book_service import BookService

    logger.info("Starting api-lab python-grpc-api...")
    logger.info("Environment: %s", app_config.environment)

    setup_tracing(app=None, service_name="python-grpc-api", enable_grpc_server=True)

    cache = RedisCache()
    await cache.connect()

    book_service = BookService(async_session_factory, cache)

    server = await start_grpc_server(book_service, grpc_config.port)
    logger.info("api-lab python-grpc-api started successfully")

    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)

    await stop_event.wait()

    logger.info("Shutting down api-lab python-grpc-api...")
    await server.stop(grace=5)
    shutdown_tracing()
    await cache.disconnect()
    await engine.dispose()
    logger.info("Shutdown complete")


def main():
    asyncio.run(serve())


if __name__ == "__main__":
    main()
