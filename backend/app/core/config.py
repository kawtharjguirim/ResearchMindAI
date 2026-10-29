from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ResearchMind AI API"
    api_prefix: str = "/api/v1"
    environment: str = "development"

    # Database (SQLite for quick local dev, PostgreSQL in Docker / production)
    database_url: str = "sqlite:///./researchmind.db"

    # Supabase Auth
    supabase_url: str = ""
    # Legacy HS256 secret (Project Settings > API > JWT Secret). Leave empty if the
    # project uses asymmetric signing keys: tokens are then verified through JWKS.
    supabase_jwt_secret: str = ""
    supabase_jwt_audience: str = "authenticated"

    # Comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
