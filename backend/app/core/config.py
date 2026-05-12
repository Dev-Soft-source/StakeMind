from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent
ENV_FILES = tuple(
    str(path) for path in (BACKEND_DIR / ".env", ROOT_DIR / ".env") if path.is_file()
) or (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "StakeMind API"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql+asyncpg://stakemind:stakemind@localhost:5432/stakemind",
        validation_alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=10, validation_alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, validation_alias="DB_MAX_OVERFLOW")

    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    redis_default_ttl_seconds: int = Field(
        default=300, validation_alias="REDIS_DEFAULT_TTL_SECONDS"
    )
    redis_session_ttl_seconds: int = Field(
        default=86400, validation_alias="REDIS_SESSION_TTL_SECONDS"
    )

    cors_origins: str = Field(
        default="http://localhost:3000",
        validation_alias="CORS_ORIGINS",
    )

    bittensor_rpc_url: str = Field(
        default="https://entrypoint-finney.opentensor.ai:443",
        validation_alias="BITTENSOR_RPC_URL",
    )
    bittensor_rpc_timeout_seconds: float = Field(
        default=10.0,
        validation_alias="BITTENSOR_RPC_TIMEOUT_SECONDS",
    )
    bittensor_rpc_max_retries: int = Field(
        default=3,
        validation_alias="BITTENSOR_RPC_MAX_RETRIES",
    )
    bittensor_ingestion_subnet_limit: int = Field(
        default=16,
        validation_alias="BITTENSOR_INGESTION_SUBNET_LIMIT",
    )

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            return url
        if url.startswith("postgresql+psycopg2://"):
            return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
