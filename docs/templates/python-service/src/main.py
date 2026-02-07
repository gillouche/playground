"""
{{SERVICE_NAME}} - Main Application Entry Point

Replace {{SERVICE_NAME}} with your service name.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="{{SERVICE_NAME}}",
    description="{{SERVICE_DESCRIPTION}}",
    version="0.1.0",
    lifespan=lifespan,
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)


@app.get("/healthz")
async def healthz():
    """Kubernetes liveness probe."""
    return {"status": "healthy"}


@app.get("/ready")
async def ready():
    """Kubernetes readiness probe."""
    return {"status": "ready"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"service": "{{SERVICE_NAME}}", "status": "running"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
