import os
from dataclasses import dataclass, field
from pathlib import Path

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

    @property
    def url(self) -> str:
        password = os.environ.get("MONGODB_PASSWORD", "")
        if self.user and password:
            return f"mongodb://{self.user}:{password}@{self.host}:{self.port}"
        return f"mongodb://{self.host}:{self.port}"


@dataclass
class Config:
    postgres: PostgresConfig = field(default_factory=PostgresConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    kafka: KafkaConfig = field(default_factory=KafkaConfig)
    mongodb: MongoDBConfig = field(default_factory=MongoDBConfig)
    environment: str = "local"
    log_level: str = "INFO"


def _apply_yaml_config(target: object, data: dict, section: str) -> None:
    if section in data:
        for key, value in data[section].items():
            if hasattr(target, key):
                setattr(target, key, value)


def load_config(config_path: Path | None = None) -> Config:
    config = Config()

    if config_path is None:
        config_path = Path("config.yaml")

    if config_path.exists():
        with config_path.open() as f:
            data = yaml.safe_load(f) or {}

        _apply_yaml_config(config.postgres, data, "postgres")
        _apply_yaml_config(config.redis, data, "redis")
        _apply_yaml_config(config.kafka, data, "kafka")
        _apply_yaml_config(config.mongodb, data, "mongodb")

    config.postgres.host = os.environ.get("POSTGRES_HOST", config.postgres.host)
    config.postgres.port = int(os.environ.get("POSTGRES_PORT", config.postgres.port))
    config.postgres.database = os.environ.get("POSTGRES_DB", config.postgres.database)
    config.postgres.user = os.environ.get("POSTGRES_USER", config.postgres.user)
    config.postgres.password = os.environ.get("POSTGRES_PASSWORD", config.postgres.password)

    config.redis.host = os.environ.get("REDIS_HOST", config.redis.host)
    config.redis.port = int(os.environ.get("REDIS_PORT", config.redis.port))
    config.redis.password = os.environ.get("REDIS_PASSWORD", config.redis.password)

    config.kafka.bootstrap_servers = os.environ.get(
        "KAFKA_BOOTSTRAP_SERVERS", config.kafka.bootstrap_servers
    )
    config.kafka.topic = os.environ.get("KAFKA_TOPIC", config.kafka.topic)

    config.mongodb.host = os.environ.get("MONGODB_HOST", config.mongodb.host)
    config.mongodb.port = int(os.environ.get("MONGODB_PORT", config.mongodb.port))
    config.mongodb.database = os.environ.get("MONGODB_DB", config.mongodb.database)
    config.mongodb.user = os.environ.get("MONGODB_USER", config.mongodb.user)

    config.environment = os.environ.get("ENVIRONMENT", config.environment)
    config.log_level = os.environ.get("LOG_LEVEL", config.log_level)

    return config
