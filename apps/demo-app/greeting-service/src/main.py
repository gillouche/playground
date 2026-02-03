import logging
import sys
import os
import platform
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator
import uvicorn
from fastapi import FastAPI
from lib import get_greeting, sanitize

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("demo-app")

def setup_opentelemetry(app: FastAPI):
    if os.environ.get("ENABLE_TRACING", "true").lower() == "true":
        resource = Resource(attributes={
            "service.name": "greeting-service",
            "service.namespace": os.environ.get("NAMESPACE", "default"),
            "deployment.environment": os.environ.get("ENVIRONMENT", "unknown")
        })

        trace.set_tracer_provider(TracerProvider(resource=resource))
        tracer_provider = trace.get_tracer_provider()

        otlp_exporter = OTLPSpanExporter(endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo.monitoring.svc.cluster.local:4317"))
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)

        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
        logger.info("OpenTelemetry instrumentation enabled.")

@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup logic
    logger.info("Demo App Application Starting...")
    logger.info(f"Architecture: {platform.machine()}")
    logger.info(f"System: {platform.system()}")
    logger.info(f"Python Version: {sys.version.split()[0]}")
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'unknown')}")
    logger.debug(f"Hostname: {os.environ.get('HOSTNAME', 'unknown')}")

    greeting = get_greeting("User")
    logger.info(f"App says: {greeting}")

    yield


app = FastAPI(lifespan=lifespan)
Instrumentator().instrument(app).expose(app)
setup_opentelemetry(app)


@app.get("/")
async def root(name: str | None = None):
    subject = sanitize(name)
    if not subject:
        subject = "World"
    return {"message": get_greeting(subject)}

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    return {"status": "ready"}

@app.get("/info")
async def info():
    """
    Return operational information about the pod's environment.
    Useful for verification and observability.
    """
    return {
        "hostname": os.environ.get("HOSTNAME", platform.node()),
        "app_version": os.environ.get("APP_VERSION"),
        "environment": os.environ.get("ENVIRONMENT"),
        "app": os.environ.get("APP"),
        "component": os.environ.get("COMPONENT"),
        "node": os.environ.get("NODE_NAME"),
        "pod_ip": os.environ.get("POD_IP"),
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
        "git_tag": os.environ.get("GIT_TAG"),
        "git_commit": os.environ.get("GIT_COMMIT"),
    }

def main():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    main()
