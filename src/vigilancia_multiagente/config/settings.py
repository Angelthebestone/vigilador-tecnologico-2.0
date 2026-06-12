from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Vigilancia Tecnologica Multiagente"
    app_env: str = "development"

    minimax_api_key: SecretStr | None = None
    minimax_model: str = "MiniMax-M2.7"
    minimax_base_url: str = "https://api.minimax.io"

    embedding_api_key: SecretStr | None = None
    embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = 768
    embedding_batch_size: int = 16

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vigilancia"

    mcp_default_timeout_ms: int = 30000
    mcp_default_retry_limit: int = 2

    # System Base (canonical global agent rules)
    system_base_version: str = "1.0.0"
    system_base_enabled: bool = True

    # Serper REST API (no MCP)
    serper_api_key: SecretStr | None = None

    # MiniMax Image MCP (Token Plan — separate key from text chat)
    minimax_image_api_key: SecretStr | None = None
    minimax_api_host: str = "https://api.minimax.io"

    # Audit mode: enable detailed logging of data transformation between layers
    audit_mode: bool = False

    # MCP Provider API Keys (all optional — system falls back gracefully)
    tavily_api_key: SecretStr | None = None
    exa_api_key: SecretStr | None = None
    jina_api_key: SecretStr | None = None
    brave_api_key: SecretStr | None = None
    firecrawl_api_key: SecretStr | None = None
    cohere_api_key: SecretStr | None = None

    # OpenAlex: email para el "polite pool" (mejores rate limits) y API key
    # premium opcional.
    openalex_email: str | None = None
    openalex_api_key: SecretStr | None = None

    # Spec 007 - Sistema de Evaluacion Inteligente (Workstreams A..E).
    eval_ws_a_enabled: bool = False
    eval_ws_b_enabled: bool = False
    eval_ws_c_enabled: bool = False
    eval_ws_d_enabled: bool = False
    eval_ws_e_enabled: bool = False

    google_factcheck_api_key: SecretStr | None = None
    retraction_watch_csv_url: str | None = None

    # Spec 008 — Config UI persistence
    workstream_overrides_path: str = "config/workstream_overrides.json"
    prompt_overrides_dir: str = "config/prompt_overrides"

    # ------------------------------------------------------------------
    # Spec 009 — Vigilador 3.0 MVP Foundation (enterprise/)
    # ------------------------------------------------------------------

    # LLM provider activo y adapters
    llm_default: str = "xiaomimimo"
    llm_adapter_xiaomimimo_enabled: bool = True
    llm_adapter_minimax_enabled: bool = False

    # Xiaomimimo (default del MVP, endpoint OpenAI-compatible)
    xiaomimimo_api_key: SecretStr | None = None
    xiaomimimo_model: str = "mimo-v2-flash"
    xiaomimimo_base_url: str = "https://platform.xiaomimimo.com/v1"

    # HealthMonitor (CQS; circuit breaker)
    health_monitor_enabled: bool = True
    health_monitor_interval_sec: int = 30
    health_monitor_cb_threshold: int = 3
    health_monitor_cb_window_sec: int = 60
    health_monitor_cooldown_sec: int = 300

    # OAuth & credentials (Fernet)
    credentials_dir: str | None = None

    # Google Workspace OAuth
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_redirect_uri: str | None = None

    # Tenant (single-tenant en MVP)
    default_tenant_id: str = "00000000-0000-0000-0000-000000000001"

    # Observabilidad
    otel_exporter_endpoint: str | None = None
    prometheus_metrics_path: str = "/metrics"

    # Spec 018 — catálogo SSOT de tools/MCPs
    catalog_path: str = "config/tools/catalog.yaml"

    # Spec 016 — audit trail
    audit_dir: str = "~/.vigilador/audit/agent_mods"

    # ------------------------------------------------------------------
    # Specs 011-017 — Ola 2 (modes, skills, playbooks, goals, artifacts,
    # dreaming). Config surface for current + future features.
    # ------------------------------------------------------------------
    enterprise_enabled: bool = True
    file_system_root: str = ""

    # Spec 011 — modes + playbooks
    modes_dir: str = "config/modes"
    playbooks_dir: str = "config/playbooks"

    # Spec 015 + Spec 021 D3 — skill marketplace
    skills_marketplace_enabled: bool = True
    skills_sources_enabled: list[str] = [
        "curated",
        "learned",
        "external:k-dense",
        "external:agency-agents",
    ]
    skills_curated_path: str = "config/skills/curated"
    skills_learned_path: str = "config/skills/learned"
    skills_vendor_dir: str = "src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor"
    cold_skills_enabled: bool = False

    # Spec 013 — goal pursuit (F5b roadmap)
    goal_pursuit_max_depth: int = 5
    goal_pursuit_checkpoint_every: int = 3
    goal_pursuit_token_ttl_sec: int = 28800

    # Spec 014 — artifact development (F5b roadmap)
    artifacts_registry_path: str = "data/artifacts.jsonl"

    # Spec 017 — dreaming (background maintenance)
    dreaming_enabled: bool = False
    dreaming_cron_hour: int = 3
    dreaming_idle_timeout_min: int = 10

    # ------------------------------------------------------------------
    # Spec 021 — Integracion Runtime MVP (D1..D5)
    # ------------------------------------------------------------------
    mcp_external_config: str = "config/mcp/external.yaml"
    mcp_supervisor_enabled: bool = True
    mcp_logs_dir: str = "~/.vigilador/mcp-logs"
    vector_index_backend: str = "turbovec"
    ingestion_enabled: bool = True
    ingestion_connectors: list[str] = ["google_drive"]
    embedding_provider: str = "gemini"
    reranker_provider: str = "cohere"
    frontend_enabled: bool = True
    onboarding_enabled: bool = True
    computer_use_enabled: bool = False
    computer_use_app_allowlist: list[str] = []
    pi_defense_enabled: bool = True

    model_config = SettingsConfigDict(
        env_prefix="VT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
