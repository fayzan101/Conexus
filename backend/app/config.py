from functools import lru_cache

from pydantic import model_validator
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
    default_tenant_id: str = "default"

    database_url: str = "postgresql+psycopg://eb:eb@localhost:5432/enterprise_brain"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "eb_chunks"

    redis_url: str = "redis://localhost:6379/0"
    queue_backend: str = "memory"
    queue_inline: bool = True
    worker_poll_seconds: float = 1.0
    connector_auto_ingest: bool = True
    event_bus_backend: str = "memory"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_ingest: str = "eb.ingest.events"
    queue_max_depth: int = 10_000

    object_store_endpoint: str = "http://localhost:9000"
    object_store_access_key: str = "minioadmin"
    object_store_secret_key: str = "minioadmin"
    object_store_bucket: str = "enterprise-brain"
    object_store_region: str = "us-east-1"
    object_store_use_ssl: bool = False

    auth_provider: str = "dev"  # dev | oidc | saml
    auth_issuer: str = ""
    auth_audience: str = ""
    auth_jwks_url: str = ""
    auth_client_id: str = ""
    auth_client_secret: str = ""
    auth_invite_expire_hours: int = 72
    refresh_token_expire_days: int = 14
    access_token_expire_minutes: int = 60 * 12
    saml_sp_entity_id: str = ""
    saml_acs_url: str = ""
    saml_idp_entity_id: str = ""
    saml_idp_sso_url: str = ""
    saml_idp_x509_cert: str = ""
    scim_bearer_token: str = ""
    kms_backend: str = "local"  # local | vault
    vault_addr: str = ""
    vault_token: str = ""
    retention_days_default: int = 365
    require_tls: bool = False
    encryption_at_rest_verified: bool = False
    dev_admin_email: str = "admin@enterprisebrain.local"
    dev_admin_password: str = "admin123"
    dev_user_email: str = "user@enterprisebrain.local"
    dev_user_password: str = "user123"

    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_mode: str = "public"  # public | private | airgap
    llm_allow_public_egress: bool = True
    llm_no_train: bool = True
    require_llm_key: bool = False
    embedding_provider: str = "hash"
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 384

    hybrid_graph_hops: int = 1
    hybrid_graph_limit: int = 8
    hybrid_rerank: bool = True
    auto_link_min_confidence: float = 0.55

    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_signing_secret: str = ""
    slack_redirect_uri: str = ""

    github_client_id: str = ""
    github_client_secret: str = ""
    github_webhook_secret: str = ""
    github_redirect_uri: str = ""

    ms_client_id: str = ""
    ms_client_secret: str = ""
    ms_tenant_id: str = "common"
    ms_redirect_uri: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    jira_client_id: str = ""
    jira_client_secret: str = ""
    jira_redirect_uri: str = ""
    jira_cloud_id: str = ""
    jira_base_url: str = ""

    ff_graphql: bool = False
    ff_connectors: bool = False
    ff_research_agent: bool = False
    auto_migrate: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def versioned_collection(self) -> str:
        provider = (self.embedding_provider or "hash").replace("/", "_")
        return f"{self.qdrant_collection}_{provider}_{self.embedding_dim}"

    @model_validator(mode="after")
    def _guard_dev_auth_outside_local(self) -> "Settings":
        env = (self.environment or "local").lower()
        if self.auth_provider == "dev" and env not in {"local", "test", "development"}:
            raise ValueError(
                "AUTH_PROVIDER=dev is only allowed when ENVIRONMENT is local|test|development. "
                "Use AUTH_PROVIDER=oidc or saml for staging/production."
            )
        if self.require_llm_key and not self.llm_api_key and env not in {"local", "test"}:
            raise ValueError("LLM_API_KEY is required when REQUIRE_LLM_KEY=true outside local/test.")
        mode = (self.llm_mode or "public").lower()
        if mode in {"private", "airgap"} and not self.llm_allow_public_egress:
            public_hosts = ("api.openai.com", "openai.azure.com")
            base = (self.llm_base_url or "").lower()
            if any(h in base for h in public_hosts):
                raise ValueError(
                    "LLM_MODE=private|airgap with LLM_ALLOW_PUBLIC_EGRESS=false forbids public LLM hosts. "
                    "Set LLM_BASE_URL to a VPC/private endpoint."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
