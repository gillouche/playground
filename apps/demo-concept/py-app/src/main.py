import html
import logging
import sys
import os
import platform
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from lib import get_greeting, sanitize


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("demo-concept")

@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup logic
    logger.info("Demo Concept Application Starting...")
    logger.info(f"Architecture: {platform.machine()}")
    logger.info(f"System: {platform.system()}")
    logger.info(f"Python Version: {sys.version.split()[0]}")
    logger.info(f"Environment: {os.environ}")
    
    greeting = get_greeting("User")
    logger.info(f"App says: {greeting}")
    
    yield
    # Shutdown logic if needed

app = FastAPI(lifespan=lifespan)

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

def main():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    main()
