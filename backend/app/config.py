"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_name: str = "DocLens"
    environment: str = "development"
    api_prefix: str = "/api"

    # Database
    database_url: str = "postgresql+psycopg://doclens:doclens@localhost:5432/doclens"

    # Comma-separated list of allowed browser origins (the deployed frontend URL).
    cors_origins: str = "http://localhost:3000"

    # Per-IP rate limiting on expensive endpoints (set false to disable, e.g. in tests).
    rate_limit_enabled: bool = True

    # Authentication
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # LLM provider
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    chat_model: str = "gemini-2.5-flash"
    embedding_model: str = "models/gemini-embedding-001"
    # gemini-embedding-001 defaults to 3072 dims but supports truncation; we
    # request this size explicitly so it matches the vector column.
    embedding_dimension: int = 768

    # Retrieval
    chunk_size: int = 900
    chunk_overlap: int = 150
    retrieval_top_k: int = 5

    # Uploads
    upload_dir: str = "storage/uploads"
    max_upload_mb: int = 25

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        """Normalise managed-host URLs (e.g. ``postgresql://``) to the psycopg driver."""
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
