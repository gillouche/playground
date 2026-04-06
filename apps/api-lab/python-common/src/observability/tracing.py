import logging

from config import app_config
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger("api-lab.tracing")

_provider: TracerProvider | None = None

try:
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
except ImportError:
    AsyncPGInstrumentor = None

try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except ImportError:
    FastAPIInstrumentor = None

try:
    from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer
except ImportError:
    GrpcInstrumentorServer = None

try:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
except ImportError:
    HTTPXClientInstrumentor = None

try:
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
except ImportError:
    LoggingInstrumentor = None

try:
    from opentelemetry.instrumentation.redis import RedisInstrumentor
except ImportError:
    RedisInstrumentor = None

try:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
except ImportError:
    SQLAlchemyInstrumentor = None


def setup_tracing(
    app=None,
    service_name: str = "python-api",
    enable_httpx: bool = False,
    enable_grpc_server: bool = False,
) -> TracerProvider | None:
    global _provider  # noqa: PLW0603

    if not app_config.enable_tracing:
        logger.info("Tracing disabled")
        return None

    try:
        resource = Resource(
            attributes={
                "service.name": service_name,
                "service.namespace": "api-lab",
                "service.version": app_config.component_version,
                "deployment.environment": app_config.environment,
            }
        )
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=app_config.otel_exporter_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _provider = provider

        if app and FastAPIInstrumentor:
            FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)

        if SQLAlchemyInstrumentor:
            SQLAlchemyInstrumentor().instrument(tracer_provider=provider)

        if AsyncPGInstrumentor:
            AsyncPGInstrumentor().instrument(tracer_provider=provider)

        if RedisInstrumentor:
            RedisInstrumentor().instrument(tracer_provider=provider)

        if LoggingInstrumentor:
            LoggingInstrumentor().instrument(tracer_provider=provider)

        if enable_httpx and HTTPXClientInstrumentor:
            HTTPXClientInstrumentor().instrument(tracer_provider=provider)

        if enable_grpc_server and GrpcInstrumentorServer:
            GrpcInstrumentorServer().instrument(tracer_provider=provider)

        logger.info("OpenTelemetry tracing enabled for %s", service_name)
        return provider
    except Exception as e:
        logger.warning("Failed to setup tracing: %s", e)
        return None


def shutdown_tracing():
    global _provider  # noqa: PLW0603
    if _provider:
        _provider.force_flush()
        _provider.shutdown()
        _provider = None
        logger.info("Tracing shut down")


def get_tracer(name: str = "api-lab") -> trace.Tracer:
    return trace.get_tracer(name)
