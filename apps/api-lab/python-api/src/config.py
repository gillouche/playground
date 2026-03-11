from pydantic_settings import BaseSettings


class PostgresConfig(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    database: str = "api_lab"
    user: str = "api_lab"
    password: str = "api_lab"

    model_config = {"env_prefix": "POSTGRES_"}

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class RedisConfig(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    password: str = ""

    model_config = {"env_prefix": "REDIS_"}

    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/0"
        return f"redis://{self.host}:{self.port}/0"


class GrpcConfig(BaseSettings):
    port: int = 50051

    model_config = {"env_prefix": "GRPC_"}


class AppConfig(BaseSettings):
    environment: str = "local"
    app: str = "api-lab"
    component: str = "python-api"
    app_version: str = "unknown"
    component_version: str = "unknown"
    log_level: str = "INFO"
    enable_tracing: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    git_tag: str = "unknown"
    git_commit: str = "unknown"

    model_config = {"env_prefix": ""}


postgres_config = PostgresConfig()
redis_config = RedisConfig()
grpc_config = GrpcConfig()
app_config = AppConfig()
