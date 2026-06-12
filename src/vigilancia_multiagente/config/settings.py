from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Vigilancia Tecnologica Multiagente"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

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
    system_base_filename: str = "system-base.md"
    system_base_enabled: bool = True  # feature flag for rollback safety

    # Serper REST API (no MCP)
    serper_api_key: SecretStr | None = None

    # MiniMax Image MCP (Token Plan — separate key from text chat)
    minimax_image_api_key: SecretStr | None = None
    minimax_api_host: str = "https://api.minimax.io"

    # Playwright MCP
    playwright_headless: bool = True

    # Markitdown MCP
    markitdown_timeout: int = 60000

    # Sandbox
    sandbox_timeout: int = 120
    sandbox_max_output_size: int = 1_048_576  # 1MB

    # Audit mode: enable detailed logging of data transformation between layers
    audit_mode: bool = False

    # MCP Provider API Keys (all optional — system falls back gracefully)
    tavily_api_key: SecretStr | None = None
    exa_api_key: SecretStr | None = None
    jina_api_key: SecretStr | None = None
    brave_api_key: SecretStr | None = None
    firecrawl_api_key: SecretStr | None = None
    cohere_api_key: SecretStr | None = None  # reranker; opcional, fallback a embeddings

    # OpenAlex: email para el "polite pool" (mejores rate limits) y API key
    # premium opcional. Usados tanto por el cliente REST como por el MCP.
    openalex_email: str | None = None
    openalex_api_key: SecretStr | None = None

    # Spec 007 - Sistema de Evaluacion Inteligente (Workstreams A..E).
    # Flags opt-in: default false preserva el comportamiento actual del
    # vigilador. Cada workstream se activa explicitamente sin afectar los
    # demas. Los adapters externos degradan a None si su clave no esta
    # configurada (Manejo de Errores Estricto + Convencion sobre Configuracion).
    eval_ws_a_enabled: bool = False  # Source Quality
    eval_ws_b_enabled: bool = False  # Data Intelligence
    eval_ws_c_enabled: bool = False  # Deep Analysis
    eval_ws_d_enabled: bool = False  # Strategic Signals
    eval_ws_e_enabled: bool = False  # Output Assurance

    google_factcheck_api_key: SecretStr | None = None
    retraction_watch_csv_url: str | None = None

    # Spec 008 — Config UI persistence
    workstream_overrides_path: str = "config/workstream_overrides.json"
    prompt_overrides_dir: str = "config/prompt_overrides"

    # ------------------------------------------------------------------
    # Spec 009 — Vigilador 3.0 MVP Foundation (enterprise/)
    # Campos aditivos. Nada obligatorio salvo xiaomimimo_api_key para que el
    # LLM default del MVP funcione. Se mantiene el patrón plano del 2.0
    # (claves VT_<campo>), no objetos anidados.
    # ------------------------------------------------------------------

    # LLM provider activo y adapters
    llm_default: str = "xiaomimimo"  # xiaomimimo | minimax
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

    # OAuth & credentials (Fernet). Vacío resuelve a ~/.vigilador/credentials/.
    credentials_dir: str | None = None

    # Spec 021 — Google Workspace OAuth (read-only Drive scope; spec 021 F2.C
    # connector + F4a.G onboarding endpoint). Both are SecretStr-friendly when
    # configured; if unset the connector / onboarding route surface a clear
    # 503 (constitución #4 explicit error).
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_redirect_uri: str | None = None

    # Tenant (single-tenant en MVP; schema preparado para multi-tenancy)
    default_tenant_id: str = "00000000-0000-0000-0000-000000000001"

    # Observabilidad
    otel_exporter_endpoint: str | None = None
    prometheus_metrics_path: str = "/metrics"

    # Admin frontend (single-tenant)
    admin_username: str = "admin"

    # Spec 018 — catálogo SSOT de tools/MCPs
    catalog_path: str = "config/tools/catalog.yaml"

    # Spec 016 — audit trail (directorio de logs JSONL de modificaciones)
    audit_dir: str = "~/.vigilador/audit/agent_mods"

    # ------------------------------------------------------------------
    # Specs 011-017 — Ola 2 (modes, skills, playbooks, goals, artifacts,
    # dreaming). Campos aditivos planos VT_<campo>. Defaults seguros: el
    # subsistema dreaming arranca OFF (ejecuta fases en background).
    # ------------------------------------------------------------------
    # Composition gate
    enterprise_enabled: bool = True
    file_system_root: str = ""  # vacío resuelve al PROJECT_ROOT

    # Spec 011 — modes + playbooks
    modes_dir: str = "config/modes"
    playbooks_dir: str = "config/playbooks"

    # Spec 015 + Spec 021 D3 — skill marketplace (sin claude-local en runtime)
    skills_marketplace_enabled: bool = True
    skills_sources_enabled: list[str] = [
        "curated",
        "learned",
        "external:k-dense",
        "external:agency-agents",
    ]
    skills_curated_path: str = "config/skills/curated"
    skills_learned_path: str = "config/skills/learned"
    # Spec 021 D2 — repos clonados dentro de src/
    skills_vendor_dir: str = "src/vigilancia_multiagente/enterprise/skills_marketplace/_vendor"
    # Spec 022 FR-037 — cold skills activation
    cold_skills_enabled: bool = False

    # Spec 013 — goal pursuit
    goal_pursuit_max_depth: int = 5
    goal_pursuit_checkpoint_every: int = 3
    goal_pursuit_token_ttl_sec: int = 28800

    # Spec 014 — artifact development
    artifacts_registry_path: str = "data/artifacts.jsonl"

    # Spec 017 — dreaming (background maintenance; default OFF por seguridad)
    dreaming_enabled: bool = False
    dreaming_cron_hour: int = 3
    dreaming_idle_timeout_min: int = 10

    # ------------------------------------------------------------------
    # Spec 021 — Integracion Runtime MVP (D1..D5)
    # ------------------------------------------------------------------
    # MCP fallback supervisor (FR-004..008). En native-first idealmente N=0.
    mcp_external_config: str = "config/mcp/external.yaml"
    mcp_supervisor_enabled: bool = True
    mcp_logs_dir: str = "~/.vigilador/mcp-logs"
    # Vector index (D1 revisada): TurboVec NATIVO via paquete PyPI `turbovec`.
    vector_index_backend: str = "turbovec"
    # Ingestion (F2)
    ingestion_enabled: bool = True
    ingestion_connectors: list[str] = ["google_drive"]
    # Provider selection (FR-049)
    embedding_provider: str = "gemini"
    reranker_provider: str = "cohere"
    # Frontend MVP (FR-046, sin login por D4)
    frontend_enabled: bool = True
    onboarding_enabled: bool = True
    # Computer use (FR-029/030, off por seguridad)
    computer_use_enabled: bool = False
    computer_use_app_allowlist: list[str] = []
    # Governance (FR-042..045)
    tools_delete_whitelist: list[str] = ["forget_user"]
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
