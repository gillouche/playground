import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import yaml


@dataclass
class PostgresConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "playground"
    user: str = "playground"
    password: str = ""

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    password: str = ""


@dataclass
class KafkaConfig:
    bootstrap_servers: str = "localhost:9092"
    topic: str = "infra-check"


@dataclass
class MongoDBConfig:
    host: str = "localhost"
    port: int = 27017
    database: str = "playground"
    user: str = "playground"
    password: str = ""

    @property
    def url(self) -> str:
        if self.user and self.password:
            return f"mongodb://{self.user}:{self.password}@{self.host}:{self.port}"
        return f"mongodb://{self.host}:{self.port}"


@dataclass
class Config:
    postgres: PostgresConfig = field(default_factory=PostgresConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    kafka: KafkaConfig = field(default_factory=KafkaConfig)
    mongodb: MongoDBConfig = field(default_factory=MongoDBConfig)
    environment: str = "local"
    log_level: str = "INFO"


def load_config(config_path: Optional[Path] = None) -> Config:
    config = Config()

    if config_path is None:
        config_path = Path("config.yaml")

    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

        if "postgres" in data:
            for key, value in data["postgres"].items():
                if hasattr(config.postgres, key):
                    setattr(config.postgres, key, value)

        if "redis" in data:
            for key, value in data["redis"].items():
                if hasattr(config.redis, key):
                    setattr(config.redis, key, value)

        if "kafka" in data:
            for key, value in data["kafka"].items():
                if hasattr(config.kafka, key):
                    setattr(config.kafka, key, value)

        if "mongodb" in data:
            for key, value in data["mongodb"].items():
                if hasattr(config.mongodb, key):
                    setattr(config.mongodb, key, value)

    config.postgres.host = os.environ.get("POSTGRES_HOST", config.postgres.host)
    config.postgres.port = int(os.environ.get("POSTGRES_PORT", config.postgres.port))
    config.postgres.database = os.environ.get("POSTGRES_DB", config.postgres.database)
    config.postgres.user = os.environ.get("POSTGRES_USER", config.postgres.user)
    config.postgres.password = os.environ.get("POSTGRES_PASSWORD", config.postgres.password)

    config.redis.host = os.environ.get("REDIS_HOST", config.redis.host)
    config.redis.port = int(os.environ.get("REDIS_PORT", config.redis.port))
    config.redis.password = os.environ.get("REDIS_PASSWORD", config.redis.password)

    config.kafka.bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", config.kafka.bootstrap_servers)
    config.kafka.topic = os.environ.get("KAFKA_TOPIC", config.kafka.topic)

    config.mongodb.host = os.environ.get("MONGODB_HOST", config.mongodb.host)
    config.mongodb.port = int(os.environ.get("MONGODB_PORT", config.mongodb.port))
    config.mongodb.database = os.environ.get("MONGODB_DB", config.mongodb.database)
    config.mongodb.user = os.environ.get("MONGODB_USER", config.mongodb.user)
    config.mongodb.password = os.environ.get("MONGODB_PASSWORD", config.mongodb.password)

    config.environment = os.environ.get("ENVIRONMENT", config.environment)
    config.log_level = os.environ.get("LOG_LEVEL", config.log_level)

    return config
