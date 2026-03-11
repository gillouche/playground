import logging
import os

from fastapi import FastAPI

logger = logging.getLogger("api-lab.tracing")


def setup_tracing(app: FastAPI, service_name: str = "python-api"):
    from config import app_config

    if not app_config.enable_tracing:
        logger.info("Tracing disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource(
            attributes={
                "service.name": service_name,
                "service.namespace": os.environ.get("NAMESPACE", "default"),
                "deployment.environment": app_config.environment,
            }
        )
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=app_config.otel_exporter_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        logger.info("OpenTelemetry tracing enabled")
    except Exception as e:
        logger.warning(f"Failed to setup tracing: {e}")
