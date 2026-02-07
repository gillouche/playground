import logging
import os
import platform
import sys
from contextlib import asynccontextmanager

import uvicorn
from clients.kafka import KafkaClient
from clients.mongodb import MongoClient
from clients.postgres import PostgresClient
from clients.redis import RedisClient
from config import load_config
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("infra-check-service")

config = load_config()

clients: dict = {
    "postgres": None,
    "redis": None,
    "kafka": None,
    "mongo": None,
}


class WriteRequest(BaseModel):
    key: str
    value: str


class KafkaMessage(BaseModel):
    message: str
    topic: str | None = None


@asynccontextmanager
async def lifespan(_application: FastAPI):
    logger.info("Infra Check Service Starting...")
    logger.info(f"Architecture: {platform.machine()}")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Postgres: {config.postgres.host}:{config.postgres.port}")
    logger.info(f"Redis: {config.redis.host}:{config.redis.port}")
    logger.info(f"Kafka: {config.kafka.bootstrap_servers}")
    logger.info(f"MongoDB: {config.mongodb.host}:{config.mongodb.port}")

    clients["postgres"] = PostgresClient(config.postgres)
    clients["redis"] = RedisClient(config.redis)
    clients["kafka"] = KafkaClient(config.kafka)
    clients["mongo"] = MongoClient(config.mongodb)

    await clients["postgres"].connect()
    logger.info("PostgreSQL connected")

    await clients["redis"].connect()
    logger.info("Redis connected")

    await clients["kafka"].connect()
    logger.info("Kafka connected")

    await clients["mongo"].connect()
    logger.info("MongoDB connected")

    yield

    await clients["postgres"].disconnect()
    await clients["redis"].disconnect()
    await clients["kafka"].disconnect()
    await clients["mongo"].disconnect()
    logger.info("All connections closed")


app = FastAPI(title="Infra Check Service", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)


@app.get("/")
async def root():
    return {
        "service": "infra-check-service",
        "environment": config.environment,
        "endpoints": ["/postgres", "/redis", "/kafka", "/mongodb"],
    }


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    if not all(clients.values()):
        raise HTTPException(status_code=503, detail="Clients not initialized")

    pg_health = await clients["postgres"].health_check()
    redis_health = await clients["redis"].health_check()
    kafka_health = await clients["kafka"].health_check()
    mongo_health = await clients["mongo"].health_check()

    if (
        pg_health.get("status") != "healthy"
        or redis_health.get("status") != "healthy"
        or kafka_health.get("status") != "healthy"
        or mongo_health.get("status") != "healthy"
    ):
        raise HTTPException(status_code=503, detail="One or more clients are unhealthy")

    return {"status": "ready"}


@app.get("/info")
async def info():
    return {
        "hostname": os.environ.get("HOSTNAME", platform.node()),
        "app_version": os.environ.get("APP_VERSION"),
        "environment": config.environment,
        "app": os.environ.get("APP"),
        "component": os.environ.get("COMPONENT"),
        "node": os.environ.get("NODE_NAME"),
        "pod_ip": os.environ.get("POD_IP"),
        "log_level": config.log_level,
        "git_tag": os.environ.get("GIT_TAG"),
        "git_commit": os.environ.get("GIT_COMMIT"),
    }


@app.get("/postgres")
async def postgres_read(key: str | None = None):
    pg = clients["postgres"]
    if not pg or not pg.engine:
        raise HTTPException(status_code=503, detail="PostgreSQL not connected")
    return await pg.read(key)


@app.post("/postgres")
async def postgres_write(req: WriteRequest):
    pg = clients["postgres"]
    if not pg or not pg.engine:
        raise HTTPException(status_code=503, detail="PostgreSQL not connected")
    return await pg.write(req.key, req.value)


@app.get("/postgres/health")
async def postgres_health():
    pg = clients["postgres"]
    if not pg:
        return {"status": "not initialized"}
    return await pg.health_check()


@app.get("/redis")
async def redis_read(key: str | None = None):
    redis = clients["redis"]
    if not redis or not redis.client:
        raise HTTPException(status_code=503, detail="Redis not connected")
    return await redis.get(key)


@app.post("/redis")
async def redis_write(req: WriteRequest):
    redis = clients["redis"]
    if not redis or not redis.client:
        raise HTTPException(status_code=503, detail="Redis not connected")
    return await redis.set(req.key, req.value)


@app.get("/redis/health")
async def redis_health():
    redis = clients["redis"]
    if not redis:
        return {"status": "not initialized"}
    return await redis.health_check()


@app.get("/kafka")
async def kafka_consume(topic: str | None = None, timeout: float = 5.0):
    kafka = clients["kafka"]
    if not kafka or not kafka.producer:
        raise HTTPException(status_code=503, detail="Kafka not connected")
    return await kafka.consume(topic, timeout)


@app.post("/kafka")
async def kafka_produce(msg: KafkaMessage):
    kafka = clients["kafka"]
    if not kafka or not kafka.producer:
        raise HTTPException(status_code=503, detail="Kafka not connected")
    return await kafka.produce(msg.message, msg.topic)


@app.get("/kafka/health")
async def kafka_health():
    kafka = clients["kafka"]
    if not kafka:
        return {"status": "not initialized"}
    return await kafka.health_check()


@app.get("/mongodb")
async def mongodb_read(key: str | None = None):
    mongo = clients["mongo"]
    if not mongo or not mongo.client:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    return await mongo.find(key)


@app.post("/mongodb")
async def mongodb_write(req: WriteRequest):
    mongo = clients["mongo"]
    if not mongo or not mongo.client:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    return await mongo.insert(req.key, req.value)


@app.get("/mongodb/health")
async def mongodb_health():
    mongo = clients["mongo"]
    if not mongo:
        return {"status": "not initialized"}
    return await mongo.health_check()


def main():
    uvicorn.run(app, host="0.0.0.0", port=8080, loop="asyncio")


if __name__ == "__main__":
    main()
