import os
from pathlib import Path
import tempfile
from config import load_config, PostgresConfig


def test_load_config_defaults():
    config = load_config(Path("/nonexistent/path/config.yaml"))
    assert config.postgres.host == "localhost"
    assert config.postgres.port == 5432
    assert config.redis.host == "localhost"
    assert config.kafka.bootstrap_servers == "localhost:9092"
    assert config.mongodb.host == "localhost"


def test_load_config_from_yaml():
    yaml_content = """
postgres:
  host: db.example.com
  port: 5433
redis:
  host: cache.example.com
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = load_config(Path(f.name))

    assert config.postgres.host == "db.example.com"
    assert config.postgres.port == 5433
    assert config.redis.host == "cache.example.com"
    assert config.mongodb.host == "localhost"

    os.unlink(f.name)


def test_load_config_env_override(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "env-db.example.com")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "kafka1:9092,kafka2:9092")

    config = load_config(Path("/nonexistent/path/config.yaml"))

    assert config.postgres.host == "env-db.example.com"
    assert config.redis.port == 6380
    assert config.kafka.bootstrap_servers == "kafka1:9092,kafka2:9092"


def test_postgres_url():
    pg = PostgresConfig(host="db", port=5432, database="test", user="u", password="p")
    assert pg.url == "postgresql+asyncpg://u:p@db:5432/test"
