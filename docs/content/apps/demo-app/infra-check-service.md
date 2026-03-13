# Infra Check Service

A multi-backend verification service that tests connectivity to PostgreSQL, Redis, Kafka, and MongoDB.

## Overview

| Attribute | Value |
|-----------|-------|
| Framework | FastAPI |
| Port | 8080 |
| Source | `apps/demo-app/infra-check-service/` |

## Endpoints

Each backend has read/write and health endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/postgres` | Read/write test to PostgreSQL |
| GET | `/postgres/health` | PostgreSQL connectivity check |
| GET | `/redis` | Get/set test to Redis |
| GET | `/redis/health` | Redis connectivity check |
| GET | `/kafka` | Produce/consume test to Kafka |
| GET | `/kafka/health` | Kafka connectivity check |
| GET | `/mongodb` | Insert/find test to MongoDB |
| GET | `/mongodb/health` | MongoDB connectivity check |
| GET | `/ready` | Readiness (fails if any backend unhealthy) |
| GET | `/metrics` | Prometheus metrics |

## Configuration

Configuration via environment variables or `config.yaml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka brokers |
| `MONGODB_HOST` | `localhost` | MongoDB host |
| `MONGODB_PORT` | `27017` | MongoDB port |

## Clients

Each backend has a dedicated async client:

- **PostgreSQL:** asyncpg with SQLAlchemy URL building
- **Redis:** redis-py async client
- **Kafka:** aiokafka producer/consumer
- **MongoDB:** Motor async client

## Running

```bash
bazel run //apps/demo-app/infra-check-service:infra-check-service
```

Requires local infrastructure running (see [Local Development](../../common/local-development.md)).
