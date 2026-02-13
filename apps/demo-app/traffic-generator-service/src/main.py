import asyncio
import contextlib
import logging
import os
import random
import signal
import string

import httpx
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
)
logger = logging.getLogger("traffic-generator")
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
logger.addHandler(handler)

TARGET_URL = os.environ.get("TARGET_URL", "http://greeting-service:8080")
CONCURRENCY = int(os.environ.get("CONCURRENCY", "10"))
running_state = {"running": True}


def setup_opentelemetry():
    if os.environ.get("ENABLE_TRACING", "true").lower() == "true":
        resource = Resource(
            attributes={
                "service.name": "traffic-generator-service",
                "service.namespace": os.environ.get("NAMESPACE", "default"),
                "deployment.environment": os.environ.get("ENVIRONMENT", "unknown"),
            }
        )

        trace.set_tracer_provider(TracerProvider(resource=resource))
        tracer_provider = trace.get_tracer_provider()

        otlp_endpoint = os.environ.get(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo.monitoring.svc.cluster.local:4317"
        )
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

        # Instrument httpx globally
        HTTPXClientInstrumentor().instrument()
        logger.info(f"OpenTelemetry instrumentation enabled. Exporting to {otlp_endpoint}")


def handle_sigterm(*_args):
    running_state["running"] = False
    logger.info("Received termination signal.")


def generate_random_string(length=8):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


async def worker(client: httpx.AsyncClient):
    """
    Worker task that continuously sends requests while 'running' is True.
    """
    while running_state["running"]:
        try:
            random_name = generate_random_string()
            url = f"{TARGET_URL}?name={random_name}"
            resp = await client.get(url, timeout=5.0)
            logger.debug(f"Request to {url}: {resp.status_code}")
        except httpx.RequestError as exc:
            logger.error(f"Request failed: {exc}")
        except Exception as exc:
            logger.error(f"Unexpected error: {exc}")

        # Small sleep to yield control back to the event loop
        # and prevent 100% CPU usage on the loop itself
        await asyncio.sleep(0.01)


async def wait_for_target(client: httpx.AsyncClient):
    """Wait for the target service to become healthy before sending traffic."""
    interval = 5
    logger.info(f"Waiting for target {TARGET_URL} to become ready...")
    while running_state["running"]:
        try:
            resp = await client.get(TARGET_URL, timeout=5.0)
            if resp.status_code < 500:
                logger.info(f"Target {TARGET_URL} is ready (status {resp.status_code})")
                return True
        except httpx.RequestError:
            pass
        logger.info(f"Target not ready, retrying in {interval}s...")
        await asyncio.sleep(interval)
    return False


async def main():
    setup_opentelemetry()
    logger.info(
        f"Starting Async Traffic Generator. Target: {TARGET_URL}, Concurrency: {CONCURRENCY}"
    )

    # Efficiently reuse connection pool
    limits = httpx.Limits(max_keepalive_connections=CONCURRENCY, max_connections=CONCURRENCY + 5)

    async with httpx.AsyncClient(limits=limits) as client:
        if not await wait_for_target(client):
            logger.info("Shutting down before target became ready.")
            return

        tasks = [asyncio.create_task(worker(client)) for _ in range(CONCURRENCY)]

        # Wait until a signal sets running = False
        while running_state["running"]:
            await asyncio.sleep(1)

        # Wait for workers to finish their current iteration
        await asyncio.gather(*tasks)
        logger.info("Traffic generator stopped successfully.")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_sigterm)
    signal.signal(signal.SIGTERM, handle_sigterm)

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
