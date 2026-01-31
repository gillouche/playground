import logging
import sys
import os
import platform
from contextlib import asynccontextmanager
from typing import Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from config import load_config
from clients.postgres import PostgresClient
from clients.redis import RedisClient
from clients.kafka import KafkaClient
from clients.mongodb import MongoClient


logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("infra-check-service")

config = load_config()
postgres_client: Optional[PostgresClient] = None
redis_client: Optional[RedisClient] = None
kafka_client: Optional[KafkaClient] = None
mongo_client: Optional[MongoClient] = None


class WriteRequest(BaseModel):
    key: str
    value: str


class KafkaMessage(BaseModel):
    message: str
    topic: Optional[str] = None


@asynccontextmanager
async def lifespan(application: FastAPI):
    global postgres_client, redis_client, kafka_client, mongo_client

    logger.info("Infra Check Service Starting...")
    logger.info(f"Architecture: {platform.machine()}")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"Postgres: {config.postgres.host}:{config.postgres.port}")
    logger.info(f"Redis: {config.redis.host}:{config.redis.port}")
    logger.info(f"Kafka: {config.kafka.bootstrap_servers}")
    logger.info(f"MongoDB: {config.mongodb.host}:{config.mongodb.port}")

    postgres_client = PostgresClient(config.postgres)
    redis_client = RedisClient(config.redis)
    kafka_client = KafkaClient(config.kafka)
    mongo_client = MongoClient(config.mongodb)

    await postgres_client.connect()
    logger.info("PostgreSQL connected")

    await redis_client.connect()
    logger.info("Redis connected")

    await kafka_client.connect()
    logger.info("Kafka connected")

    await mongo_client.connect()
    logger.info("MongoDB connected")

    yield

    await postgres_client.disconnect()
    await redis_client.disconnect()
    await kafka_client.disconnect()
    await mongo_client.disconnect()
    logger.info("All connections closed")


app = FastAPI(title="Infra Check Service", lifespan=lifespan)


@app.get("/")
async def root():
    return {
        "service": "infra-check-service",
        "environment": config.environment,
        "endpoints": ["/postgres", "/redis", "/kafka", "/mongodb"]
    }


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    if not all([postgres_client, redis_client, kafka_client, mongo_client]):
        raise HTTPException(status_code=503, detail="Clients not initialized")
        
    pg_health = await postgres_client.health_check()
    redis_health = await redis_client.health_check()
    kafka_health = await kafka_client.health_check()
    mongo_health = await mongo_client.health_check()
    
    if (pg_health.get("status") != "healthy" or 
        redis_health.get("status") != "healthy" or 
        kafka_health.get("status") != "healthy" or 
        mongo_health.get("status") != "healthy"):
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
async def postgres_read(key: Optional[str] = None):
    if not postgres_client or not postgres_client.engine:
        raise HTTPException(status_code=503, detail="PostgreSQL not connected")
    return await postgres_client.read(key)


@app.post("/postgres")
async def postgres_write(req: WriteRequest):
    if not postgres_client or not postgres_client.engine:
        raise HTTPException(status_code=503, detail="PostgreSQL not connected")
    return await postgres_client.write(req.key, req.value)


@app.get("/postgres/health")
async def postgres_health():
    if not postgres_client:
        return {"status": "not initialized"}
    return await postgres_client.health_check()


@app.get("/redis")
async def redis_read(key: Optional[str] = None):
    if not redis_client or not redis_client.client:
        raise HTTPException(status_code=503, detail="Redis not connected")
    return await redis_client.get(key)


@app.post("/redis")
async def redis_write(req: WriteRequest):
    if not redis_client or not redis_client.client:
        raise HTTPException(status_code=503, detail="Redis not connected")
    return await redis_client.set(req.key, req.value)


@app.get("/redis/health")
async def redis_health():
    if not redis_client:
        return {"status": "not initialized"}
    return await redis_client.health_check()


@app.get("/kafka")
async def kafka_consume(topic: Optional[str] = None, timeout: float = 5.0):
    if not kafka_client or not kafka_client.producer:
        raise HTTPException(status_code=503, detail="Kafka not connected")
    return await kafka_client.consume(topic, timeout)


@app.post("/kafka")
async def kafka_produce(msg: KafkaMessage):
    if not kafka_client or not kafka_client.producer:
        raise HTTPException(status_code=503, detail="Kafka not connected")
    return await kafka_client.produce(msg.message, msg.topic)


@app.get("/kafka/health")
async def kafka_health():
    if not kafka_client:
        return {"status": "not initialized"}
    return await kafka_client.health_check()


@app.get("/mongodb")
async def mongodb_read(key: Optional[str] = None):
    if not mongo_client or not mongo_client.client:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    return await mongo_client.find(key)


@app.post("/mongodb")
async def mongodb_write(req: WriteRequest):
    if not mongo_client or not mongo_client.client:
        raise HTTPException(status_code=503, detail="MongoDB not connected")
    return await mongo_client.insert(req.key, req.value)


@app.get("/mongodb/health")
async def mongodb_health():
    if not mongo_client:
        return {"status": "not initialized"}
    return await mongo_client.health_check()


def main():
    uvicorn.run(app, host="0.0.0.0", port=8080, loop="asyncio")


if __name__ == "__main__":
    main()
