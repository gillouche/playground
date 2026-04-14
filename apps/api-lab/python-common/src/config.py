from urllib.parse import quote_plus

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
        encoded_password = quote_plus(self.password)
        return f"postgresql+asyncpg://{self.user}:{encoded_password}@{self.host}:{self.port}/{self.database}"


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


class KeycloakConfig(BaseSettings):
    server_url: str = "http://localhost:8180"
    realm: str = "api-lab"
    client_id: str = "api-lab"
    client_secret: str = "api-lab-secret"
    auth_service_client_id: str = "api-lab-auth-service"
    auth_service_client_secret: str = "api-lab-auth-service-secret"

    model_config = {"env_prefix": "KEYCLOAK_"}

    @property
    def issuer_url(self) -> str:
        return f"{self.server_url}/realms/{self.realm}"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer_url}/protocol/openid-connect/certs"

    @property
    def token_url(self) -> str:
        return f"{self.issuer_url}/protocol/openid-connect/token"

    @property
    def admin_url(self) -> str:
        return f"{self.server_url}/admin/realms/{self.realm}"


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
keycloak_config = KeycloakConfig()
app_config = AppConfig()
