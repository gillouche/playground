import logging
import sys
import os
import platform
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator
import uvicorn
from fastapi import FastAPI
from lib import get_greeting, sanitize


logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("demo-app")

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
