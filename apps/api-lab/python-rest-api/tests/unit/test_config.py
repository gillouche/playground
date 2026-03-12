import os
from unittest.mock import patch

from config import AppConfig, GrpcConfig, PostgresConfig, RedisConfig


class TestPostgresConfig:
    def test_default_values(self):
        cfg = PostgresConfig()
        assert cfg.host == "localhost"
        assert cfg.port == 5432
        assert cfg.database == "api_lab"
        assert cfg.user == "api_lab"
        assert cfg.password == "api_lab"

    def test_url_property(self):
        cfg = PostgresConfig()
        assert cfg.url == "postgresql+asyncpg://api_lab:api_lab@localhost:5432/api_lab"

    def test_url_with_custom_values(self):
        cfg = PostgresConfig(
            host="db.example.com",
            port=5433,
            database="mydb",
            user="admin",
            password="secret",
        )
        assert cfg.url == "postgresql+asyncpg://admin:secret@db.example.com:5433/mydb"

    def test_env_prefix(self):
        env = {
            "POSTGRES_HOST": "pg-host",
            "POSTGRES_PORT": "5555",
            "POSTGRES_DATABASE": "testdb",
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = PostgresConfig()
        assert cfg.host == "pg-host"
        assert cfg.port == 5555
        assert cfg.database == "testdb"
        assert cfg.user == "testuser"
        assert cfg.password == "testpass"


class TestRedisConfig:
    def test_default_values(self):
        cfg = RedisConfig()
        assert cfg.host == "localhost"
        assert cfg.port == 6379
        assert cfg.password == ""

    def test_url_without_password(self):
        cfg = RedisConfig()
        assert cfg.url == "redis://localhost:6379/0"

    def test_url_with_password(self):
        cfg = RedisConfig(password="s3cret")
        assert cfg.url == "redis://:s3cret@localhost:6379/0"

    def test_url_with_custom_host_port_and_password(self):
        cfg = RedisConfig(host="redis.example.com", port=6380, password="pass123")
        assert cfg.url == "redis://:pass123@redis.example.com:6380/0"

    def test_env_prefix(self):
        env = {
            "REDIS_HOST": "redis-host",
            "REDIS_PORT": "6380",
            "REDIS_PASSWORD": "redispass",
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = RedisConfig()
        assert cfg.host == "redis-host"
        assert cfg.port == 6380
        assert cfg.password == "redispass"


class TestGrpcConfig:
    def test_default_values(self):
        cfg = GrpcConfig()
        assert cfg.port == 50051

    def test_env_prefix(self):
        with patch.dict(os.environ, {"GRPC_PORT": "9090"}, clear=False):
            cfg = GrpcConfig()
        assert cfg.port == 9090


class TestAppConfig:
    def test_default_values(self):
        cfg = AppConfig()
        assert cfg.environment == "local"
        assert cfg.app == "api-lab"
        assert cfg.component == "python-api"
        assert cfg.app_version == "unknown"
        assert cfg.component_version == "unknown"
        assert cfg.log_level == "INFO"
        assert cfg.enable_tracing is False
        assert cfg.otel_exporter_otlp_endpoint == "http://localhost:4317"
        assert cfg.git_tag == "unknown"
        assert cfg.git_commit == "unknown"

    def test_env_prefix_is_empty(self):
        env = {
            "ENVIRONMENT": "production",
            "LOG_LEVEL": "DEBUG",
            "ENABLE_TRACING": "true",
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = AppConfig()
        assert cfg.environment == "production"
        assert cfg.log_level == "DEBUG"
        assert cfg.enable_tracing is True
