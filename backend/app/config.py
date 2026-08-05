from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    log_level: str = "info"
    environment: str = "local"
    secret_key: str = "dev-secret-change-me-in-production"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg://eb:eb@localhost:5432/enterprise_brain"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "eb_chunks"

    redis_url: str = "redis://localhost:6379/0"

    object_store_endpoint: str = "http://localhost:9000"
    object_store_access_key: str = "minioadmin"
    object_store_secret_key: str = "minioadmin"
    object_store_bucket: str = "enterprise-brain"
    object_store_region: str = "us-east-1"
    object_store_use_ssl: bool = False

    auth_provider: str = "dev"
    auth_issuer: str = ""
    auth_audience: str = ""
    auth_client_id: str = ""
    auth_client_secret: str = ""
    dev_admin_email: str = "admin@enterprisebrain.local"
    dev_admin_password: str = "admin123"
    dev_user_email: str = "user@enterprisebrain.local"
    dev_user_password: str = "user123"

    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    embedding_provider: str = "hash"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    ff_graphql: bool = False
    ff_connectors: bool = False
    ff_research_agent: bool = False
    auto_migrate: bool = True

    access_token_expire_minutes: int = 60 * 12

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
