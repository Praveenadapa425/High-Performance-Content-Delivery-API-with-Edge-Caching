from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "High-Performance Content Delivery API"
    app_env: str = "development"
    app_port: int = 8000

    database_url: str = "sqlite+pysqlite:///./content_api.db"

    s3_endpoint: str = "localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "assets"
    s3_secure: bool = False

    token_ttl_seconds: int = 300
    cdn_allowed_ips: str = "127.0.0.1"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
